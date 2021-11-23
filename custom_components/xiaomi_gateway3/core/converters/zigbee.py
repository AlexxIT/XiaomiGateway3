import math
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING, Optional

import zigpy.device
import zigpy.quirks
from zigpy.const import SIG_ENDPOINTS
from zigpy.device import Device

from .base import Config, Converter, MathConv
from .silabs import *

if TYPE_CHECKING:
    from .devices import XDevice

CL_POWER = 0x1
CL_ILLUMINANCE = 0x400
CL_TEMPERATURE = 0x402
CL_OCCUPANCY = 0x406


def generate_device(manufacturer: str, model: str) -> Optional[Device]:
    """Generate device from quirks. Should be called earlier:
        zhaquirks.setup()

    Or direct import:
        from zhaquirks.xiaomi.mija.sensor_switch import MijaButton

    Used like a Cluster:
        hdr, value = device.deserialize(<endpoint_id>, <cluster_id>, data)
    """
    quirks = zigpy.quirks.get_quirk_list(manufacturer, model)
    if not quirks:
        return None

    device = Device(None, None, 0)
    device.manufacturer = manufacturer
    device.model = model

    quirk: zigpy.quirks.CustomDevice = quirks[0]
    if SIG_ENDPOINTS in quirk.replacement:
        for endpoint_id in quirk.replacement[SIG_ENDPOINTS].keys():
            device.add_endpoint(endpoint_id)

    return quirks[0](None, None, 0, device)


################################################################################
# Base (global) converters
################################################################################

@dataclass
class ZOnOffConv(Converter):
    ep: int = 1
    zigbee = "on_off"

    def decode(self, device: 'XDevice', payload: dict, value: dict):
        if value["endpoint"] == self.ep and "on_off" in value:
            payload[self.attr] = bool(value["on_off"])

    def encode(self, device: "XDevice", payload: dict, value: bool):
        cmd = zcl_on_off(device.nwk, self.ep, value)
        payload.setdefault("commands", []).extend(cmd)

    def read(self, device: "XDevice", payload: dict):
        cmd = zcl_read(device.nwk, self.ep, 6, 0)
        payload.setdefault("commands", []).extend(cmd)


@dataclass
class ZBrightnessConv(Converter):
    ep: int = 1
    zigbee = "level"

    def decode(self, device: "XDevice", payload: dict, value: dict):
        if "current_level" in value:
            payload[self.attr] = value["current_level"]

    def encode(self, device: "XDevice", payload: dict, value: Any):
        # brightness and transition in seconds
        if not isinstance(value, tuple):
            value = (value, 1)  # default transition
        cmd = zcl_level(device.nwk, self.ep, *value)
        payload.setdefault("commands", []).extend(cmd)

    def read(self, device: "XDevice", payload: dict):
        cmd = zcl_read(device.nwk, self.ep, 8, 0)
        payload.setdefault("commands", []).extend(cmd)


@dataclass
class ZColorTempConv(Converter):
    ep: int = 1
    zigbee = "light_color"

    min: int = 153
    max: int = 500

    def decode(self, device: "XDevice", payload: dict, value: Any):
        if "color_temperature" in value:
            payload[self.attr] = value["color_temperature"]

    def encode(self, device: "XDevice", payload: dict, value: Any):
        if not isinstance(value, tuple):
            value = (value, 1)  # default transition
        cmd = zcl_color(device.nwk, self.ep, *value)
        payload.setdefault("commands", []).extend(cmd)

    def read(self, device: "XDevice", payload: dict):
        cmd = zcl_read(device.nwk, self.ep, 0x0300, 0)
        payload.setdefault("commands", []).extend(cmd)


@dataclass
class ZElectricalConv(MathConv):
    zigbee = "electrical_measurement"
    zattr: str = None

    def decode(self, device: "XDevice", payload: dict, value: dict):
        if self.zattr in value:
            super().decode(device, payload, value[self.zattr])

    def read(self, device: "XDevice", payload: dict):
        # voltage, current, power
        cmd = zcl_read(device.nwk, 1, 0x0B04, [1285, 1288, 1291])
        payload.setdefault("commands", []).extend(cmd)


@dataclass
class ZIlluminance(Converter):
    ep: int = 1
    zigbee = "illuminance"

    def decode(self, device: 'XDevice', payload: dict, value: dict):
        if isinstance(value.get("measured_value"), int):
            payload[self.attr] = value['measured_value'] / 100

    def read(self, device: "XDevice", payload: dict):
        cmd = zcl_read(device.nwk, self.ep, 0x400, [0])
        payload.setdefault("commands", []).extend(cmd)


@dataclass
class ZOccupancyConv(Converter):
    ep: int = 1
    zigbee = "occupancy"

    def decode(self, device: 'XDevice', payload: dict, value: Any):
        if isinstance(value.get("occupancy"), int):
            payload[self.attr] = bool(value["occupancy"])

    def read(self, device: "XDevice", payload: dict):
        cmd = zcl_read(device.nwk, self.ep, 0x406, [0])
        payload.setdefault("commands", []).extend(cmd)


