import time

from .base import XGateway
from ..const import MESH, GROUP
from ..mini_mqtt import MQTTMessage
from ..shell.shell_mgw import ShellMGW


# noinspection PyMethodMayBeStatic,PyUnusedLocal
class MeshGateway(XGateway):
    async def mesh_read_devices(self, sh: ShellMGW):
        try:
            # prevent read database two times
            db = await sh.read_db_bluetooth()

            childs = {}

            # load Mesh bulbs
            rows = sh.db.read_table("mesh_device_v3")
            for row in rows:
                did = row[0]
                device = self.devices.get(did)
                if not device:
                    mac = row[1].lower()  # aa:bb:cc:dd:ee:ff
                    model = row[2]
                    device = self.init_device(model, did=did, mac=mac, type=MESH)
                self.add_device(device)

                # add bulb to group address
                childs.setdefault(row[5], []).append(did)

            # load Mesh groups
            rows = sh.db.read_table("mesh_group_v3")
            for row in rows:
                did = "group." + row[0]
                device = self.devices.get(did)
                if not device:
                    model = row[2]
                    device = self.init_device(model, did=did, type=GROUP)
                # update childs of device
                device.extra["childs"] = childs.get(row[1])
                self.add_device(device)

        except Exception as e:
            self.debug("Can't read mesh DB", exc_info=e)

    def mesh_on_mqtt_publish(self, msg: MQTTMessage):
        if msg.topic == "miio/report":
            if b'"_sync.ble_mesh_keep_alive"' in msg.payload:
                self.mesh_process_keepalive(msg.json["params"])
            elif b'"_sync.ble_mesh_offline"' in msg.payload:
                self.mesh_process_offline(msg.json["params"]["list"])
            # elif b'"_sync.ble_mesh_query_dev"' in msg.payload:
            #     self.mesh_process_query_dev(msg.json["params"])

    def mesh_process_keepalive(self, data: list):
        # "params":[{"did":"123","rssi":-52,"hops":0,"ts":123}],
        ts = int(time.time())

        for item in data:
            if device := self.devices.get(item["did"]):
                # noinspection PyTypedDict
                device.extra["rssi_" + self.device.uid] = item["rssi"]
                device.on_keep_alive(self, ts)

    def mesh_process_offline(self, data: list):
        for item in data:
            if device := self.devices.get(item["did"]):
                self.debug("ble_mesh_offline", device=device)
                device.last_seen.pop(self.device, None)
                device.update()
