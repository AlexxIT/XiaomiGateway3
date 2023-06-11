from datetime import datetime, timezone
from typing import TYPE_CHECKING

from .base import Converter
from .const import GATEWAY, ZIGBEE, BLE, MESH

if TYPE_CHECKING:
    from ..device import XDevice

ZIGBEE_CLUSTERS = {
    0x0000: "Basic",
    0x0001: "PowerCfg",
    0x0003: "Identify",
    0x0006: "OnOff",
    0x0008: "LevelCtrl",
    0x000A: "Time",
    0x000C: "AnalogInput",  # cube, gas sensor
    0x0012: "Multistate",
    0x0019: "OTA",  # illuminance sensor
    0x0101: "DoorLock",
    0x0300: "LightColor",
    0x0400: "Illuminance",  # motion sensor
    0x0402: "Temperature",
    0x0403: "Pressure",
    0x0405: "Humidity",
    0x0406: "Occupancy",  # motion sensor
    0x0500: "IasZone",  # gas sensor
    0x0B04: "ElectrMeasur",
    0xFCC0: "Xiaomi",
}

BLE_EVENTS = {
    0x0006: "LockFinger",
    0x0007: "LockDoor",
    0x0008: "LockArmed",
    0x000B: "LockAction",
    0x000F: "Motion",
    0x0010: "Toothbrush",
    0x1001: "Action",
    0x1002: "Sleep",
    0x1003: "RSSI",
    0x1004: "Temperature",
    0x1005: "Kettle",
    0x1006: "Humidity",
    0x1007: "Illuminance",
    0x1008: "Moisture",
    0x1009: "Conductivity",
    0x100A: "Battery",
    0x100D: "TempHum",
    0x100E: "Lock",
    0x100F: "Door",
    0x1010: "Formaldehyde",
    0x1012: "Opening",
    0x1013: "Supply",
    0x1014: "WaterLeak",
    0x1015: "Smoke",
    0x1016: "Gas",
    0x1017: "IdleTime",
    0x1018: "Light",
    0x1019: "Contact",
    0x4803: "Battery2",
    0x4C01: "Temperature2",
    0x4C08: "Humidity2",
}


class GatewayStatsConverter(Converter):
    childs = {
        "network_pan_id",
        "radio_tx_power",
        "radio_channel",
        "free_mem",
        "load_avg",
        "rssi",
        "uptime",
        "gateway",
        "miio",
        "openmiio",
        "serial",
        "zigbee",
    }

    def decode(self, device: "XDevice", payload: dict, value: dict):
        if "networkUp" in value:
            payload.update(
                {
                    "network_pan_id": value.get("networkPanId"),
                    "radio_tx_power": value.get("radioTxPower"),
                    "radio_channel": value.get("radioChannel"),
                }
            )

        if "free_mem" in value:
            s = value["run_time"]
            d = s // (3600 * 24)
            h = s % (3600 * 24) // 3600
            m = s % 3600 // 60
            s = s % 60
            # fw 1.5.4 has negative (right rssi), lower fw - don't
            rssi = value["rssi"] if value["rssi"] <= 0 else value["rssi"] - 100
            payload.update(
                {
                    "free_mem": value["free_mem"],
                    "load_avg": value["load_avg"],
                    "rssi": rssi,
                    "uptime": f"{d} days, {h:02}:{m:02}:{s:02}",
                }
            )

        if "openmiio" in value:
            payload.update(value)


class ZigbeeStatsConverter(Converter):
    childs = {
        "ieee",
        "nwk",
        "msg_received",
        "msg_missed",
        "linkquality",
        "rssi",
        "last_msg",
        "type",
        "parent",
        "new_resets",
    }

    def decode(self, device: "XDevice", payload: dict, value: dict):
        if "sourceAddress" in value:
            cid = int(value["clusterId"], 0)

            if "msg_received" in device.extra:
                device.extra["msg_received"] += 1
            else:
                device.extra.update({"msg_received": 1, "msg_missed": 0})

            # For some devices better works APSCounter, for other - sequence
            # number in payload. Sometimes broken messages arrived.
            try:
                raw = value["APSPlayload"]
                manufact_spec = int(raw[2:4], 16) & 4
                new_seq1 = int(value["APSCounter"], 0)
                new_seq2 = int(raw[8:10] if manufact_spec else raw[4:6], 16)
                # new_seq2 == 0 -> probably device reset
                if "last_seq1" in device.extra and new_seq2 != 0:
                    miss = min(
                        (new_seq1 - device.extra["last_seq1"] - 1) & 0xFF,
                        (new_seq2 - device.extra["last_seq2"] - 1) & 0xFF,
                    )
                    # sometimes device repeat message, skip this situation:
                    # 0xF6 > 0xF7 > 0xF8 > 0xF7 > 0xF8 > 0xF9
                    if 0 < miss < 240:
                        device.extra["msg_missed"] += miss

                device.extra["last_seq1"] = new_seq1
                device.extra["last_seq2"] = new_seq2
            except Exception:
                pass

            payload.update(
                {
                    ZIGBEE: datetime.now(timezone.utc),
                    # 'ieee': value['eui64'],
                    # 'nwk': value['sourceAddress'],
                    "msg_received": device.extra["msg_received"],
                    "msg_missed": device.extra["msg_missed"],
                    "linkquality": value["linkQuality"],
                    "rssi": value["rssi"],
                    "last_msg": ZIGBEE_CLUSTERS.get(cid, cid),
                }
            )

        # if 'ago' in value:
        #     payload.update({
        #         ZIGBEE: dt.now() - timedelta(seconds=value['ago']),
        #         'type': value['type'],
        #     })

        if "parent" in value:
            payload["parent"] = value["parent"]

        # if 'resets' in value:
        #     if 'resets0' not in device.extra:
        #         device.extra['resets0'] = value['resets']
        #     payload['new_resets'] = value['resets'] - device.extra['resets0']


class BLEStatsConv(Converter):
    childs = {"mac", "msg_received", "last_msg"}

    def decode(self, device: "XDevice", payload: dict, value: dict):
        if "msg_received" in device.extra:
            device.extra["msg_received"] += 1
        else:
            device.extra["msg_received"] = 1

        eid = value.get("eid")

        payload.update(
            {
                BLE: datetime.now(timezone.utc),
                "mac": device.mac,
                "msg_received": device.extra["msg_received"],
                "last_msg": BLE_EVENTS.get(eid, eid),
            }
        )


class MeshStatsConv(Converter):
    childs = {"mac", "msg_received", "last_msg"}

    def decode(self, device: "XDevice", payload: dict, value: list):
        if "msg_received" in device.extra:
            device.extra["msg_received"] += 1
        else:
            device.extra["msg_received"] = 1

        param = value[0]
        if "piid" in param:
            prop = f"{param['siid']}.p.{param['piid']}"
        elif "eiid" in param:
            prop = f"{param['siid']}.e.{param['eiid']}"
        else:
            raise NotImplementedError

        payload.update(
            {
                MESH: datetime.now(timezone.utc),
                "mac": device.mac,
                "msg_received": device.extra["msg_received"],
                "last_msg": prop,
            }
        )


GatewayStats = GatewayStatsConverter(GATEWAY, "binary_sensor")

STAT_GLOBALS = {
    # GATEWAY: GatewayStats,
    BLE: BLEStatsConv(BLE, "sensor"),
    MESH: MeshStatsConv(MESH, "sensor"),
    ZIGBEE: ZigbeeStatsConverter(ZIGBEE, "sensor"),
}
