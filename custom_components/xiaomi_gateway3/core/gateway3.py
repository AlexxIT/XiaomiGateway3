import asyncio
import json
import logging
import re
import socket
import time
from pathlib import Path
from typing import Optional

import yaml

from . import bluetooth, utils, zigbee
from .helpers import DevicesRegistry
from .mini_miio import AsyncMiIO
from .mini_mqtt import MiniMQTT, MQTTMessage
from .shell import TelnetShell, ntp_time
from .unqlite import Unqlite, SQLite

_LOGGER = logging.getLogger(__name__)

RE_NWK_KEY = re.compile(r'lumi send-nwk-key (0x.+?) {(.+?)}')

TELNET_CMD = '{"method":"enable_telnet_service","params":""}'


class GatewayBase(DevicesRegistry):
    did: str = None
    """Xiaomi did of the gateway"""

    available: bool = None
    """Getaway is considered online if there is an active connection to mqtt"""
    enabled: bool = None
    """Gateway stops main loop if enabled property sets to False"""

    host: str = None

    options: dict = None

    # TODO: remove this prop
    gw_topic: str = None

    mqtt: MiniMQTT = None
    miio: AsyncMiIO = None

    @property
    def debug_mode(self):
        return self.options.get('debug', '')

    @property
    def device(self):
        return self.devices[self.did]

    def debug(self, message: str):
        # basic logs
        if 'true' in self.debug_mode:
            _LOGGER.debug(f"{self.host} | {message}")