class ZAnalogInput(Converter):
    zigbee = "analog_input"

    def decode(self, device: 'XDevice', payload: dict, value: dict):
        if isinstance(value.get("present_value"), float):
            payload[self.attr] = round(value['present_value'], 2)


class ZIASZoneConv(Converter):
    zigbee = "ias_zone"

    def decode(self, device: "XDevice", payload: dict, value: dict):
        value = value.get("value")
        if isinstance(value, list) and len(value) == 4:
            payload[self.attr] = value[0] == 1


# cluster 0x402, attribute 0
@dataclass
class ZTemperatureConv(Converter):
    ep: int = 1
    zigbee = "temperature"

    def decode(self, device: 'XDevice', payload: dict, value: dict):
        if isinstance(value.get("measured_value"), int):
            payload[self.attr] = value["measured_value"] / 100

    def read(self, device: "XDevice", payload: dict):
        cmd = zcl_read(device.nwk, self.ep, 0x402, [0])
        payload.setdefault("commands", []).extend(cmd)


class ZEnergyConv(MathConv):
    zigbee = "smartenergy_metering"

    def decode(self, device: "XDevice", payload: dict, value: dict):
        if "current_summ_delivered" in value:
            super().decode(device, payload, value["current_summ_delivered"])


@dataclass
class ZBatteryConv(Converter):
    ep: int = 1
    childs = {"battery_voltage"}
    zigbee = "power"

    def decode(self, device: "XDevice", payload: dict, value: dict):
        if isinstance(value.get("battery_percentage_remaining"), int):
            payload[self.attr] = int(value["battery_percentage_remaining"] / 2)
        elif isinstance(value.get("battery_voltage"), int):
            payload["battery_voltage"] = value["battery_voltage"] * 100

    def read(self, device: "XDevice", payload: dict):
        cmd = zcl_read(device.nwk, self.ep, 1, [32, 33])
        payload.setdefault("commands", []).extend(cmd)


################################################################################
# Specific defices converters
################################################################################

# Thanks to:
# https://github.com/Koenkk/zigbee-herdsman/blob/master/src/zcl/definition/cluster.ts
# moesStartUpOnOff: {ID: 0x8002, type: DataType.enum8},
class ZTuyaPowerOnConv(Converter):
    zigbee = "on_off"
    map = {0: "off", 1: "on", 2: "previous"}

    def decode(self, device: 'XDevice', payload: dict, value: dict):
        if 0x8002 in value:
            payload[self.attr] = self.map.get(value[0x8002])

    def encode(self, device: "XDevice", payload: dict, value: str):
        v = next(k for k, v in self.map.items() if v == value)
        cmd = zcl_write(device.nwk, 1, 6, 0x8002, 0x30, v)
        payload.setdefault("commands", []).extend(cmd)

    def read(self, device: "XDevice", payload: dict):
        cmd = zcl_read(device.nwk, 1, 6, 0x8002)
        payload.setdefault("commands", []).extend(cmd)


class ZAqaraCubeMain(Converter):
    childs = {"side", "from_side", "to_side"}
    zigbee = "multistate_input"

    def decode(self, device: "XDevice", payload: dict, value: dict):
        # Thanks to zigbee2mqtt:
        # https://github.com/Koenkk/zigbee-herdsman-converters/blob/4a74caad6361e606e0e995d74e7f9ca2f6bdce3e/converters/fromZigbee.js#L5490
        value = value["present_value"]
        if value == 0:
            payload["action"] = "shake"
        elif value == 2:
            payload["action"] = "wakeup"
        elif value == 3:
            payload["action"] = "fall"
        elif value >= 512:
            payload.update({"action": "tap", "side": value - 512})
        elif value >= 256:
            payload.update({"action": "slide", "side": value - 256})
        elif value >= 128:
            payload.update({"action": "flip180", "side": value - 128})
        elif value >= 64:
            payload.update({
                "action": "flip90",
                "from_side": math.floor((value - 64) / 8),
                "to_side": value % 8,
            })


class ZAqaraCubeRotate(Converter):
    childs = {"duration"}
    zigbee = "analog_input"

    def decode(self, device: "XDevice", payload: dict, value: dict):
        payload.update({
            "action": "rotate",
            "angle": round(value["present_value"]),
            "duration": round(value[65285] * 0.001, 2),
        })


class ZSonoffButtonConv(Converter):
    zigbee = "on_off"
    map = {0: "hold", 1: "double", 2: "single"}

    def decode(self, device: "XDevice", payload: dict, value: dict):
        payload[self.attr] = self.map.get(value["command_id"])


