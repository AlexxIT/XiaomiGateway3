import base64
import json
import logging
import re
import socket
import time
from telnetlib import Telnet
from threading import Thread
from typing import Optional, Union

from paho.mqtt.client import Client, MQTTMessage
from . import ble, utils
from .miio_fix import Device
from .unqlite import Unqlite
from .utils import GLOBAL_PROP

_LOGGER = logging.getLogger(__name__)


class Gateway3(Thread):
    def __init__(self, host: str, token: str, config: dict):
        super().__init__(daemon=True)

        self.host = host
        self.miio = Device(host, token)

        self.mqtt = Client()
        self.mqtt.on_connect = self.on_connect
        self.mqtt.on_disconnect = self.on_disconnect
        self.mqtt.on_message = self.on_message
        self.mqtt.connect_async(host)

        self.ble = GatewayBLE(self)

        self.debug = config['debug'] if 'debug' in config else ''
        self.devices = config['devices'] if 'devices' in config else {}
        self.updates = {}
        self.setups = {}

    @property
    def device(self):
        return self.devices['lumi.0']

    def add_update(self, did: str, handler):
        """Add handler to device update event."""
        self.updates.setdefault(did, []).append(handler)

    def add_setup(self, domain: str, handler):
        """Add hass device setup funcion."""
        self.setups[domain] = handler

    def run(self):
        """Main loop"""
        while 'lumi.0' not in self.devices:
            if self._miio_connect():
                devices = self._get_devices_v3()
                if devices:
                    self.setup_devices(devices)
                else:
                    self._enable_telnet()
            else:
                time.sleep(30)

        # start bluetooth read loop
        self.ble.start()

        while True:
            if self._mqtt_connect():
                self.mqtt.loop_forever()

            elif self._miio_connect() and self._enable_telnet():
                self._enable_mqtt()

            else:
                _LOGGER.debug("sleep 30")
                time.sleep(30)

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
            _LOGGER.debug(f"{self.host} | Can't send handshake")
            return False

    def _get_devices_v1(self) -> Optional[list]:
        """Load devices via miio protocol."""
        _LOGGER.debug(f"{self.host} | Read devices")
        try:
            devices = {}

            # endless loop protection
            for _ in range(16):
                # load only 8 device per part
                part = self.miio.send('get_device_list', retry_count=10)
                if len(part) == 0:
                    return []

                for item in part:
                    devices[item['num']] = {
                        'did': item['did'],
                        'mac': f"0x{item['did'][5:]}",
                        'model': item['model'],
                    }

                if part[0]['total'] == len(devices):
                    break

            devices = list(devices.values())
            for device in devices:
                desc = utils.get_device(device['model'])
                # skip unknown model
                if desc is None:
                    continue
                # get xiaomi param names
                params = [p[1] for p in desc['params'] if p[1] is not None]
                # skip if don't have retain params
                if not params:
                    continue
                # load param values
                values = self.miio.send('get_device_prop',
                                        [device['did']] + params)
                # get hass param names
                params = [p[2] for p in desc['params'] if p[1] is not None]

                data = dict(zip(params, values))
                # fix some param values
                for k, v in data.items():
                    if k in ('temperature', 'humidity'):
                        data[k] = v / 100.0
                    elif v in ('on', 'open'):
                        data[k] = 1
                    elif v in ('off', 'close'):
                        data[k] = 0

                device['init'] = data

            device = self.miio.info()
            devices.append({
                'did': 'lumi.0',
                'mac': device.mac_address,  # wifi mac!!!
                'model': device.model
            })

            return devices

        except Exception as e:
            _LOGGER.exception(f"{self.host} | Get devices: {e}")
            return None

    def _get_devices_v2(self) -> Optional[list]:
        """Load device list via Telnet.

        Device desc example:
          mac: '0x158d0002c81234'
          shortId: '0x0691'
          manuCode: '0x115f'
          model: 'lumi.sensor_ht'
          did: 'lumi.158d0002c81234'
          devType: 0
          appVer: 2
          hardVer: 0
          devID: 770
          status: 0
          model_ver: 2
        """
        _LOGGER.debug(f"{self.host} | Read devices")
        try:
            telnet = Telnet(self.host)
            telnet.read_until(b"login: ")
            telnet.write(b"admin\r\n")
            telnet.read_until(b'\r\n# ')  # skip greeting

            telnet.write(b"cat /data/zigbee/coordinator.info\r\n")
            telnet.read_until(b'\r\n')  # skip command
            raw = telnet.read_until(b'# ')
            device = json.loads(raw[:-2])
            device.update({
                'did': 'lumi.0',
                'model': 'lumi.gateway.mgl03',
                'host': self.host
            })

            devices = [device]

            telnet.write(b"cat /data/zigbee/device.info\r\n")
            telnet.read_until(b'\r\n')  # skip command
            raw = telnet.read_until(b'# ')
            raw = json.loads(raw[:-2])
            devices += raw['devInfo']
            telnet.close()

            return devices
        except Exception as e:
            _LOGGER.exception(f"Can't read devices: {e}")
            return None

    def _get_devices_v3(self):
        """Load device list via Telnet."""
        _LOGGER.debug(f"{self.host} | Read devices")
        try:
            telnet = Telnet(self.host, timeout=5)
            telnet.read_until(b"login: ")
            telnet.write(b"admin\r\n")
            telnet.read_until(b'\r\n# ')  # skip greeting

            # https://github.com/AlexxIT/XiaomiGateway3/issues/14
            # fw 1.4.6_0012 and below have one zigbee_gw.db file
            # fw 1.4.6_0030 have many json files in this folder
            telnet.write(b"cat /data/zigbee_gw/* | base64\r\n")
            telnet.read_until(b'\r\n')  # skip command
            raw = telnet.read_until(b'# ')
            raw = base64.b64decode(raw)
            if raw.startswith(b'unqlite'):
                db = Unqlite(raw)
                data = db.read_all()
            else:
                raw = re.sub(br'}\s+{', b',', raw)
                data = json.loads(raw)

            devices = []

            # data = {} or data = {'dev_list': 'null'}
            dev_list = json.loads(data.get('dev_list', 'null')) or []
            _LOGGER.debug(f"{self.host} | Load {len(dev_list)} zigbee devices")

            for did in dev_list:
                model = data[did + '.model']
                desc = utils.get_device(model)

                # skip unknown model
                if desc is None:
                    _LOGGER.debug(f"Unsupported model: {model}")
                    continue

                retain = json.loads(data[did + '.prop'])['props']
                _LOGGER.debug(f"{self.host} | {model} retain: {retain}")

                params = {
                    p[2]: retain.get(p[1])
                    for p in desc['params']
                    if p[1] is not None
                }

                # fix some param values
                for k, v in params.items():
                    if k in ('temperature', 'humidity'):
                        params[k] = v / 100.0
                    elif v in ('on', 'open'):
                        params[k] = 1
                    elif v in ('off', 'close'):
                        params[k] = 0
                    elif k == 'battery' and v and v > 1000:
                        params[k] = round((min(v, 3200) - 2500) / 7)

                device = {
                    'did': did,
                    'mac': '0x' + data[did + '.mac'],
                    'model': data[did + '.model'],
                    'type': 'zigbee',
                    'zb_ver': data[did + '.version'],
                    'init': params
                }
                devices.append(device)

            telnet.write(b"cat /data/zigbee/coordinator.info\r\n")
            telnet.read_until(b'\r\n')  # skip command
            raw = telnet.read_until(b'# ')

            device = json.loads(raw[:-2])
            devices.insert(0, {
                'did': 'lumi.0',
                'model': 'lumi.gateway.mgl03',
                'mac': device['mac'],
                'type': 'gateway'
            })

            return devices

        except (ConnectionRefusedError, socket.timeout):
            return None

        except Exception as e:
            _LOGGER.debug(f"Can't read devices: {e}")
            return None

    def _enable_telnet(self):
        _LOGGER.debug(f"{self.host} | Try enable telnet")
        try:
            resp = self.miio.send("enable_telnet_service")
            return resp[0] == 'ok'
        except Exception as e:
            _LOGGER.exception(f"Can't enable telnet: {e}")
            return False

    def _enable_mqtt(self):
        _LOGGER.debug(f"{self.host} | Try run public MQTT")
        try:
            telnet = Telnet(self.host)
            telnet.read_until(b"login: ")
            telnet.write(b"admin\r\n")
            telnet.read_very_eager()  # skip response

            # enable public mqtt
            telnet.write(b"killall mosquitto\r\n")
            telnet.read_very_eager()  # skip response
            time.sleep(.5)
            telnet.write(b"mosquitto -d\r\n")
            telnet.read_very_eager()  # skip response
            time.sleep(1)

            telnet.close()
            return True
        except Exception as e:
            _LOGGER.debug(f"Can't run MQTT: {e}")
            return False

    def on_connect(self, client, userdata, flags, rc):
        _LOGGER.debug(f"{self.host} | MQTT connected")
        self.mqtt.subscribe('#')

    def on_disconnect(self, client, userdata, rc):
        _LOGGER.debug(f"{self.host} | MQTT disconnected")
        # force end mqtt.loop_forever()
        self.mqtt.disconnect()

    def on_message(self, client: Client, userdata, msg: MQTTMessage):
        if 'mqtt' in self.debug:
            _LOGGER.debug(f"[MQ] {msg.topic} {msg.payload.decode()}")

        if msg.topic == 'zigbee/send':
            payload = json.loads(msg.payload)
            self.process_message(payload)

    def setup_devices(self, devices: list):
        """Add devices to hass."""
        for device in devices:
            desc = utils.get_device(device['model'])
            if not desc:
                _LOGGER.debug(f"Unsupported model: {device}")
                continue

            _LOGGER.debug(f"{self.host} | Setup device {device['model']}")

            device.update(desc)

            # update params from config
            default_config = self.devices.get(device['mac'])
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

    def process_message(self, data: dict):
        if data['cmd'] == 'heartbeat':
            # don't know if only one item
            assert len(data['params']) == 1, data

            data = data['params'][0]
            pkey = 'res_list'
        elif data['cmd'] == 'report':
            pkey = 'params' if 'params' in data else 'mi_spec'
        elif data['cmd'] == 'write_rsp':
            pkey = 'results'
        else:
            raise NotImplemented(f"Unsupported cmd: {data}")

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

            if prop in ('temperature', 'humidity'):
                payload[prop] = param['value'] / 100.0
            elif prop == 'battery' and param['value'] > 1000:
                payload[prop] = round((min(param['value'], 3200) - 2500) / 7)
            else:
                payload[prop] = param['value']

        _LOGGER.debug(f"{self.host} | {device['did']} {device['model']} <= "
                      f"{payload}")

        for handler in self.updates[did]:
            handler(payload)

        if 'added_device' in payload:
            # {'did': 'lumi.fff', 'mac': 'fff', 'model': 'lumi.sen_ill.mgl01',
            # 'version': '21', 'zb_ver': '3.0'}
            device = payload['added_device']
            device['mac'] = '0x' + device['mac']
            self.setup_devices([device])

    def process_ble_event(self, raw: Union[bytes, str]):
        data = json.loads(raw[10:])['params'] \
            if isinstance(raw, bytes) else json.loads(raw)

        _LOGGER.debug(f"{self.host} | Process BLE {data}")

        did = data['dev']['did']
        if did not in self.devices:
            mac = data['dev']['mac'].replace(':', '').lower() \
                if 'mac' in data['dev'] else \
                'ble_' + did.replace('blt.3.', '')
            self.devices[did] = device = {
                'did': did, 'mac': mac, 'init': {}, 'device_name': "BLE",
                'type': 'ble'}
        else:
            device = self.devices[did]

        if isinstance(data['evt'], list):
            # check if only one
            assert len(data['evt']) == 1, data
            payload = ble.parse_xiaomi_ble(data['evt'][0])
        elif isinstance(data['evt'], dict):
            payload = ble.parse_xiaomi_ble(data['evt'])
        else:
            payload = None

        if payload is None:
            _LOGGER.debug(f"Unsupported BLE {data}")
            return

        # init entities if needed
        for k in payload.keys():
            if k in device['init']:
                continue

            device['init'][k] = payload[k]

            domain = ble.get_ble_domain(k)
            if not domain:
                continue

            # wait domain init
            while domain not in self.setups:
                time.sleep(1)

            self.setups[domain](self, device, k)

        if did in self.updates:
            for handler in self.updates[did]:
                handler(payload)

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

        _LOGGER.debug(f"{self.host} | {device['did']} {device['model']} => "
                      f"{payload}")

        payload = json.dumps(payload, separators=(',', ':')).encode()
        self.mqtt.publish('zigbee/recv', payload)