class GatewayMesh(GatewayBase):
    mesh_params: list = None
    mesh_ts: float = 0

    def mesh_start(self):
        self.mesh_params = []

        for device in self.devices.values():
            if device['type'] == 'mesh' and 'childs' not in device:
                # TODO: rewrite more clear logic for lights and switches
                p = device['miot_spec'][0]
                self.mesh_params.append({
                    'did': device['did'], 'siid': p[0], 'piid': p[1]
                })

        if self.mesh_params:
            self.mesh_ts = time.time() + 30
            asyncio.create_task(self.mesh_run_forever())

    async def mesh_run_forever(self):
        self.debug("Start Mesh Thread")

        while self.enabled:
            if time.time() < self.mesh_ts:
                await asyncio.sleep(1)
                continue

            try:
                resp = await self.miio.send_bulk(
                    'get_properties', self.mesh_params
                )
                if resp:
                    params2 = []
                    for item in resp:
                        if 'value' not in item:
                            continue

                        did = item['did']
                        device_params = self.devices[did]['miot_spec']
                        # get other props for turn on lights or live switches
                        if device_params[0][3] == 'switch' or item['value']:
                            params2 += [{
                                'did': did, 'siid': p[0], 'piid': p[1]
                            } for p in device_params[1:]]

                    if params2:
                        resp2 = await self.miio.send_bulk(
                            'get_properties', params2
                        )
                        if resp2:
                            resp += resp2

                    self.debug(f"Pull Mesh {resp}")
                    asyncio.create_task(self.process_mesh_data(resp))

                else:
                    self.debug("Can't get mesh bulb state")

            except Exception as e:
                self.debug(f"ERROR in mesh thread {e}")

            self.mesh_ts = time.time() + 30

    async def process_mesh_data(self, data: list):
        """Can receive multiple properties from multiple devices.

           data = [{'did':123,'siid':2,'piid':1,'value:True}]
        """
        bulk = {}

        for param in data:
            code = param.get('code', 0)
            if code == -4004:
                # handle device offline state
                param['value'] = None
            elif code != 0:
                continue

            did = param['did']
            if did not in self.devices:
                continue

            device = self.devices[did]

            prop = next((
                p[2] for p in device['miot_spec']
                if p[0] == param['siid'] and p[1] == param['piid']
            ), None)
            if not prop:
                continue

            if did not in bulk:
                bulk[did] = {}

            # TODO: fix this dirty hack
            if device['model'] == 3083 and prop == 'power' and param['value']:
                param['value'] /= 100.0

            # https://github.com/AlexxIT/XiaomiGateway3/issues/312
            if prop in ('temperature', 'humidity') and param['value']:
                param['value'] = round(param['value'], 2)

            bulk[did][prop] = param['value']

        for did, payload in bulk.items():
            # self.debug(f"Process Mesh Data for {did}: {payload}")
            device = self.devices[did]
            for entity in device['entities'].values():
                if entity:
                    await entity.async_update(payload)

    async def send_mesh(self, device: dict, data: dict):
        # data = {'light':True}
        payload = []
        for k, v in data.items():
            param = next(
                p for p in device['miot_spec']
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
            if await self.miio.send('set_properties', payload):
                self.mesh_force_update()
        except:
            self.debug(f"Can't send mesh {device['did']} => {data}")

    def mesh_force_update(self):
        self.mesh_ts = time.time() + 2


class GatewayStats(GatewayMesh):
    # global stats for all gateways
    # stats: dict = {}
    parent_scan_ts: float = 0

    # interval for auto parent refresh in minutes, 0 - disabled auto refresh
    # -1 - disabled
    parent_scan_interval: Optional[int] = None

    # collected data from MQTT topic log/z3 (zigbee console)
    z3buffer: Optional[dict] = None

    @property
    def stats_enable(self):
        return self.options.get('stats')

    async def process_gw_stats(self, payload: dict = None):
        # empty payload - update available state
        self.debug(f"gateway <= {payload or self.available}")

        if self.parent_scan_ts and time.time() > self.parent_scan_ts:
            # block any auto updates in 30 seconds
            self.parent_scan_ts = time.time() + 30

            await self.get_gateway_info()

        device = self.devices.get(self.did)
        if not device or not device.get('stats'):
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
                d, h, m, s = (s // (3600 * 24), s % (3600 * 24) // 3600,
                              s % 3600 // 60, s % 60)

                payload = {
                    'free_mem': payload['free_mem'],
                    'load_avg': payload['load_avg'],
                    'rssi': -payload['rssi'],
                    'uptime': f"{d} days, {h:02}:{m:02}:{s:02}",
                }

        await device['stats'].async_update(payload)

    async def process_zb_stats(self, payload: dict):
        # convert ieee to did
        did = 'lumi.' + str(payload['eui64']).lstrip('0x').lower()
        device = self.devices.get(did)
        if device and device.get('stats'):
            await device['stats'].async_update(payload)

    async def process_ble_stats(self, mac: str, data: dict = None):
        device = self.devices.get(mac)
        if device and device.get('stats'):
            await device['stats'].async_update(data)

    async def process_z3(self, payload: str):
        if payload.startswith("CLI command executed"):
            cmd = payload[22:-1]
            if cmd == "debugprint all_on" or self.z3buffer is None:
                # reset all buffers
                self.z3buffer = {}
            else:
                self.z3buffer[cmd] = self.z3buffer['buffer']

            self.z3buffer['buffer'] = ''

            if cmd == "plugin concentrator print-table":
                await self.process_gateway_info()

        elif self.z3buffer:
            self.z3buffer['buffer'] += payload

    async def get_gateway_info(self):
        self.debug("Update zigbee network info")
        payload = {'commands': [
            {'commandcli': "debugprint all_on"},
            {'commandcli': "plugin device-table print"},
            {'commandcli': "plugin stack-diagnostics child-table"},
            {'commandcli': "plugin stack-diagnostics neighbor-table"},
            {'commandcli': "plugin concentrator print-table"},
            {'commandcli': "debugprint all_off"},
        ]}
        await self.mqtt.publish(self.gw_topic + 'commands', payload)

    async def send_zigbee_cli(self, commands: list):
        payload = {'commands': [{'commandcli': cmd} for cmd in commands]}
        await self.mqtt.publish(self.gw_topic + 'commands', payload)

    async def process_gateway_info(self):
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

                nwk = i[0]  # FFFF
                ago = int(i[2])
                type_ = 'device' if i[1] in m2 else \
                    'router' if i[1] in m3 else '-'
                parent = '0x' + m4[nwk][0].lower() if nwk in m4 else '-'
                nwk = '0x' + nwk.lower()  # 0xffff

                payload = {
                    'eui64': ieee,
                    'nwk': nwk,
                    'ago': ago,
                    'type': type_,
                    'parent': parent
                }

                did = 'lumi.' + str(payload['eui64']).lstrip('0x').lower()
                device = self.devices.get(did)
                if device and device.get('stats'):
                    # the device remains in the gateway database after deletion
                    # and may appear on another gw with another nwk
                    if nwk == device.get('nwk'):
                        await self.process_zb_stats(payload)
                    else:
                        self.debug(f"Zigbee device with wrong NWK: {ieee}")
                else:
                    self.debug(f"Unknown zigbee device {ieee}: {payload}")

            # one hour later
            if self.parent_scan_interval > 0:
                self.parent_scan_ts = time.time() + self.parent_scan_interval * 60

        except Exception as e:
            self.debug(f"Can't update parents: {e}")


class GatewayBLE(GatewayStats):
    async def process_ble_event(self, data: dict):
        self.debug(f"Process BLE {data}")

        mac = data['dev']['mac'].replace(':', '').lower() \
            if 'mac' in data['dev'] else data['dev']['did']

        if mac not in self.devices:
            # some devices doesn't send mac, only number did
            # https://github.com/AlexxIT/XiaomiGateway3/issues/24
            device = self.find_or_create_device({
                'did': data['dev'].get('did'),
                'mac': mac,
                'model': data['dev']['pdid'],
                'type': 'ble',
                'init': {}
            })
        else:
            device = self.devices[mac]

        if device.get('seq') == data['frmCnt']:
            return
        device['seq'] = data['frmCnt']

        pdid = data['dev'].get('pdid')

        if isinstance(data['evt'], list):
            # check if only one
            assert len(data['evt']) == 1, data
            payload = bluetooth.parse_xiaomi_ble(data['evt'][0], pdid)
        elif isinstance(data['evt'], dict):
            payload = bluetooth.parse_xiaomi_ble(data['evt'], pdid)
        else:
            payload = None

        if payload:
            await self.process_ble_payload(device, payload)

    async def process_ble_event_fix(self, data: dict):
        self.debug(f"Process BLE Fix {data}")

        device = next((
            device for device in self.devices.values()
            if device['did'] == data['did']
        ), None)

        if not device:
            self.debug(f"Unregistered BLE device {data}")
            return

        if device.get('seq') == data['seq']:
            return
        device['seq'] = data['seq']

        payload = bluetooth.parse_xiaomi_ble(data, data['pdid'])
        if payload:
            await self.process_ble_payload(device, payload)

    async def process_ble_payload(self, device: dict, payload: dict):
        mac = device['mac']

        # init entities if needed
        init = device['init']
        for k in payload.keys():
            # update for retain
            init[k] = payload[k]

            if k in device['entities']:
                continue

            domain = bluetooth.get_ble_domain(k)
            self.add_entity(domain, device, k)

        for entity in device['entities'].values():
            if entity:
                await entity.async_update(payload)

        if self.stats_enable:
            self.add_stats(device)

        await self.process_ble_stats(mac)

        raw = json.dumps(init, separators=(',', ':'))
        await self.mqtt.publish(f"ble/{mac}", raw, retain=True)

    async def process_ble_retain(self, mac: str, payload: dict):
        if mac not in self.devices:
            self.debug(f"BLE device {mac} is no longer on the gateway")
            return

        self.debug(f"{mac} retain: {payload}")

        device = self.devices[mac]

        # init entities if needed
        for k in payload.keys():
            # don't retain action and motion
            if k in device['entities']:
                continue

            if k in ('action', 'motion'):
                device['init'][k] = ''
            else:
                device['init'][k] = payload[k]

            domain = bluetooth.get_ble_domain(k)
            self.add_entity(domain, device, k)

        for entity in device['entities'].values():
            if entity:
                await entity.async_update(payload)


class GatewayNetwork(GatewayBLE):
    @property
    def telnet_cmd(self):
        return self.options.get('telnet_cmd') or TELNET_CMD

    async def check_port(self, port: int):
        """Check if gateway port open."""
        try:
            coro = asyncio.open_connection(self.host, port)
            await asyncio.wait_for(coro, 2)
            return True
        except:
            return False

    async def enable_telnet(self):
        """Enable telnet with miio protocol."""
        raw = json.loads(self.telnet_cmd)
        if await self.miio.send(raw['method'], raw.get('params')) != ['ok']:
            self.debug(f"Can't enable telnet")
            return False
        return True


# noinspection PyUnusedLocal
class GatewayEntry(GatewayNetwork):
    """Main class for working with the gateway via Telnet (23), MQTT (1883) and
    miIO (54321) protocols.
    """
    time_offset = 0
    pair_model = None
    pair_payload = None
    pair_payload2 = None

    def __init__(self, host: str, token: str, **options):
        self.host = host
        self.options = options

        self.miio = AsyncMiIO(host, token)
        self.mqtt = MiniMQTT()

        if 'true' in self.debug_mode:
            self.miio.debug = True

        self.setups = {}

    @property
    def ble_mode(self):
        return self.options.get('ble', True)

    @property
    def zha_mode(self):
        return self.options.get('zha', False)

    @property
    def parent_scan_interval(self):
        return self.options.get('parent', -1)

    def start(self):
        asyncio.create_task(self.run_forever())

    async def stop(self):
        self.enabled = False
        await self.mqtt.disconnect()

        for device in self.devices.values():
            if self in device['gateways']:
                device['gateways'].remove(self)

    async def run_forever(self):
        self.debug("Start main loop")

        """Main thread loop."""
        self.enabled = True
        while self.enabled:
            # if not telnet - enable it
            if not await self.check_port(23) and \
                    not await self.enable_telnet():
                await asyncio.sleep(30)
                continue

            if not self.did:
                devices = await self.get_devices()
                if not devices:
                    await asyncio.sleep(60)
                    continue

                self.setup_devices(devices)
                await self.update_time_offset()
                self.mesh_start()

            # if not mqtt - enable it (handle Mi Home and ZHA mode)
            if not await self.prepare_gateway() or \
                    not await self.mqtt.connect(self.host):
                await asyncio.sleep(60)
                continue

            await self.on_connect()
            async for msg in self.mqtt:
                asyncio.create_task(self.on_message(msg))
            await self.on_disconnect()

        self.debug("Stop main thread")

    async def on_connect(self):
        self.debug("MQTT connected")

        await self.mqtt.subscribe('#')

        self.available = True
        await self.process_gw_stats()
        await self.update_entities_states()

    async def on_message(self, msg: MQTTMessage):
        try:
            topic = msg.topic

            if 'mqtt' in self.debug_mode:
                _LOGGER.debug(f"{self.host} | MQTT | {topic} {msg.payload}")

            if topic == 'zigbee/send':
                await self.process_zigbee_message(msg.json)

            elif topic == 'log/miio':
                # don't need to process another data
                if b'ot_agent_recv_handler_one' not in msg.payload:
                    return

                for raw in utils.extract_jsons(msg.payload):
                    if self.ble_mode and b'_async.ble_event' in raw:
                        data = json.loads(raw)['params']
                        await self.process_ble_event(data)
                    elif self.ble_mode and b'properties_changed' in raw:
                        data = json.loads(raw)['params']
                        self.debug(f"Process props {data}")
                        await self.process_mesh_data(data)
                    elif b'event.gw.heartbeat' in raw:
                        payload = json.loads(raw)['params'][0]
                        await self.process_gw_stats(payload)
                        # time offset may changed right after gw.heartbeat
                        await self.update_time_offset()

            elif topic == 'log/ble':
                await self.process_ble_event_fix(msg.json)

            elif topic == 'log/z3':
                await self.process_z3(msg.text)

            elif topic.endswith('/heartbeat'):
                await self.process_gw_stats(msg.json)

            elif topic.endswith(('/MessageReceived', '/devicestatechange')):
                await self.process_zb_stats(msg.json)

            # read only retained ble
            elif topic.startswith('ble') and msg.retain:
                await self.process_ble_retain(topic[4:], msg.json)

            elif self.pair_model and topic.endswith('/commands'):
                await self.process_pair(msg.payload)

        except:
            _LOGGER.exception(f"Processing MQTT: {msg.topic} {msg.payload}")

    async def on_disconnect(self):
        self.debug("MQTT disconnected")

        self.available = False
        await self.process_gw_stats()
        await self.update_entities_states()

    async def get_devices(self):
        """Load devices info for Coordinator, Zigbee and Mesh."""
        try:
            shell = TelnetShell()
            if not await shell.connect(self.host) or not await shell.login():
                return None

            # 1. Read coordinator info
            raw = await shell.read_file('/data/zigbee/coordinator.info')
            device = json.loads(raw)
            devices = [{
                'did': await shell.get_did(),
                'model': 'lumi.gateway.mgl03',
                'mac': device['mac'],
                'wlan_mac': await shell.get_wlan_mac(),
                'type': 'gateway',
                'fw_ver': shell.ver,
                'online': True,
                'init': {
                    'firmware lock': await shell.check_firmware_lock(),
                }
            }]

            # 2. Read zigbee devices
            if not self.zha_mode:
                raw = await shell.read_file('/data/zigbee/device.info')
                lumi = json.loads(raw)['devInfo']

                # read Xiaomi devices DB
                raw = await shell.read_file(shell.zigbee_db, as_base64=True)
                # self.debug(f"Devices RAW: {raw}")
                if raw is None:
                    self.debug("No zigbee database")
                    xiaomi = {}
                elif raw.startswith(b'unqlite'):
                    db = Unqlite(raw)
                    xiaomi = db.read_all()
                else:
                    raw = re.sub(br'}\s*{', b',', raw)
                    xiaomi = json.loads(raw)

                for item in lumi:
                    did = item['did']
                    model = item['model']
                    desc = zigbee.get_device(model)

                    # skip unknown model
                    if desc is None:
                        self.debug(f"{did} has an unsupported modell: {model}")
                        continue

                    try:
                        retain = json.loads(xiaomi[did + '.prop'])['props']
                    except:
                        self.debug(f"{did} is not in the Xiaomi database")
                        continue

                    self.debug(f"{did} {model} retain: {retain}")

                    params = {
                        p[2]: retain.get(p[1])
                        for p in (desc['lumi_spec'] or desc['miot_spec'])
                        if p[1] is not None
                    }

                    ver = f"mod: {item['model_ver']} hw: {item['hardVer']} " \
                          f"fw: {item['appVer']}"

                    device = {
                        'did': did,
                        'mac': item['mac'],  # 0xff without leading zeroes
                        'nwk': item['shortId'],  # 0xffff
                        'model': model,
                        'type': 'zigbee',
                        'fw_ver': ver,
                        'init': zigbee.fix_xiaomi_props(model, params),
                        'online': retain.get('alive', 1) == 1
                    }
                    devices.append(device)

            # 3. Read bluetooth devices
            if self.ble_mode:
                raw = await shell.read_file('/data/miio/mible_local.db',
                                            as_base64=True)
                try:
                    db = SQLite(raw)

                    # load BLE devices
                    rows = db.read_table('gateway_authed_table')
                    for row in rows:
                        device = {
                            'did': row[4],
                            'mac': utils.reverse_mac(row[1]),
                            'model': row[2],
                            'type': 'ble',
                            'online': True,
                            'init': {}
                        }
                        devices.append(device)

                    # load Mesh groups
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
                            'type': 'mesh',
                            'online': True
                        }
                        devices.append(device)

                        group_addr = row[1]
                        mesh_groups[group_addr] = device

                    # load Mesh bulbs
                    rows = db.read_table(shell.mesh_device_table)
                    for row in rows:
                        device = {
                            'did': row[0],
                            'mac': row[1].replace(':', ''),
                            'model': row[2],
                            'type': 'mesh',
                            'online': False
                        }
                        devices.append(device)

                        group_addr = row[5]
                        if group_addr in mesh_groups:
                            # add bulb to group if exist
                            mesh_groups[group_addr]['childs'].append(row[0])

                except:
                    _LOGGER.exception("Can't read mesh devices")

            # for testing purposes
            for k, v in self.defaults.items():
                if k[0] == '_':
                    devices.append(v)

            return devices

        except (ConnectionRefusedError, socket.timeout):
            return None

        except Exception as e:
            _LOGGER.exception(f"{self.host} | Can't read devices: {e}")
            return None

    async def prepare_gateway(self):
        """Launching the required utilities on the hub, if they are not already
        running.
        """
        self.debug("Prepare Gateway")
        try:
            shell = TelnetShell()
            if not await shell.connect(self.host) or not await shell.login():
                return False

            self.debug(f"Version: {shell.ver}")

            ps = await shell.get_running_ps()

            if "mosquitto -d" not in ps:
                self.debug("Run public mosquitto")
                await shell.run_public_mosquitto()

            if "ntpd" not in ps:
                # run NTPd for sync time
                await shell.run_ntpd()

            if await shell.check_bt():
                if "-t log/ble" not in ps:
                    self.debug("Run fixed BT")
                    await shell.run_bt()
            else:
                self.debug("Fixed BT don't supported")

            if "-t log/miio" not in ps:
                # all data or only necessary events
                pattern = (
                    '\\{"' if 'miio' in self.debug_mode else
                    "ot_agent_recv_handler_one.+"
                    "ble_event|properties_changed|heartbeat"
                )
                self.debug(f"Redirect miio to MQTT")
                await shell.redirect_miio2mqtt(pattern)

            if self.options.get('buzzer'):
                if "dummy:basic_gw" not in ps:
                    self.debug("Disable buzzer")
                    await shell.stop_buzzer()
            else:
                if "dummy:basic_gw" in ps:
                    self.debug("Enable buzzer")
                    await shell.run_buzzer()

            if self.zha_mode:
                # stop lumi without checking if it's running
                await shell.stop_lumi_zigbee()

                if "tcp-l:8889" in ps:
                    await shell.stop_zigbee_tcp()
                if "tcp-l:8888" not in ps:
                    self.debug("Run Zigbee TCP")
                    await shell.run_zigbee_tcp()

            else:
                # check both 8888 and 8889
                if "tcp-l:888" in ps:
                    self.debug("Stop Zigbee TCP")
                    await shell.stop_zigbee_tcp()

                if self.parent_scan_interval >= 0:
                    if "Lumi_Z3GatewayHost_MQTT -n 1 -b 115200 -l" not in ps:
                        self.debug("Run public Zigbee console")
                        await shell.run_public_zb_console()

                    if self.parent_scan_interval > 0:
                        self.parent_scan_ts = 1

                elif "daemon_app.sh" not in ps:
                    self.debug("Run Lumi Zigbee")
                    await shell.run_lumi_zigbee()

            await shell.close()

            return True

        except (ConnectionRefusedError, socket.timeout):
            return False

        except Exception as e:
            self.debug(f"Can't prepare gateway: {e}")
            return False

    async def update_time_offset(self):
        gw_time = await asyncio.get_event_loop().run_in_executor(
            None, ntp_time, self.host
        )
        if gw_time:
            self.time_offset = gw_time - time.time()
            self.debug(f"Gateway time offset: {self.time_offset}")

    async def lock_firmware(self, enable: bool):
        self.debug(f"Set firmware lock to {enable}")
        try:
            shell = TelnetShell()
            if not await shell.connect(self.host) or not await shell.login():
                return False
            await shell.lock_firmware(enable)
            locked = await shell.check_firmware_lock()
            await shell.close()
            return enable == locked

        except Exception as e:
            self.debug(f"Can't set firmware lock: {e}")
            return False

    async def update_entities_states(self):
        for device in list(self.devices.values()):
            if self in device['gateways']:
                for entity in list(device['entities'].values()):
                    if entity:
                        entity.async_write_ha_state()

    def setup_devices(self, devices: list):
        """Add devices to hass."""
        for device in devices:
            type_ = device['type']
            self.debug(f"Setup {type_} device {device}")

            device = self.find_or_create_device(device)

            if type_ == 'gateway':
                self.did = device['did']
                self.gw_topic = f"gw/{device['mac'][2:].upper()}/"

            if type_ == 'gateway' and self.zha_mode:
                # only firmware lock
                param = device['lumi_spec'][-1]
                self.add_entity(param[3], device, param[2])

            elif type_ in ('gateway', 'zigbee', 'mesh'):
                for param in device['lumi_spec'] or []:
                    self.add_entity(param[3], device, param[2])
                for param in device['miot_spec'] or []:
                    self.add_entity(param[3], device, param[2])

            if self.stats_enable and type_ in ('gateway', 'zigbee'):
                self.add_stats(device)

    async def process_zigbee_message(self, data: dict):
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
        if did not in self.devices or pkey not in data:
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

            if prop in zigbee.GLOBAL_PROP:
                prop = zigbee.GLOBAL_PROP[prop]
            else:
                prop = next((
                    p[2] for p in (device['lumi_spec'] or device['miot_spec'])
                    if p[0] == prop
                ), prop)

            # https://github.com/Koenkk/zigbee2mqtt/issues/798
            # https://www.maero.dk/aqara-temperature-humidity-pressure-sensor-teardown/
            if (prop == 'temperature' and
                    device['model'] != 'lumi.airmonitor.acn01'):
                if -4000 < param['value'] < 12500:
                    payload[prop] = param['value'] / 100.0
            elif (prop == 'humidity' and
                  device['model'] != 'lumi.airmonitor.acn01'):
                if 0 <= param['value'] <= 10000:
                    payload[prop] = param['value'] / 100.0
            elif prop == 'pressure':
                payload[prop] = param['value'] / 100.0
            elif prop == 'battery':
                # I do not know if the formula is correct, so battery is more
                # important than voltage
                payload[prop] = zigbee.fix_xiaomi_battery(param['value'])
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
            elif prop in ('voltage', 'current'):
                payload[prop] = round(param['value'] / 1000.0, 2)
            elif prop == 'energy':
                # energy consumption Wh to kWh
                payload[prop] = round(param['value'] / 1000.0, 3)
            elif prop == 'fw_ver' and param['value'] != device['fw_ver']:
                device['fw_ver'] = param['value']
                self.update_device_fw_ver(device, param['value'])
            elif prop == 'ota_progress':
                self.update_device_fw_ver(device, f"Update {param['value']}%")
            elif 'value' in param:
                payload[prop] = param['value']
            elif 'arguments' in param:
                d = yaml.safe_load(prop)
                if isinstance(d, dict):
                    payload.update(d)
                else:
                    payload[prop] = param['arguments']

        # no time in device add command
        ts = round(ts - data['time'] * 0.001 + self.time_offset, 2) \
            if 'time' in data else '?'
        self.debug(f"{device['did']} {device['model']} <= {payload} [{ts}]")

        if payload:
            device['online'] = True

        for entity in device['entities'].values():
            if entity:
                await entity.async_update(payload)

        # TODO: move code earlier!!!
        if 'added_device' in payload:
            # {'did': 'lumi.fff', 'mac': 'fff', 'model': 'lumi.sen_ill.mgl01',
            # 'version': '21', 'zb_ver': '3.0'}
            device = payload['added_device']
            device['mac'] = '0x' + device['mac']
            device['type'] = 'zigbee'
            device['init'] = payload
            self.setup_devices([device])

        # return for tests purpose
        return payload

    @staticmethod
    def update_device_fw_ver(device: dict, fw_ver: str):
        for entity in device['entities'].values():
            if entity:
                utils.update_device_info(
                    entity.hass, device['did'], sw_version=fw_ver
                )
                break

    async def process_pair(self, raw: bytes):
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
            await self.mqtt.publish(self.gw_topic + 'MessageReceived',
                                    self.pair_payload2)
            await self.mqtt.publish(self.gw_topic + 'MessageReceived',
                                    self.pair_payload)

    async def send_zigbee(self, device: dict, data: dict):
        did = device['did'] if device['did'] != self.did else 'lumi.0'
        payload = {'cmd': 'write', 'did': did}

        # convert hass prop to lumi prop
        if device['miot_spec']:
            try:
                params = []
                for k, v in data.items():
                    k = next(p[0] for p in device['miot_spec'] if p[2] == k)
                    if k == 'switch':
                        v = bool(v)
                    params.append({
                        'siid': int(k[0]), 'piid': int(k[2]), 'value': v
                    })

                # Attention! mi_spec are used in payload
                payload['mi_spec'] = params
            except StopIteration:
                pass

        # lumi_spec and miot_spec persist simultaneously only in gateway
        if device['lumi_spec']:
            try:
                params = [{
                    'res_name': next(
                        p[0] for p in device['lumi_spec'] if p[2] == k
                    ),
                    'value': v
                } for k, v in data.items()]

                payload['params'] = params
            except StopIteration:
                pass

        self.debug(f"{device['did']} {device['model']} => {payload}")
        await self.mqtt.publish('zigbee/recv', payload)

    async def send_telnet(self, *args: str):
        shell = TelnetShell()
        if not await shell.connect(self.host) or not await shell.login():
            return

        for command in args:
            if command == 'ftp':
                shell.run_ftp()
            elif command == 'dump':
                raw = await shell.tar_data()
                filename = Path().absolute() / f"{self.host}.tar.gz"
                with open(filename, 'wb') as f:
                    f.write(raw)
            else:
                await shell.exec(command)

        await shell.close()

    async def send_mqtt(self, cmd: str):
        if cmd == 'publishstate':
            await self.mqtt.publish(self.gw_topic + 'publishstate', '')

    def get_device(self, mac: str) -> Optional[dict]:
        for device in self.devices.values():
            if device.get('mac') == mac:
                return device
        return None


Gateway3 = GatewayEntry
