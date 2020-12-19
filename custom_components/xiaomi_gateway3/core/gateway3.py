import json
import logging
import re
import socket
import time
from telnetlib import Telnet
from threading import Thread
from typing import Optional, Union

from paho.mqtt.client import Client, MQTTMessage
from . import bluetooth, utils
from .mini_miio import SyncmiIO
from .shell import TelnetShell
from .unqlite import Unqlite, SQLite
from .utils import GLOBAL_PROP

_LOGGER = logging.getLogger(__name__)

RE_NWK_KEY = re.compile(r'lumi send-nwk-key (0x.+?) {(.+?)}')
RE_MAC = re.compile('^0x0*')
# MAC reverse
RE_REVERSE = re.compile(r'(..)(..)(..)(..)(..)(..)')


class GatewayV:
    """Handling different firmware versions."""
    ver = None

    @property
    def ver_mesh_group(self) -> str:
        return 'mesh_group_v1' if self.ver >= '1.4.6_0043' else 'mesh_group'

    @property
    def ver_zigbee_db(self) -> str:
        # https://github.com/AlexxIT/XiaomiGateway3/issues/14
        # fw 1.4.6_0012 and below have one zigbee_gw.db file
        # fw 1.4.6_0030 have many json files in this folder
        return '*.json' if self.ver >= '1.4.6_0030' else 'zigbee_gw.db'

    @property
    def ver_miio(self) -> bool:
        return self.ver >= '1.4.7_0063'


class GatewayMesh:
    enabled: bool = None

    devices: dict = None
    updates: dict = None

    miio: SyncmiIO = None
    mesh_params: list = None
    mesh_ts: float = 0

    def debug(self, message: str):
        raise NotImplemented

    def mesh_start(self):
        self.mesh_params = [
            {'did': device['did'], 'siid': 2, 'piid': 1}
            for device in self.devices.values()
            # cannot get state of mesh group
            if device['type'] == 'mesh' and 'childs' not in device
        ]

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
                    # get turn on bulbs
                    params = [
                        {'did': item['did'], 'siid': 2, 'piid': 2}
                        for item in resp if item.get('value')
                    ]

                    if params:
                        params += [
                            {'did': item['did'], 'siid': 2, 'piid': 3}
                            for item in params
                        ]
                        resp2 = self.miio.send_bulk('get_properties', params)
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
        data = bluetooth.parse_xiaomi_mesh(data)
        for did, payload in data.items():
            if did in self.updates:
                for handler in self.updates[did]:
                    handler(payload)

    def send_mesh(self, device: dict, data: dict):
        did = device['did']
        payload = bluetooth.pack_xiaomi_mesh(did, data)
        try:
            # 2 seconds are selected experimentally
            if self.miio.send('set_properties', payload):
                self.mesh_force_update()
        except:
            self.debug(f"Can't send mesh {did} => {data}")

    def mesh_force_update(self):
        self.mesh_ts = time.time() + 2


