from . import miot
from .base import GatewayBase, SIGNAL_PREPARE_GW, SIGNAL_MQTT_PUB
from .. import shell
from ..device import XDevice, BLE
from ..mini_mqtt import MQTTMessage


# noinspection PyMethodMayBeStatic,PyUnusedLocal
class BLEGateway(GatewayBase):
    def ble_init(self):
        if not self.ble_mode:
            return
        self.dispatcher_connect(SIGNAL_PREPARE_GW, self.ble_prepare_gateway)
        self.dispatcher_connect(SIGNAL_MQTT_PUB, self.ble_mqtt_publish)

    async def ble_read_devices(self, sh: shell.ShellMGW):
        try:
            # prevent read database two times
            db = await sh.read_db_bluetooth()

            # load BLE devices
            rows = sh.db.read_table('gateway_authed_table')
            for row in rows:
                # BLE key is mac
                mac = reverse_mac(row[1])
                device = self.devices.get(mac)
                if not device:
                    device = XDevice(BLE, row[2], row[4], mac)
                self.add_device(mac, device)
        except Exception:
            pass

    async def ble_prepare_gateway(self, sh: shell.ShellMGW):
        if self.available is None:
            await self.ble_read_devices(sh)

        if self.options.get('memory') and sh.model == "mgw":
            self.debug("Init Bluetooth in memory storage")
            sh.patch_memory_bluetooth()

    async def ble_mqtt_publish(self, msg: MQTTMessage):
        if msg.topic == "miio/report" and b'"_async.ble_event"' in msg.payload:
            await self.ble_process_event(msg.json["params"])

    async def ble_process_event(self, data: dict):
        # {'dev': {'did': 'blt.3.xxx', 'mac': 'AA:BB:CC:DD:EE:FF', 'pdid': 2038},
        # 'evt': [{'eid': 15, 'edata': '010000'}],
        # 'frmCnt': 36, 'gwts': 1636208932}

        # some devices doesn't send mac, only number did
        # https://github.com/AlexxIT/XiaomiGateway3/issues/24
        if 'mac' in data['dev']:
            mac = data['dev']['mac'].replace(':', '').lower()
            device = self.devices.get(mac)
            if not device:
                device = XDevice(
                    BLE, data['dev']['pdid'], data['dev']['did'], mac
                )
                self.add_device(mac, device)
        else:
            device = next((
                d for d in self.devices.values() if d.did == data['dev']['did']
            ), None)
            if not device:
                self.debug(f"Unregistered BLEE device {data}")
                return

        if device.extra.get('seq') == data['frmCnt']:
            return
        device.extra['seq'] = data['frmCnt']

        if isinstance(data['evt'], list):
            payload = data['evt'][0]
        elif isinstance(data['evt'], dict):
            payload = data['evt']
        else:
            raise NotImplementedError

        if BLE in device.entities:
            device.update(device.decode(BLE, payload))

        payload = device.decode("mibeacon", payload)
        device.update(payload)
        self.debug_device(device, "recv", payload, "BLEE")


def reverse_mac(s: str):
    return f"{s[10:]}{s[8:10]}{s[6:8]}{s[4:6]}{s[2:4]}{s[:2]}"
