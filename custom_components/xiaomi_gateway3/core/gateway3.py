import json
import logging
import random
import re
import socket
import string
import time
from threading import Thread
from typing import Optional, Dict

from paho.mqtt.client import Client, MQTTMessage
from . import bluetooth, utils
from .mini_miio import SyncmiIO
from .shell import TelnetShell, ntp_time
from .unqlite import Unqlite, SQLite
from .utils import GLOBAL_PROP

_LOGGER = logging.getLogger(__name__)

RE_NWK_KEY = re.compile(r'lumi send-nwk-key (0x.+?) {(.+?)}')
RE_MAC = re.compile('^0x0*')
# MAC reverse
RE_REVERSE = re.compile(r'(..)(..)(..)(..)(..)(..)')

TELNET_CMD = '{"method":"enable_telnet_service","params":""}'


class DevicesRegistry:
    """Global registry for all gateway devices. Because BLE devices updates
    from all gateway simultaniosly.

    Key - device did, `numb` for wifi and mesh devices, `lumi.ieee` for zigbee
    devices, `blt.3.alphanum` for ble devices, `group.numb` for mesh groups.

    Dict: did, model, mac, type, init(dict)
    """
    devices: Dict[str, dict] = {}
    updates: Dict[str, list] = {}

    def add_update(self, did: str, handler):
        """Add handler to device update event."""
        self.updates.setdefault(did, []).append(handler)

    def remove_update(self, did: str, handler):
        self.updates[did].remove(handler)


class GatewayMesh(DevicesRegistry):
    enabled: bool = None

    miio: SyncmiIO = None
    mesh_params: list = None
    mesh_ts: float = 0

    def debug(self, message: str):
        raise NotImplemented

    def mesh_start(self):
        self.mesh_params = []

        for device in self.devices.values():
            if device['type'] == 'mesh' and 'childs' not in device:
                # TODO: rewrite more clear logic for lights and switches
                p = device['params'][0]
                self.mesh_params.append({
                    'did': device['did'], 'siid': p[0], 'piid': p[1]
                })

        if self.mesh_params:
            self.mesh_ts = time.time() + 30
            Thread(target=self.mesh_run).start()

    def mesh_run(self):
        self.debug("Start Mesh Thread")

        while self.enabled:
            if time.time() < self.mesh_ts:
                time.sleep(1)
                continue

            try:
                resp = self.miio.send_bulk('get_properties', self.mesh_params)
                if resp:
                    params2 = []
                    for item in resp:
                        if 'value' not in item:
                            continue

                        did = item['did']
                        device_params = self.devices[did]['params']
                        # get other props for turn on lights or live switches
                        if device_params[0][3] == 'switch' or item['value']:
                            params2 += [{
                                'did': did, 'siid': p[0], 'piid': p[1]
                            } for p in device_params[1:]]

                    if params2:
                        resp2 = self.miio.send_bulk('get_properties', params2)
                        if resp2:
                            resp += resp2

                    self.debug(f"Pull Mesh {resp}")
                    self.process_mesh_data(resp)

                else:
                    self.debug("Can't get mesh bulb state")

            except Exception as e:
                self.debug(f"ERROR in mesh thread {e}")

            self.mesh_ts = time.time() + 30

    def process_mesh_data(self, data: list):
        """Can receive multiple properties from multiple devices.

           data = [{'did':123,'siid':2,'piid':1,'value:True}]
        """
        bulk = {}

        for param in data:
            if param.get('code', 0) != 0:
                continue

            did = param['did']
            if did not in self.updates:
                continue

            device = self.devices[did]

            prop = next((
                p[2] for p in device['params']
                if p[0] == param['siid'] and p[1] == param['piid']
            ), None)
            if not prop:
                continue

            if did not in bulk:
                bulk[did] = {}

            bulk[did][prop] = param['value']

        for did, payload in bulk.items():
            self.debug(f"Process Mesh Data for {did}: {payload}")
            for handler in self.updates[did]:
                handler(payload)

    def send_mesh(self, device: dict, data: dict):
        # data = {'light':True}
        payload = []
        for k, v in data.items():
            param = next(
                p for p in device['params']
                if p[2] == k
            )
            payload.append({
                'did': device['did'],
                'siid': param[0],
                'piid': param[1],
                'value': v if param[0] != 8 else int(v)
            })

        try:
            # 2 seconds are selected experimentally
            if self.miio.send('set_properties', payload):
                self.mesh_force_update()
        except:
            self.debug(f"Can't send mesh {device['did']} => {data}")

    def mesh_force_update(self):
        self.mesh_ts = time.time() + 2