class ZHueDimmerOnConv(Converter):
    zigbee = "on_off"

    def decode(self, device: "XDevice", payload: dict, value: dict):
        if value["command_id"] == 1:
            payload[self.attr] = "button_1_single"
        elif value["command_id"] == 64:
            payload[self.attr] = "button_4_single"


class ZHueDimmerLevelConv(Converter):
    zigbee = "level"

    def decode(self, device: "XDevice", payload: dict, value: dict):
        if value["command"] == "step":
            if value["value"][0] == 0:
                payload[self.attr] = "button_2_single"
            elif value["value"][0] == 1:
                payload[self.attr] = "button_3_single"


class ZXiaomiBrightnessConv(Converter):
    """Converter decode and read data in Lumi format for support heartbeats.
    But encode data in Zigbee format for support transition.
    """

    def decode(self, device: "XDevice", payload: dict, value: Any):
        payload[self.attr] = value / 100.0 * 255.0

    def encode(self, device: "XDevice", payload: dict, value: Any):
        # brightness and transition in seconds
        if not isinstance(value, tuple):
            value = (value, 1)  # default transition
        cmd = zcl_level(device.nwk, 1, *value)
        payload.setdefault("commands", []).extend(cmd)


class ZXiaomiColorTempConv(Converter):
    """Converter decode and read data in Lumi format for support heartbeats.
    But encode data in Zigbee format for support transition.
    """
    minm = 153  # mireds (Aqara Bulb)
    maxm = 370  # mireds (Aqara Bulb)

    def decode(self, device: "XDevice", payload: dict, value: Any):
        if not isinstance(value, dict):
            payload[self.attr] = value

    def encode(self, device: "XDevice", payload: dict, value: Any):
        if not isinstance(value, tuple):
            value = (value, 1)  # default transition
        cmd = zcl_color(device.nwk, 1, *value)
        payload.setdefault("commands", []).extend(cmd)


# endpoint 2, cluster 0, attribute 51, type 0x10 (boolean)
class ZHueLed(Converter):
    zigbee = "basic"

    def decode(self, device: "XDevice", payload: dict, value: dict):
        if isinstance(value.get(51), int):
            payload[self.attr] = bool(value[51])

    def encode(self, device: "XDevice", payload: dict, value: bool):
        cmd = zcl_write(device.nwk, 2, 0, 51, 0x10, int(value))
        payload.setdefault("commands", []).extend(cmd)

    def read(self, device: "XDevice", payload: dict):
        cmd = zcl_read(device.nwk, 2, 0, 51)
        payload.setdefault("commands", []).extend(cmd)


################################################################################
# Final converter classes
################################################################################

ZCurrent = ZElectricalConv(
    "current", "sensor", zattr="rms_current", multiply=0.001
)
ZVoltage = ZElectricalConv("voltage", "sensor", zattr="rms_voltage")
ZPower = ZElectricalConv("power", "sensor", zattr="active_power")

ZVoltagePoll = ZElectricalConv(
    "voltage", "sensor", zattr="rms_voltage", poll=True
)

ZLight = ZOnOffConv("light", "light")
ZBrightness = ZBrightnessConv("brightness", parent="light")
ZColorTemp = ZColorTempConv("color_temp", parent="light")

ZTuyaPowerOn = ZTuyaPowerOnConv("power_on_state", "select")


################################################################################
# Configs
################################################################################


@dataclass
class ZBindConf(Config):
    clusters: set = None
    ep: int = 1

    def encode(self, device: "XDevice", payload: dict, gateway):
        for cluster in self.clusters:
            cmd = zdo_bind(
                device.nwk, self.ep, cluster, device.mac[2:], gateway.ieee
            )
            payload.setdefault("commands", []).extend(cmd)


@dataclass
class ZReportConf(Config):
    type: str
    ep: int = 1

    def encode(self, device: "XDevice", payload: dict, gateway):
        if self.type == "battery_percentage_remaining":
            cmd = zdb_report(device.nwk, self.ep, 1, 0x21, 0x20, 3600, 62000, 0)
        elif self.type == "occupancy":
            cmd = zdb_report(device.nwk, self.ep, 0x406, 0, 24, 0, 3600, 0)
        elif self.type == "temperature":
            cmd = zdb_report(device.nwk, self.ep, 0x402, 0, 0x29, 10, 3600, 100)
        elif self.type == "illuminance":
            cmd = zdb_report(device.nwk, self.ep, 0x400, 0, 0x21, 10, 3600, 5)
        else:
            raise NotImplementedError
        payload.setdefault("commands", []).extend(cmd)


class ZHueConf(Config):
    def encode(self, device: "XDevice", payload: dict, gateway):
        # Thanks to zigbee2mqtt and ZHA (some unknown magic)
        cmd = zcl_write(device.nwk, ep=2, cluster=0, attr=0x0031, type=0x19,
                        data=0x000B, mfg=0x100B)
        payload.setdefault("commands", []).extend(cmd)
