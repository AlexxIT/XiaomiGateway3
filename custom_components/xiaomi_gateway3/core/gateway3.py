import json
import logging
import re
import socket
import time
from threading import Thread
from typing import Optional, Union

from paho.mqtt.client import Client, MQTTMessage
from . import bluetooth, utils
from .miio_fix import Device
from .shell import TelnetShell
from .unqlite import Unqlite, SQLite
from .utils import GLOBAL_PROP

_LOGGER = logging.getLogger(__name__)

RE_NWK_KEY = re.compile(r'lumi send-nwk-key (0x.+?) {(.+?)}')
RE_MAC = re.compile('^0x0*')
# MAC reverse
RE_REVERSE = re.compile(r'(..)(..)(..)(..)(..)(..)')


class Gateway3(Thread):
    pair_model = None
    pair_payload = None

    def __init__(self, host: str, token: str, config: dict, ble: bool = True,
                 zha: bool = False):
        super().__init__(daemon=True)

        self.host = host
        self.ble = ble
        self.zha = zha

        self.miio = Device(host, token)

        self.mqtt = Client()
        self.mqtt.on_connect = self.on_connect
        self.mqtt.on_disconnect = self.on_disconnect
        self.mqtt.on_message = self.on_message
        self.mqtt.connect_async(host)

        self._debug = config['debug'] if 'debug' in config else ''
        self._disable_buzzer = config.get('buzzer') is False
        self.default_devices = config['devices']

        self.devices = {}
        self.updates = {}
        self.setups = {}

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

    def run(self):
        """Main thread loop."""
        while True:
            # if not telnet - enable it
            if not self._check_port(23) and not self._enable_telnet():
                time.sleep(30)
                continue

            devices = self._prepeare_gateway(with_devices=True)
            if devices:
                self.setup_devices(devices)
                break

        while True:
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
        self.debug("Try enable telnet")
        try:
            resp = self.miio.send("enable_telnet_service")
            return resp[0] == 'ok'
        except Exception as e:
            self.debug(f"Can't enable telnet: {e}")
            return False

    def _prepeare_gateway(self, with_devices: bool = False):
        """Launching the required utilities on the hub, if they are not already
        running.
        """
        self.debug("Prepare Gateway")
        try:
            shell = TelnetShell(self.host)
            ps = shell.get_running_ps()

            if "mosquitto -d" not in ps:
                self.debug("Run public mosquitto")
                shell.run_public_mosquitto()

            # all data or only necessary events
            pattern = '\\{"' if 'miio' in self._debug \
                else "ble_event|properties_changed"

            if f"awk /{pattern} {{" not in ps:
                new_version = 'FILE_STORE' in ps
                self.debug(f"Redirect miio to MQTT, new: {new_version}")
                shell.redirect_miio2mqtt(pattern, new_version)

            if self._disable_buzzer and "basic_gw -b" in ps:
                _LOGGER.debug("Disable buzzer")
                shell.stop_buzzer()

            if self.zha:
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

                if "Lumi_Z3GatewayHost_MQTT" not in ps:
                    self.debug("Run Lumi Zigbee")
                    shell.run_lumi_zigbee()
            # elif "Lumi_Z3GatewayHost_MQTT -n 1 -b 115200 -v" not in ps:
            #     self.debug("Run public Zigbee console")
            #     shell.run_public_zb_console()

            if with_devices:
                self.debug("Get devices")
                return self._get_devices(shell)

            return True

        except (ConnectionRefusedError, socket.timeout):
            return False

        except Exception as e:
            _LOGGER.debug(f"Can't read devices: {e}")
            return False

    def _mqtt_connect(self) -> bool:
        try:
            self.mqtt.reconnect()
            return True
        except:
            return False

    def _miio_connect(self) -> bool:
        try:
            self.miio.send_handshake()
            return True
        except:
            self.debug("Can't send handshake")
            return False

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
        if not self.zha:
            # https://github.com/AlexxIT/XiaomiGateway3/issues/14
            # fw 1.4.6_0012 and below have one zigbee_gw.db file
            # fw 1.4.6_0030 have many json files in this folder
            raw = shell.read_file('/data/zigbee_gw/*', as_base64=True)
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
                    for p in desc['params']
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
        if self.ble:
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

                rows = db.read_table('mesh_group')
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

        self.process_gw_message({'online': True})

    def on_disconnect(self, client, userdata, rc):
        self.debug("MQTT disconnected")
        # force end mqtt.loop_forever()
        self.mqtt.disconnect()

        self.process_gw_message({'online': False})

    def on_message(self, client: Client, userdata, msg: MQTTMessage):
        if 'mqtt' in self._debug:
            self.debug(f"[MQ] {msg.topic} {msg.payload.decode()}")

        if msg.topic == 'zigbee/send':
            payload = json.loads(msg.payload)
            self.process_message(payload)

        elif msg.topic == 'log/miio':
            if 'miio' in self._debug:
                _LOGGER.debug(f"[MI] {msg.payload}")

            if self.ble and (
                    b'_async.ble_event' in msg.payload or
                    b'properties_changed' in msg.payload
            ):
                try:
                    for raw in utils.extract_jsons(msg.payload):
                        if b'_async.ble_event' in raw:
                            self.process_ble_event(raw)
                        elif b'properties_changed' in raw:
                            self.process_mesh_data(raw)
                except:
                    _LOGGER.warning(f"Can't read BT: {msg.payload}")

        elif msg.topic.endswith('/heartbeat'):
            payload = json.loads(msg.payload)
            self.process_gw_message(payload)

        elif msg.topic.endswith('/MessageReceived'):
            payload = json.loads(msg.payload)
            self.process_zb_message(payload)

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
                default_config = self.default_devices.get(device['mac']) or \
                                 self.default_devices.get(device['did'])
                if default_config:
                    device.update(default_config)

                self.devices[device['did']] = device

                for param in device['params']:
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
                prop = next((p[2] for p in device['params']
                             if p[0] == prop), prop)

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

    def process_gw_message(self, payload: dict):
        self.debug(f"gateway <= {payload}")

        if 'lumi.0' not in self.updates:
            return

        if 'networkUp' in payload:
            payload = {
                'network_pan_id': payload['networkPanId'],
                'radio_tx_power': payload['radioTxPower'],
                'radio_channel': payload['radioChannel'],
            }
        elif 'online' in payload:
            self.device['online'] = payload['online']

        for handler in self.updates['lumi.0']:
            handler(payload)

    def process_zb_message(self, payload: dict):
        did = 'lumi.' + RE_MAC.sub('', payload['eui64']).lower()
        if did not in self.devices:
            return
        device = self.devices[did]
        device['linq_quality'] = payload['linkQuality']
        self.debug(f"{did} <= LQI {payload['linkQuality']}")

    def process_ble_event(self, raw: Union[bytes, str]):
        if isinstance(raw, bytes):
            data = json.loads(raw)['params']
        else:
            data = json.loads(raw)

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
            _LOGGER.debug(f"BLE device {did} is no longer on the gateway")
            return

        _LOGGER.debug(f"{did} retain: {payload}")

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

    def process_mesh_data(self, raw: Union[bytes, list]):
        if isinstance(raw, bytes):
            data = json.loads(raw)['params']
        else:
            data = raw

        # not always Mesh devices
        self.debug(f"Process Mesh* {data}")

        data = bluetooth.parse_xiaomi_mesh(data)
        for did, payload in data.items():
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
        # convert hass prop to lumi prop
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

    def send_mesh(self, device: dict, data: dict):
        did = device['did']
        payload = bluetooth.pack_xiaomi_mesh(did, data)
        return self.miio.send('set_properties', payload)

    def get_device(self, mac: str) -> Optional[dict]:
        for device in self.devices.values():
            if device.get('mac') == mac:
                return device
        return None


def is_gw3(host: str, token: str) -> Optional[str]:
    try:
        device = Device(host, token)
        info = device.info()
        if info.model != 'lumi.gateway.mgl03':
            raise Exception(f"Wrong device model: {info.model}")
    except Exception as e:
        return str(e)

    return None