# noinspection PyUnusedLocal
class GatewayStats:
    did: str = None
    stats: dict = None
    host: str = None
    info_ts: float = 0

    mqtt: Client = None
    gw_topic: str = None

    # if mqtt connected
    available: bool = None

    # interval for auto parent refresh in minutes, 0 - disabled auto refresh
    # -1 - disabled
    parent_scan_interval: Optional[int] = None

    # collected data from MQTT topic log/z3 (zigbee console)
    z3buffer: Optional[dict] = None

    def debug(self, message: str):
        raise NotImplemented

    def add_stats(self, ieee: str, handler):
        self.stats[ieee] = handler

        if self.parent_scan_interval > 0:
            self.info_ts = time.time() + 5

    def remove_stats(self, ieee: str, handler):
        self.stats.pop(ieee)

    def process_gw_stats(self, payload: dict = None):
        # empty payload - update available state
        self.debug(f"gateway <= {payload or self.available}")

        if self.did not in self.stats:
            return

        if payload:
            if 'networkUp' in payload:
                # {"networkUp":false}
                payload = {
                    'network_pan_id': payload.get('networkPanId'),
                    'radio_tx_power': payload.get('radioTxPower'),
                    'radio_channel': payload.get('radioChannel'),
                }
            elif 'free_mem' in payload:
                s = payload['run_time']
                h, m, s = s // 3600, s % 3600 // 60, s % 60
                payload = {
                    'free_mem': payload['free_mem'],
                    'load_avg': payload['load_avg'],
                    'rssi': -payload['rssi'],
                    'uptime': f"{h:02}:{m:02}:{s:02}",
                }

        self.stats[self.did](payload)

    def process_zb_stats(self, payload: dict):
        ieee = payload['eui64']
        if ieee in self.stats:
            self.stats[ieee](payload)

        if self.info_ts and time.time() > self.info_ts:
            # block any auto updates in 30 seconds
            self.info_ts = time.time() + 30

            self.get_gateway_info()

    def process_ble_stats(self, payload: dict):
        did = payload['dev']['did'] if 'dev' in payload else payload['did']
        if did in self.stats:
            self.stats[did](payload)

    def process_z3(self, payload: str):
        if payload.startswith("CLI command executed"):
            cmd = payload[22:-1]
            if cmd == "debugprint all_on" or self.z3buffer is None:
                # reset all buffers
                self.z3buffer = {}
            else:
                self.z3buffer[cmd] = self.z3buffer['buffer']

            self.z3buffer['buffer'] = ''

            if cmd == "plugin concentrator print-table":
                self._process_gateway_info()

        elif self.z3buffer:
            self.z3buffer['buffer'] += payload

    def get_gateway_info(self):
        self.debug("Update zigbee network info")
        payload = {'commands': [
            {'commandcli': "debugprint all_on"},
            {'commandcli': "plugin device-table print"},
            {'commandcli': "plugin stack-diagnostics child-table"},
            {'commandcli': "plugin stack-diagnostics neighbor-table"},
            {'commandcli': "plugin concentrator print-table"},
            {'commandcli': "debugprint all_off"},
        ]}
        payload = json.dumps(payload, separators=(',', ':'))
        self.mqtt.publish(self.gw_topic + 'commands', payload)

    def send_zigbee_cli(self, commands: list):
        payload = {'commands': [{'commandcli': cmd} for cmd in commands]}
        payload = json.dumps(payload, separators=(',', ':'))
        self.mqtt.publish(self.gw_topic + 'commands', payload)

    def _process_gateway_info(self):
        self.debug("Update parent info table")

        try:
            raw = self.z3buffer["plugin device-table print"]
            m1 = re.findall(r'\d+ ([A-F0-9]{4}): {2}([A-F0-9]{16}) 0 {2}\w+ '
                            r'(\d+)', raw)

            raw = self.z3buffer["plugin stack-diagnostics child-table"]
            m2 = re.findall(r'\(>\)([A-F0-9]{16})', raw)

            raw = self.z3buffer["plugin stack-diagnostics neighbor-table"]
            m3 = re.findall(r'\(>\)([A-F0-9]{16})', raw)

            raw = self.z3buffer["plugin concentrator print-table"]
            m4 = re.findall(r': ([A-F0-9x> -]{16,}) -> 0x0000', raw)
            m4 = [i.replace('0x', '').split(' -> ') for i in m4]
            m4 = {i[0]: i[1:] for i in m4}

            self.debug(f"Total zigbee devices: {len(m1)}")

            for i in m1:
                ieee = '0x' + i[1]

                nwk = i[0]
                ago = int(i[2])
                type_ = 'device' if i[1] in m2 else \
                    'router' if i[1] in m3 else '-'
                parent = '0x' + m4[nwk][0] if nwk in m4 else '-'

                payload = {
                    'nwk': '0x' + nwk,
                    'ago': ago,
                    'type': type_,
                    'parent': parent
                }

                if ieee in self.stats:
                    self.stats[ieee](payload)
                else:
                    self.debug(f"Unknown zigbee device {ieee}: {payload}")

            # one hour later
            if self.parent_scan_interval > 0:
                self.info_ts = time.time() + self.parent_scan_interval * 60

        except Exception as e:
            self.debug(f"Can't update parents: {e}")