# noinspection PyUnusedLocal
class GatewayStats:
    stats: dict = None
    host: str = None
    info_ts: float = 0
    info_loading: bool = False

    # if mqtt connected
    available: bool = None

    # interval for auto parent refresh in minutes, 0 - disabled auto refresh
    # None - disabled
    parent_scan_interval: Optional[int] = None

    def debug(self, message: str):
        raise NotImplemented

    def add_stats(self, ieee: str, handler):
        self.stats[ieee] = handler

        if self.parent_scan_interval:
            self.info_ts = time.time() + 5

    def remove_stats(self, ieee: str, handler):
        self.stats.pop(ieee)

    def process_gw_stats(self, payload: dict = None):
        # empty payload - update available state
        self.debug(f"gateway <= {payload or self.available}")

        if 'lumi.0' not in self.stats:
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
                payload.pop('ip')
                payload.pop('ssid')
                s = payload.pop('run_time')
                h, m, s = s // 3600, s % 3600 // 60, s % 60
                payload['uptime'] = f"{h:02}:{m:02}:{s:02}"

        self.stats['lumi.0'](payload)

    def process_zb_stats(self, payload: dict):
        ieee = payload['eui64']
        if ieee in self.stats:
            self.stats[ieee](payload)

        if self.info_ts and time.time() > self.info_ts:
            self.get_gateway_info()

    def process_ble_stats(self, payload: dict):
        did = payload['dev']['did']
        if did in self.stats:
            self.stats[did](payload)

    def get_gateway_info(self):
        if self.info_loading:
            return
        self.info_loading = True
        Thread(target=self._info_loader_run).start()

    def _info_loader_run(self):
        self.debug("Update parent info table")

        telnet = Telnet(self.host, 4901)
        telnet.read_until(b'Lumi_Z3GatewayHost')

        telnet.write(b"option print-rx-msgs disable\r\n")
        telnet.read_until(b'Lumi_Z3GatewayHost')

        telnet.write(b"plugin device-table print\r\n")
        raw = telnet.read_until(b'Lumi_Z3GatewayHost').decode()
        m1 = re.findall(r'\d+ ([A-F0-9]{4}): {2}([A-F0-9]{16}) 0 {2}\w+ (\d+)',
                        raw)

        telnet.write(b"plugin stack-diagnostics child-table\r\n")
        raw = telnet.read_until(b'Lumi_Z3GatewayHost').decode()
        m2 = re.findall(r'\(>\)([A-F0-9]{16})', raw)

        telnet.write(b"plugin stack-diagnostics neighbor-table\r\n")
        raw = telnet.read_until(b'Lumi_Z3GatewayHost').decode()
        m3 = re.findall(r'\(>\)([A-F0-9]{16})', raw)

        telnet.write(b"plugin concentrator print-table\r\n")
        raw = telnet.read_until(b'Lumi_Z3GatewayHost').decode()
        m4 = re.findall(r': (.{16,}) -> 0x0000', raw)
        m4 = [i.replace('0x', '').split(' -> ') for i in m4]
        m4 = {i[0]: i[1:] for i in m4}

        for i in m1:
            ieee = '0x' + i[1]
            if ieee not in self.stats:
                continue

            nwk = i[0]
            ago = int(i[2])
            type_ = 'device' if i[1] in m2 else 'router' if i[1] in m3 else '-'
            parent = '0x' + m4[nwk][0] if nwk in m4 else '-'

            self.stats[ieee]({
                'nwk': '0x' + nwk,
                'ago': ago,
                'type': type_,
                'parent': parent
            })

        self.info_loading = False
        # one hour later
        if self.parent_scan_interval:
            self.info_ts = time.time() + self.parent_scan_interval * 60