class GatewayBLE(Thread):
    def __init__(self, gw: Gateway3):
        super().__init__(daemon=True)
        self.gw = gw

    def run(self):
        _LOGGER.debug(f"{self.gw.host} | Start BLE ")
        while True:
            try:
                telnet = Telnet(self.gw.host, timeout=5)
                telnet.read_until(b"login: ")
                telnet.write(b"admin\r\n")
                telnet.read_until(b'\r\n# ')  # skip greeting

                telnet.write(b"killall silabs_ncp_bt; "
                             b"silabs_ncp_bt /dev/ttyS1 1\r\n")
                telnet.read_until(b'\r\n')  # skip command

                while True:
                    raw = telnet.read_until(b'\r\n')

                    if 'bluetooth' in self.gw.debug:
                        _LOGGER.debug(f"[BT] {raw}")

                    if b'_async.ble_event' in raw:
                        self.gw.process_ble_event(raw)

            except (ConnectionRefusedError, ConnectionResetError,
                    socket.timeout):
                pass
            except Exception as e:
                _LOGGER.exception(f"Bluetooth loop error: {e}")

            time.sleep(30)


def is_gw3(host: str, token: str) -> Optional[str]:
    try:
        device = Device(host, token)
        info = device.info()
        if info.model != 'lumi.gateway.mgl03':
            raise Exception(f"Wrong device model: {info.model}")
    except Exception as e:
        return str(e)

    return None