# noinspection PyUnusedLocal
class Gateway3(Thread, GatewayMesh, GatewayStats):
    did = None
    time_offset = 0
    pair_model = None
    pair_payload = None
    telnet_cmd = None

    def __init__(self, host: str, token: str, config: dict, **options):
        super().__init__(daemon=True)

        self.host = host
        self.options = options

        self.miio = SyncmiIO(host, token)

        self.mqtt = Client()
        self.mqtt.on_connect = self.on_connect
        self.mqtt.on_disconnect = self.on_disconnect
        self.mqtt.on_message = self.on_message

        self._ble = options.get('ble', True)  # for fast access
        self._debug = options.get('debug', '')  # for fast access
        self.parent_scan_interval = options.get('parent', -1)
        self.default_devices = config['devices'] if config else None

        self.telnet_cmd = options.get('telnet_cmd') or TELNET_CMD

        if 'true' in self._debug:
            self.miio.debug = True

        self.setups = {}
        self.stats = {}

    @property
    def device(self):
        return self.devices[self.did]

    def add_setup(self, domain: str, handler):
        """Add hass device setup funcion."""
        self.setups[domain] = handler

    def setup_entry(self, domain: str, device: dict, attr: str):
        if 'setup' not in device:
            # setup first entry
            device['setup'] = [attr]
        elif attr in device['setup']:
            # skip duplicate entry
            return
        else:
            device['setup'].append(attr)

        self.setups[domain](self, device, attr)

    def debug(self, message: str):
        # basic logs
        if 'true' in self._debug:
            _LOGGER.debug(f"{self.host} | {message}")

    def stop(self):
        self.enabled = False
        self.mqtt._thread_terminate = True

    def run(self):
        """Main thread loop."""
        self.debug("Start main thread")

        self.mqtt.connect_async(self.host)

        self.enabled = True
        while self.enabled:
            # if not telnet - enable it
            if not self._check_port(23) and not self._enable_telnet():
                time.sleep(30)
                continue

            devices = self._prepare_gateway(with_devices=True)
            if devices:
                self.gw_topic = f"gw/{devices[0]['mac'][2:].upper()}/"
                self.setup_devices(devices)
                break

        self.update_time_offset()
        self.mesh_start()

        while self.enabled:
            # if not telnet - enable it
            if not self._check_port(23) and not self._enable_telnet():
                time.sleep(30)
                continue

            # if not mqtt - enable it (handle Mi Home and ZHA mode)
            if not self._prepare_gateway() or not self._mqtt_connect():
                time.sleep(60)
                continue

            self.mqtt.loop_forever()

        self.debug("Stop main thread")

    def update_time_offset(self):
        gw_time = ntp_time(self.host)
        if gw_time:
            self.time_offset = gw_time - time.time()
            self.debug(f"Gateway time offset: {self.time_offset}")

    def _check_port(self, port: int):
        """Check if gateway port open."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            return s.connect_ex((self.host, port)) == 0
        finally:
            s.close()

    def _enable_telnet(self):
        """Enable telnet with miio protocol."""
        raw = json.loads(self.telnet_cmd)
        if self.miio.send(raw['method'], raw.get('params')) != 'ok':
            self.debug(f"Can't enable telnet")
            return False
        return True

    def _prepare_gateway(self, with_devices: bool = False):
        """Launching the required utilities on the hub, if they are not already
        running.
        """
        self.debug("Prepare Gateway")
        try:
            shell = TelnetShell(self.host)
            self.debug(f"Version: {shell.ver}")

            ps = shell.get_running_ps()

            if "mosquitto -d" not in ps:
                self.debug("Run public mosquitto")
                shell.run_public_mosquitto()

            if "ntpd" not in ps:
                # run NTPd for sync time
                shell.run_ntpd()

            bt_fix = shell.check_bt()
            if bt_fix is None:
                self.debug("Fixed BT don't supported")

            elif bt_fix is False:
                self.debug("Download fixed BT")
                shell.download_bt()

                # check after download
                if shell.check_bt():
                    self.debug("Run fixed BT")
                    shell.run_bt()

            elif "log/ble" not in ps:
                self.debug("Run fixed BT")
                shell.run_bt()

            if "log/miio" not in ps:
                # all data or only necessary events
                pattern = (
                    '\\{"' if 'miio' in self._debug else
                    "ot_agent_recv_handler_one.+"
                    "ble_event|properties_changed|heartbeat"
                )
                self.debug(f"Redirect miio to MQTT")
                shell.redirect_miio2mqtt(pattern)

            if self.options.get('buzzer'):
                if "dummy:basic_gw" not in ps:
                    self.debug("Disable buzzer")
                    shell.stop_buzzer()
            else:
                if "dummy:basic_gw" in ps:
                    self.debug("Enable buzzer")
                    shell.run_buzzer()

            if self.options.get('zha'):
                if "socat" not in ps:
                    if "Received" in shell.check_or_download_socat():
                        self.debug("Download socat")
                    self.debug("Run socat")
                    shell.run_socat()

                if "Lumi_Z3GatewayHost_MQTT" in ps:
                    self.debug("Stop Lumi Zigbee")
                    shell.stop_lumi_zigbee()

            else:
                if "socat" in ps:
                    self.debug("Stop socat")
                    shell.stop_socat()

                if (self.parent_scan_interval >= 0 and
                        "Lumi_Z3GatewayHost_MQTT -n 1 -b 115200 -l" not in ps):
                    self.debug("Run public Zigbee console")
                    shell.run_public_zb_console()

                elif "Lumi_Z3GatewayHost_MQTT" not in ps:
                    self.debug("Run Lumi Zigbee")
                    shell.run_lumi_zigbee()

            if with_devices:
                self.debug("Get devices")
                return self._get_devices(shell)

            return True

        except (ConnectionRefusedError, socket.timeout):
            return False

        except Exception as e:
            self.debug(f"Can't read devices: {e}")
            return False

    def _mqtt_connect(self) -> bool:
        try:
            self.mqtt.reconnect()
            return True
        except:
            return False

    def _miio_connect(self) -> bool:
        if not self.miio.ping():
            self.debug("Can't send handshake")
            return False

        return True

    def _get_devices(self, shell: TelnetShell):
        """Load devices info for Coordinator, Zigbee and Mesh."""

        # 1. Read coordinator info
        raw = shell.read_file('/data/miio/device.conf').decode()
        m = re.search(r'did=(\d+)', raw)
        self.did = m[1]

        raw = shell.read_file('/data/zigbee/coordinator.info')
        device = json.loads(raw)
        devices = [{
            'did': self.did,
            'model': 'lumi.gateway.mgl03',
            'mac': device['mac'],
            'type': 'gateway',
            'init': {
                'firmware lock': shell.check_firmware_lock(),
            }
        }]

        # 2. Read zigbee devices
        if not self.options.get('zha'):
            # read Silicon devices DB
            nwks = {}
            try:
                raw = shell.read_file('/data/silicon_zigbee_host/devices.txt')
                raw = raw.decode().split(' ')
                for i in range(0, len(raw) - 1, 32):
                    ieee = reversed(raw[i + 3:i + 11])
                    ieee = ''.join(f"{i:>02s}" for i in ieee)
                    nwks[ieee] = f"{raw[i]:>04s}"
            except:
                _LOGGER.exception("Can't read Silicon devices DB")

            # read Xiaomi devices DB
            raw = shell.read_file(shell.zigbee_db, as_base64=True)
            # self.debug(f"Devices RAW: {raw}")
            if raw.startswith(b'unqlite'):
                db = Unqlite(raw)
                data = db.read_all()
            else:
                raw = re.sub(br'}\s*{', b',', raw)
                data = json.loads(raw)

            # data = {} or data = {'dev_list': 'null'}
            dev_list = json.loads(data.get('dev_list', 'null')) or []

            for did in dev_list:
                model = data[did + '.model']
                desc = utils.get_device(model)

                # skip unknown model
                if desc is None:
                    self.debug(f"{did} has an unsupported modell: {model}")
                    continue

                retain = json.loads(data[did + '.prop'])['props']
                self.debug(f"{did} {model} retain: {retain}")

                params = {
                    p[2]: retain.get(p[1])
                    for p in (desc['params'] or desc['mi_spec'])
                    if p[1] is not None
                }

                ieee = f"{data[did + '.mac']:>016s}"
                device = {
                    'did': did,
                    'mac': '0x' + data[did + '.mac'],
                    'ieee': ieee,
                    'nwk': nwks.get(ieee),
                    'model': data[did + '.model'],
                    'type': 'zigbee',
                    'fw_ver': retain.get('fw_ver'),
                    'init': utils.fix_xiaomi_props(params),
                    'online': retain.get('alive', 1) == 1
                }
                devices.append(device)

        # 3. Read bluetooth devices
        if self._ble:
            raw = shell.read_file('/data/miio/mible_local.db', as_base64=True)
            db = SQLite(raw)

            # load BLE devices
            rows = db.read_table('gateway_authed_table')
            for row in rows:
                device = {
                    'did': row[4],
                    'mac': RE_REVERSE.sub(r'\6\5\4\3\2\1', row[1]),
                    'model': row[2],
                    'type': 'ble'
                }
                devices.append(device)

            # load Mesh groups
            try:
                mesh_groups = {}

                rows = db.read_table(shell.mesh_group_table)
                for row in rows:
                    # don't know if 8 bytes enougth
                    mac = int(row[0]).to_bytes(8, 'big').hex()
                    device = {
                        'did': 'group.' + row[0],
                        'mac': mac,
                        'model': 0,
                        'childs': [],
                        'type': 'mesh'
                    }
                    group_addr = row[1]
                    mesh_groups[group_addr] = device

                # load Mesh bulbs
                rows = db.read_table(shell.mesh_device_table)
                for row in rows:
                    device = {
                        'did': row[0],
                        'mac': row[1].replace(':', ''),
                        'model': row[2],
                        'type': 'mesh'
                    }
                    devices.append(device)

                    group_addr = row[5]
                    if group_addr in mesh_groups:
                        # add bulb to group if exist
                        mesh_groups[group_addr]['childs'].append(row[0])

                for device in mesh_groups.values():
                    if device['childs']:
                        devices.append(device)

            except:
                _LOGGER.exception("Can't read mesh devices")

        # for testing purposes
        for k, v in self.default_devices.items():
            if k[0] == '_':
                devices.append(v)

        return devices

    def lock_firmware(self, enable: bool):
        self.debug(f"Set firmware lock to {enable}")
        try:
            shell = TelnetShell(self.host)
            if "Received" in shell.check_or_download_busybox():
                self.debug("Download busybox")
            shell.lock_firmware(enable)
            locked = shell.check_firmware_lock()
            shell.close()
            return enable == locked

        except Exception as e:
            self.debug(f"Can't set firmware lock: {e}")
            return False

    def on_connect(self, client, userdata, flags, rc):
        self.debug("MQTT connected")
        self.mqtt.subscribe('#')

        self.available = True
        self.process_gw_stats()

    def on_disconnect(self, client, userdata, rc):
        self.debug("MQTT disconnected")
        # force end mqtt.loop_forever()
        self.mqtt.disconnect()

        self.available = False
        self.process_gw_stats()

    def on_message(self, client: Client, userdata, msg: MQTTMessage):
        try:
            topic = msg.topic

            if 'mqtt' in self._debug:
                _LOGGER.debug(f"{self.host} | MQTT | {topic} {msg.payload}")

            if topic == 'zigbee/send':
                payload = json.loads(msg.payload)
                self.process_message(payload)

            elif topic == 'log/miio':
                # don't need to process another data
                if b'ot_agent_recv_handler_one' not in msg.payload:
                    return

                for raw in utils.extract_jsons(msg.payload):
                    if self._ble and b'_async.ble_event' in raw:
                        data = json.loads(raw)['params']
                        self.process_ble_event(data)
                        self.process_ble_stats(data)
                    elif self._ble and b'properties_changed' in raw:
                        data = json.loads(raw)['params']
                        self.debug(f"Process props {data}")
                        self.process_mesh_data(data)
                    elif b'event.gw.heartbeat' in raw:
                        payload = json.loads(raw)['params'][0]
                        self.process_gw_stats(payload)
                        # time offset may changed right after gw.heartbeat
                        self.update_time_offset()

            elif topic == 'log/ble':
                payload = json.loads(msg.payload)
                self.process_ble_event_fix(payload)

            elif topic == 'log/z3':
                self.process_z3(msg.payload.decode())

            elif topic.endswith('/heartbeat'):
                payload = json.loads(msg.payload)
                self.process_gw_stats(payload)

            elif topic.endswith(('/MessageReceived', '/devicestatechange')):
                payload = json.loads(msg.payload)
                self.process_zb_stats(payload)

            # read only retained ble
            elif topic.startswith('ble') and msg.retain:
                payload = json.loads(msg.payload)
                self.process_ble_retain(topic[4:], payload)

            elif self.pair_model and topic.endswith('/commands'):
                self.process_pair(msg.payload)

        except:
            _LOGGER.exception(f"Processing MQTT: {msg.topic} {msg.payload}")

    def setup_devices(self, devices: list):
        """Add devices to hass."""
        for device in devices:
            if device['did'] in self.devices:
                continue

            if device['type'] in ('gateway', 'zigbee'):
                desc = utils.get_device(device['model'])
                if not desc:
                    self.debug(f"Unsupported model: {device}")
                    continue

                self.debug(f"Setup Zigbee device {device}")

                device.update(desc)

                # update params from config
                default_config = (
                        self.default_devices.get(device['mac']) or
                        self.default_devices.get(device['did'])
                )
                if default_config:
                    device.update(default_config)

                self.devices[device['did']] = device

                for param in (device['params'] or device['mi_spec']):
                    domain = param[3]
                    if not domain:
                        continue

                    self.setup_entry(domain, device, param[2])

            elif device['type'] == 'mesh':
                desc = bluetooth.get_device(device['model'], 'Mesh')
                device.update(desc)

                self.debug(f"Setup Mesh device {device}")

                # update params from config
                default_config = self.default_devices.get(device['did'])
                if default_config:
                    device.update(default_config)

                device['online'] = False

                self.devices[device['did']] = device

                for param in device['params']:
                    domain = param[3]
                    if not domain:
                        continue

                    self.setup_entry(domain, device, param[2])

            elif device['type'] == 'ble':
                # only save info for future
                desc = bluetooth.get_device(device['model'], 'BLE')
                device.update(desc)

                # update params from config
                default_config = self.default_devices.get(device['did'])
                if default_config:
                    device.update(default_config)

                self.devices[device['did']] = device

                device['init'] = {}

            if self.options.get('stats') and device['type'] != 'mesh':
                self.setup_entry('sensor', device, device['type'])

    def process_message(self, data: dict):
        if data['cmd'] == 'heartbeat':
            # don't know if only one item
            assert len(data['params']) == 1, data

            data = data['params'][0]
            pkey = 'res_list'
        elif data['cmd'] == 'report':
            pkey = 'params' if 'params' in data else 'mi_spec'
        elif data['cmd'] in ('write_rsp', 'read_rsp'):
            pkey = 'results' if 'results' in data else 'mi_spec'
        elif data['cmd'] == 'write_ack':
            return
        else:
            _LOGGER.warning(f"Unsupported cmd: {data}")
            return

        did = data['did'] if data['did'] != 'lumi.0' else self.did

        # skip without callback and without data
        if did not in self.updates or pkey not in data:
            return

        ts = time.time()

        device = self.devices[did]
        payload = {}

        # convert codes to names
        for param in data[pkey]:
            if param.get('error_code', 0) != 0:
                continue

            if 'res_name' in param:
                prop = param['res_name']
            elif 'piid' in param:
                prop = f"{param['siid']}.{param['piid']}"
            elif 'eiid' in param:
                prop = f"{param['siid']}.{param['eiid']}"
            else:
                _LOGGER.warning(f"Unsupported param: {data}")
                return

            if prop in GLOBAL_PROP:
                prop = GLOBAL_PROP[prop]
            else:
                prop = next((
                    p[2] for p in (device['params'] or device['mi_spec'])
                    if p[0] == prop
                ), prop)

            # https://github.com/Koenkk/zigbee2mqtt/issues/798
            # https://www.maero.dk/aqara-temperature-humidity-pressure-sensor-teardown/
            if prop == 'temperature':
                if -4000 < param['value'] < 12500:
                    payload[prop] = param['value'] / 100.0
            elif prop == 'humidity':
                if 0 <= param['value'] <= 10000:
                    payload[prop] = param['value'] / 100.0
            elif prop == 'pressure':
                payload[prop] = param['value'] / 100.0
            elif prop == 'battery' and param['value'] > 1000:
                # xiaomi light sensor
                payload[prop] = round((min(param['value'], 3200) - 2500) / 7)
            elif prop == 'alive' and param['value']['status'] == 'offline':
                device['online'] = False
            elif prop == 'angle':
                # xiaomi cube 100 points = 360 degrees
                payload[prop] = param['value'] * 4
            elif prop == 'duration':
                # xiaomi cube
                payload[prop] = param['value'] / 1000.0
            elif prop in ('consumption', 'power'):
                payload[prop] = round(param['value'], 2)
            elif 'value' in param:
                payload[prop] = param['value']
            elif 'arguments' in param:
                if prop == 'motion':
                    payload[prop] = 1
                else:
                    payload[prop] = param['arguments']

        # no time in device add command
        ts = round(ts - data['time'] * 0.001 + self.time_offset, 2) \
            if 'time' in data else '?'
        self.debug(f"{device['did']} {device['model']} <= {payload} [{ts}]")

        if payload:
            device['online'] = True

        for handler in self.updates[did]:
            handler(payload)

        if 'added_device' in payload:
            # {'did': 'lumi.fff', 'mac': 'fff', 'model': 'lumi.sen_ill.mgl01',
            # 'version': '21', 'zb_ver': '3.0'}
            device = payload['added_device']
            device['mac'] = '0x' + device['mac']
            device['type'] = 'zigbee'
            device['init'] = payload
            self.setup_devices([device])

    def process_ble_event(self, data: dict):
        self.debug(f"Process BLE {data}")

        pdid = data['dev'].get('pdid')

        did = data['dev']['did']
        if did not in self.devices:
            mac = data['dev']['mac'].replace(':', '').lower() \
                if 'mac' in data['dev'] else \
                'ble_' + did.replace('blt.3.', '')
            self.devices[did] = device = {
                'did': did, 'mac': mac, 'init': {}, 'type': 'bluetooth'}
            desc = bluetooth.get_device(pdid, 'BLE')
            device.update(desc)

            # update params from config
            default_config = self.default_devices.get(did)
            if default_config:
                device.update(default_config)

        else:
            device = self.devices[did]

        if device.get('seq') == data['frmCnt']:
            return
        device['seq'] = data['frmCnt']

        if isinstance(data['evt'], list):
            # check if only one
            assert len(data['evt']) == 1, data
            payload = bluetooth.parse_xiaomi_ble(data['evt'][0], pdid)
        elif isinstance(data['evt'], dict):
            payload = bluetooth.parse_xiaomi_ble(data['evt'], pdid)
        else:
            payload = None

        self._process_ble_event(device, payload)

    def process_ble_event_fix(self, data: dict):
        self.debug(f"Process BLE Fix {data}")

        did = data['did']
        if did not in self.devices:
            self.debug(f"Unregistered BLE device {did}")
            return

        device = self.devices[did]
        if device.get('seq') == data['seq']:
            return
        device['seq'] = data['seq']

        payload = bluetooth.parse_xiaomi_ble(data, data['pdid'])
        self._process_ble_event(device, payload)

    def _process_ble_event(self, device: dict, payload: dict):
        did = device['did']

        # init entities if needed
        init = device['init']
        for k in payload.keys():
            if k in init:
                # update for retain
                init[k] = payload[k]
                continue

            init[k] = payload[k]

            domain = bluetooth.get_ble_domain(k)
            if not domain:
                continue

            self.setup_entry(domain, device, k)

        if did in self.updates:
            for handler in self.updates[did]:
                handler(payload)

        raw = json.dumps(init, separators=(',', ':'))
        self.mqtt.publish(f"ble/{did}", raw, retain=True)

    def process_ble_retain(self, did: str, payload: dict):
        if did not in self.devices:
            self.debug(f"BLE device {did} is no longer on the gateway")
            return

        self.debug(f"{did} retain: {payload}")

        device = self.devices[did]

        # init entities if needed
        for k in payload.keys():
            # don't retain action and motion
            if k in device['init']:
                continue

            if k in ('action', 'motion'):
                device['init'][k] = ''
            else:
                device['init'][k] = payload[k]

            domain = bluetooth.get_ble_domain(k)
            if not domain:
                continue

            self.setup_entry(domain, device, k)

        if did in self.updates:
            for handler in self.updates[did]:
                handler(payload)

    def process_pair(self, raw: bytes):
        _LOGGER.debug(f"!!! {raw}")
        # get shortID and eui64 of paired device
        if b'lumi send-nwk-key' in raw:
            # create model response
            payload = f"0x08020105000042{len(self.pair_model):02x}" \
                      f"{self.pair_model.encode().hex()}"
            m = RE_NWK_KEY.search(raw.decode())
            self.pair_payload = json.dumps({
                'sourceAddress': m[1],
                'eui64': '0x' + m[2],
                'profileId': '0x0104',
                'clusterId': '0x0000',
                'sourceEndpoint': '0x01',
                'destinationEndpoint': '0x01',
                'APSCounter': '0x01',
                'APSPlayload': payload
            }, separators=(',', ':'))
            self.pair_payload2 = json.dumps({
                'sourceAddress': m[1],
                'eui64': '0x' + m[2],
                'profileId': '0x0104',
                'clusterId': '0x0000',
                'sourceEndpoint': '0x01',
                'destinationEndpoint': '0x01',
                'APSCounter': '0x01',
                'APSPlayload': '0x0801010100002001'
            }, separators=(',', ':'))

        # send model response "from device"
        elif b'zdo active ' in raw:
            self.mqtt.publish(self.gw_topic + 'MessageReceived',
                              self.pair_payload2)
            self.mqtt.publish(self.gw_topic + 'MessageReceived',
                              self.pair_payload)

    def send(self, device: dict, data: dict):
        did = device['did'] if device['did'] != self.did else 'lumi.0'
        payload = {'cmd': 'write', 'did': did}

        # convert hass prop to lumi prop
        if device['mi_spec']:
            params = []
            for k, v in data.items():
                if k == 'switch':
                    v = bool(v)
                k = next(p[0] for p in device['mi_spec'] if p[2] == k)
                params.append({
                    'siid': int(k[0]), 'piid': int(k[2]), 'value': v
                })

            payload['mi_spec'] = params
        else:
            params = [{
                'res_name': next(p[0] for p in device['params'] if p[2] == k),
                'value': v
            } for k, v in data.items()]

            payload = {
                'cmd': 'write',
                'did': device['did'],
                'params': params,
            }

        self.debug(f"{device['did']} {device['model']} => {payload}")
        payload = json.dumps(payload, separators=(',', ':')).encode()
        self.mqtt.publish('zigbee/recv', payload)

    def send_telnet(self, *args: str):
        try:
            shell = TelnetShell(self.host)
            for command in args:
                if command == 'ftp':
                    shell.check_or_download_busybox()
                    shell.run_ftp()
                else:
                    shell.exec(command)
            shell.close()

        except Exception as e:
            _LOGGER.exception(f"Telnet command error: {e}")

    def send_mqtt(self, cmd: str):
        if cmd == 'publishstate':
            self.mqtt.publish(self.gw_topic + 'publishstate')

    def get_device(self, mac: str) -> Optional[dict]:
        for device in self.devices.values():
            if device.get('mac') == mac:
                return device
        return None


def is_gw3(host: str, token: str) -> Optional[str]:
    device = SyncmiIO(host, token)
    info = device.info()

    if not info:
        return 'cant_connect'

    if info['model'] != 'lumi.gateway.mgl03':
        return 'wrong_model'

    return None


def get_lan_key(device: dict):
    device = SyncmiIO(device['localip'], device['token'])
    resp = device.send('get_lumi_dpf_aes_key')
    if resp is None:
        return "Can't connect to gateway"
    if len(resp[0]) == 16:
        return resp[0]
    key = ''.join(random.choice(string.ascii_lowercase + string.digits)
                  for _ in range(16))
    resp = device.send('set_lumi_dpf_aes_key', [key])
    if resp[0] == 'ok':
        return key
    return "Can't update gateway key"