# noinspection PyUnusedLocal
class Gateway3(Thread, GatewayV, GatewayMesh, GatewayStats):
    pair_model = None
    pair_payload = None

    def __init__(self, host: str, token: str, config: dict, **options):
        super().__init__(daemon=True)

        self.host = host
        self.options = options

        self.miio = SyncmiIO(host, token)

        self.mqtt = Client()
        self.mqtt.on_connect = self.on_connect
        self.mqtt.on_disconnect = self.on_disconnect
        self.mqtt.on_message = self.on_message
        self.mqtt.connect_async(host)

        self._ble = options.get('ble')  # for fast access
        self._debug = options.get('debug', '')  # for fast access
        self.parent_scan_interval = options.get('parent')  # for fast access
        self.default_devices = config['devices']

        self.devices = {}
        self.updates = {}
        self.setups = {}
        self.stats = {}

    @property
    def device(self):
        return self.devices['lumi.0']

    def add_update(self, did: str, handler):
        """Add handler to device update event."""
        self.updates.setdefault(did, []).append(handler)

    def remove_update(self, did: str, handler):
        self.updates.setdefault(did, []).remove(handler)

    def add_setup(self, domain: str, handler):
        """Add hass device setup funcion."""
        self.setups[domain] = handler

    def debug(self, message: str):
        _LOGGER.debug(f"{self.host} | {message}")

    def stop(self):
        self.enabled = False
        self.mqtt.loop_stop()

    def run(self):
        """Main thread loop."""
        self.enabled = True
        while self.enabled:
            # if not telnet - enable it
            if not self._check_port(23) and not self._enable_telnet():
                time.sleep(30)
                continue

            devices = self._prepeare_gateway(with_devices=True)
            if devices:
                self.setup_devices(devices)
                break

        self.mesh_start()

        while self.enabled:
            # if not telnet - enable it
            if not self._check_port(23) and not self._enable_telnet():
                time.sleep(30)
                continue

            # if not mqtt - enable it (handle Mi Home and ZHA mode)
            if not self._mqtt_connect() and not self._prepeare_gateway():
                time.sleep(60)
                continue

            self.mqtt.loop_forever()

    def _check_port(self, port: int):
        """Check if gateway port open."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            return s.connect_ex((self.host, port)) == 0
        finally:
            s.close()

    def _enable_telnet(self):
        """Enable telnet with miio protocol."""
        if self.miio.send("enable_telnet_service") != 'ok':
            self.debug(f"Can't enable telnet")
            return False
        return True

    def _prepeare_gateway(self, with_devices: bool = False):
        """Launching the required utilities on the hub, if they are not already
        running.
        """
        self.debug("Prepare Gateway")
        try:
            shell = TelnetShell(self.host)

            self.ver = shell.get_version()
            self.debug(f"Version: {self.ver}")

            ps = shell.get_running_ps()

            if "mosquitto -d" not in ps:
                self.debug("Run public mosquitto")
                shell.run_public_mosquitto()

            # all data or only necessary events
            pattern = '\\{"' if 'miio' in self._debug \
                else "ble_event|properties_changed|heartbeat"

            if f"awk /{pattern} {{" not in ps:
                self.debug(f"Redirect miio to MQTT")
                shell.redirect_miio2mqtt(pattern, self.ver_miio)

            if self.options.get('buzzer'):
                if "basic_gw -b" in ps:
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

                if (self.parent_scan_interval is not None and
                        "Lumi_Z3GatewayHost_MQTT -n 1 -b 115200 -v" not in ps):
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
        raw = shell.read_file('/data/zigbee/coordinator.info')
        device = json.loads(raw)
        devices = [{
            'did': 'lumi.0',
            'model': 'lumi.gateway.mgl03',
            'mac': device['mac'],
            'type': 'gateway',
            'init': {
                'firmware lock': shell.check_firmware_lock()
            }
        }]

        # 2. Read zigbee devices
        if not self.options.get('zha'):
            raw = shell.read_file('/data/zigbee_gw/' + self.ver_zigbee_db,
                                  as_base64=True)
            if raw.startswith(b'unqlite'):
                db = Unqlite(raw)
                data = db.read_all()
            else:
                raw = re.sub(br'}\s+{', b',', raw)
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

                device = {
                    'did': did,
                    'mac': '0x' + data[did + '.mac'],
                    'model': data[did + '.model'],
                    'type': 'zigbee',
                    'zb_ver': data[did + '.version'],
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

                rows = db.read_table(self.ver_mesh_group)
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
                rows = db.read_table('mesh_device')
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
        if 'mqtt' in self._debug:
            self.debug(f"[MQ] {msg.topic} {msg.payload.decode()}")

        if msg.topic == 'zigbee/send':
            payload = json.loads(msg.payload)
            self.process_message(payload)

        elif msg.topic == 'log/miio':
            if 'miio' in self._debug:
                self.debug(f"[MI] {msg.payload}")

            if self._ble and (
                    b'_async.ble_event' in msg.payload or
                    b'properties_changed' in msg.payload or
                    b'event.gw.heartbeat' in msg.payload
            ):
                try:
                    for raw in utils.extract_jsons(msg.payload):
                        if b'_async.ble_event' in raw:
                            data = json.loads(raw)['params']
                            self.process_ble_event(data)
                            self.process_ble_stats(data)
                        elif b'properties_changed' in raw:
                            data = json.loads(raw)['params']
                            self.debug(f"Process props {data}")
                            self.process_mesh_data(data)
                        elif b'event.gw.heartbeat' in raw:
                            payload = json.loads(raw)['params'][0]
                            self.process_gw_stats(payload)
                except:
                    _LOGGER.warning(f"Can't read BT: {msg.payload}")

        elif msg.topic.endswith('/heartbeat'):
            payload = json.loads(msg.payload)
            self.process_gw_stats(payload)

        elif msg.topic.endswith(('/MessageReceived', '/devicestatechange')):
            payload = json.loads(msg.payload)
            self.process_zb_stats(payload)

        # read only retained ble
        elif msg.topic.startswith('ble') and msg.retain:
            payload = json.loads(msg.payload)
            self.process_ble_retain(msg.topic[4:], payload)

        elif self.pair_model and msg.topic.endswith('/commands'):
            self.process_pair(msg.payload)

    def setup_devices(self, devices: list):
        """Add devices to hass."""
        for device in devices:
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

                    # wait domain init
                    while domain not in self.setups:
                        time.sleep(1)

                    attr = param[2]
                    self.setups[domain](self, device, attr)

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

                # wait domain init
                while 'light' not in self.setups:
                    time.sleep(1)

                self.setups['light'](self, device, 'light')

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
                while 'sensor' not in self.setups:
                    time.sleep(1)
                self.setups['sensor'](self, device, device['type'])

    def process_message(self, data: dict):
        if data['cmd'] == 'heartbeat':
            # don't know if only one item
            assert len(data['params']) == 1, data

            data = data['params'][0]
            pkey = 'res_list'
        elif data['cmd'] == 'report':
            pkey = 'params' if 'params' in data else 'mi_spec'
        elif data['cmd'] in ('write_rsp', 'read_rsp'):
            pkey = 'results'
        elif data['cmd'] == 'write_ack':
            return
        else:
            _LOGGER.warning(f"Unsupported cmd: {data}")
            return

        did = data['did']

        # skip without callback
        if did not in self.updates:
            return

        device = self.devices[did]
        payload = {}

        # convert codes to names
        for param in data[pkey]:
            if param.get('error_code', 0) != 0:
                continue

            prop = param['res_name'] if 'res_name' in param else \
                f"{param['siid']}.{param['piid']}"

            if prop in GLOBAL_PROP:
                prop = GLOBAL_PROP[prop]
            else:
                prop = next((
                    p[2] for p in (device['params'] or device['mi_spec'])
                    if p[0] == prop
                ), prop)

            if prop in ('temperature', 'humidity', 'pressure'):
                payload[prop] = param['value'] / 100.0
            elif prop == 'battery' and param['value'] > 1000:
                # xiaomi light sensor
                payload[prop] = round((min(param['value'], 3200) - 2500) / 7)
            elif prop == 'alive':
                # {'res_name':'8.0.2102','value':{'status':'online','time':0}}
                device['online'] = (param['value']['status'] == 'online')
            elif prop == 'angle':
                # xiaomi cube 100 points = 360 degrees
                payload[prop] = param['value'] * 4
            elif prop == 'duration':
                # xiaomi cube
                payload[prop] = param['value'] / 1000.0
            elif prop in ('consumption', 'power'):
                payload[prop] = round(param['value'], 2)
            else:
                payload[prop] = param['value']

        self.debug(f"{device['did']} {device['model']} <= {payload}")

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

        if isinstance(data['evt'], list):
            # check if only one
            assert len(data['evt']) == 1, data
            payload = bluetooth.parse_xiaomi_ble(data['evt'][0], pdid)
        elif isinstance(data['evt'], dict):
            payload = bluetooth.parse_xiaomi_ble(data['evt'], pdid)
        else:
            payload = None

        if payload is None:
            self.debug(f"Unsupported BLE {data}")
            return

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

            # wait domain init
            while domain not in self.setups:
                time.sleep(1)

            self.setups[domain](self, device, k)

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
            # don't retain action
            if k in device['init'] or k == 'action':
                continue

            device['init'][k] = payload[k]

            domain = bluetooth.get_ble_domain(k)
            if not domain:
                continue

            # wait domain init
            while domain not in self.setups:
                time.sleep(1)

            self.setups[domain](self, device, k)

        if did in self.updates:
            for handler in self.updates[did]:
                handler(payload)

    def process_pair(self, raw: bytes):
        # get shortID and eui64 of paired device
        if b'lumi send-nwk-key' in raw:
            # create model response
            payload = f"0x18010105000042{len(self.pair_model):02x}" \
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

        # send model response "from device"
        elif b'zdo active ' in raw:
            mac = self.device['mac'][2:].upper()
            self.mqtt.publish(f"gw/{mac}/MessageReceived", self.pair_payload)

    def send(self, device: dict, data: dict):
        payload = {'cmd': 'write', 'did': device['did']}

        # convert hass prop to lumi prop
        if device['mi_spec']:
            params = []
            for k, v in data.items():
                if k == 'switch':
                    v = bool(v)
                k = next(p[0] for p in device['mi_spec'] if p[2] == k)
                params.append({'siid': k[0], 'piid': k[1], 'value': v})

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
            mac = self.device['mac'][2:].upper()
            self.mqtt.publish(f"gw/{mac}/publishstate")

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
