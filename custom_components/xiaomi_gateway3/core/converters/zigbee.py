import math
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING, Optional, Type

import zigpy.device
import zigpy.quirks
from zigpy.const import SIG_ENDPOINTS
from zigpy.device import Device

from .base import Config, Converter, MathConv
from .silabs import *

if TYPE_CHECKING:
    from .devices import XDevice


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
class ZConverter(Converter):
    """Basic zigbee converter."""
    ep: int = 1
    zattr = None

    def decode(self, device: 'XDevice', payload: dict, value: dict):
        if value["endpoint"] == self.ep and self.zattr in value:
            payload[self.attr] = value[self.zattr]

    def read(self, device: "XDevice", payload: dict):
        cmd = zcl_read(device.nwk, self.ep, self.zigbee, self.zattr)
        payload.setdefault("commands", []).extend(cmd)


class ZBoolConv(ZConverter):
    """Basic zigbee bool converter."""

    def decode(self, device: 'XDevice', payload: dict, value: dict):
        if value["endpoint"] == self.ep and self.zattr in value:
            payload[self.attr] = bool(value[self.zattr])


class ZOnOffConv(ZBoolConv):
    zigbee = "on_off"
    zattr = "on_off"

    def encode(self, device: "XDevice", payload: dict, value: bool):
        cmd = zcl_on_off(device.nwk, self.ep, value)
        payload.setdefault("commands", []).extend(cmd)


class ZBrightnessConv(ZConverter):
    zigbee = "level"
    zattr = "current_level"

    def encode(self, device: "XDevice", payload: dict, value: Any):
        # brightness and transition in seconds
        if not isinstance(value, tuple):
            value = (value, 1)  # default transition
        cmd = zcl_level(device.nwk, self.ep, *value)
        payload.setdefault("commands", []).extend(cmd)


class ZColorTempConv(ZConverter):
    zigbee = "light_color"
    zattr = "color_temperature"

    min: int = 153
    max: int = 500

    def encode(self, device: "XDevice", payload: dict, value: Any):
        if not isinstance(value, tuple):
            value = (value, 1)  # default transition
        cmd = zcl_color(device.nwk, self.ep, *value)
        payload.setdefault("commands", []).extend(cmd)


@dataclass
class ZElectricalConv(MathConv):
    zigbee = "electrical_measurement"
    zattr: str = None

    def decode(self, device: "XDevice", payload: dict, value: dict):
        if self.zattr in value:
            super().decode(device, payload, value[self.zattr])

    def read(self, device: "XDevice", payload: dict):
        cmd = zcl_read(
            device.nwk, 1, self.zigbee, "rms_voltage", "rms_current",
            "active_power"
        )
        payload.setdefault("commands", []).extend(cmd)


class ZIlluminanceConv(ZConverter):
    zigbee = "illuminance"
    zattr = "measured_value"

    def decode(self, device: 'XDevice', payload: dict, value: dict):
        if isinstance(value.get(self.zattr), int):
            payload[self.attr] = value[self.zattr] / 100


class ZOccupancyConv(ZBoolConv):
    zigbee = "occupancy"
    zattr = "occupancy"


@dataclass
class ZOccupancyTimeoutConv(ZConverter):
    zigbee = "occupancy"
    zattr = "pir_o_to_u_delay"
    min: int = 0
    max: int = 65535

    def encode(self, device: "XDevice", payload: dict, value: int):
        cmd = zcl_write(device.nwk, self.ep, self.zigbee, self.zattr, value)
        payload.setdefault("commands", []).extend(cmd)
        # we need to read new value after write
        self.read(device, payload)


# class ZAnalogInput(Converter):
#     zigbee = "analog_input"
#
#     def decode(self, device: 'XDevice', payload: dict, value: dict):
#         if isinstance(value.get("present_value"), float):
#             payload[self.attr] = round(value['present_value'], 2)


class ZIASZoneConv(Converter):
    zigbee = "ias_zone"

    def decode(self, device: "XDevice", payload: dict, value: dict):
        value = value.get("value")
        if isinstance(value, list) and len(value) == 4:
            payload[self.attr] = value[0] == 1


class ZTemperatureConv(ZConverter):
    zigbee = "temperature"
    zattr = "measured_value"

    def decode(self, device: 'XDevice', payload: dict, value: dict):
        if isinstance(value.get(self.zattr), int):
            payload[self.attr] = value[self.zattr] / 100


class ZHumidityConv(ZConverter):
    zigbee = "humidity"
    zattr = "measured_value"

    def decode(self, device: 'XDevice', payload: dict, value: dict):
        if isinstance(value.get(self.zattr), int):
            payload[self.attr] = value[self.zattr] / 100


class ZEnergyConv(MathConv):
    zigbee = "smartenergy_metering"
    zattr = "current_summ_delivered"

    def decode(self, device: "XDevice", payload: dict, value: dict):
        if self.zattr in value:
            super().decode(device, payload, value[self.zattr])


class ZBatteryConv(ZConverter):
    zigbee = "power"
    zattr = "battery_percentage_remaining"
    childs = {"battery_voltage"}

    def decode(self, device: "XDevice", payload: dict, value: dict):
        if isinstance(value.get(self.zattr), int):
            payload[self.attr] = int(value[self.zattr] / 2)
        elif isinstance(value.get("battery_voltage"), int):
            payload["battery_voltage"] = value["battery_voltage"] * 100

    def read(self, device: "XDevice", payload: dict):
        cmd = zcl_read(
            device.nwk, self.ep, self.zigbee, self.zattr, "battery_voltage"
        )
        payload.setdefault("commands", []).extend(cmd)


################################################################################
# Specific defices converters
################################################################################

# Thanks to:
# https://github.com/Koenkk/zigbee-herdsman/blob/master/src/zcl/definition/cluster.ts
# moesStartUpOnOff: {ID: 0x8002, type: DataType.enum8},
class ZTuyaPowerOnConv(ZConverter):
    zigbee = "on_off"
    zattr = 0x8002
    map = {0: "off", 1: "on", 2: "previous"}

    def decode(self, device: 'XDevice', payload: dict, value: dict):
        if self.zattr in value:
            payload[self.attr] = self.map.get(value[self.zattr])

    def encode(self, device: "XDevice", payload: dict, value: str):
        v = next(k for k, v in self.map.items() if v == value)
        cmd = zcl_write(device.nwk, self.ep, self.zigbee, self.attr, v, 0x30)
        payload.setdefault("commands", []).extend(cmd)


class ZAqaraCubeMain(Converter):
    zigbee = "multistate_input"
    zattr = "present_value"
    childs = {"side", "from_side", "to_side"}

    def decode(self, device: "XDevice", payload: dict, value: dict):
        # Thanks to zigbee2mqtt:
        # https://github.com/Koenkk/zigbee-herdsman-converters/blob/4a74caad6361e606e0e995d74e7f9ca2f6bdce3e/converters/fromZigbee.js#L5490
        value = value[self.zattr]
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
    zigbee = "analog_input"
    zattr = "present_value"
    childs = {"duration"}

    def decode(self, device: "XDevice", payload: dict, value: dict):
        payload.update({
            "action": "rotate",
            "angle": round(value["present_value"]),
            "duration": round(value[65285] * 0.001, 2),
        })


class ZSonoffButtonConv(Converter):
    zigbee = "on_off"
    zattr = "command_id"
    map = {0: "hold", 1: "double", 2: "single"}

    def decode(self, device: "XDevice", payload: dict, value: dict):
        payload[self.attr] = self.map.get(value[self.zattr])


class ZHueDimmerOnConv(Converter):
    zigbee = "on_off"
    zattr = "command_id"

    def decode(self, device: "XDevice", payload: dict, value: dict):
        if value[self.zattr] == 1:
            payload[self.attr] = "button_1_single"
        elif value[self.zattr] == 64:
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


class IKEARemoteConv1(ZConverter):
    zigbee = "on_off"

    def decode(self, device: "XDevice", payload: dict, value: dict):
        if value.get("command_id") == 2:
            payload["button"] = "toggle"


class IKEARemoteConv2(ZConverter):
    zigbee = "level"
    map = {
        1: "brightness_down_hold",
        2: "brightness_down_click",
        3: "brightness_down_release",
        4: "toggle_hold",
        5: "brightness_up_hold",
        6: "brightness_up_click",
        7: "brightness_up_release",
    }

    def decode(self, device: "XDevice", payload: dict, value: dict):
        if "command_id" in value:
            payload["button"] = self.map.get(value["command_id"])


################################################################################
# Final converter classes
################################################################################

ZSwitch = ZOnOffConv("switch", "switch")

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

ZTuyaPowerOn = ZTuyaPowerOnConv("power_on_state", "select", enabled=False)


################################################################################
# Configs
################################################################################


class ZBindConf(Config):
    def __init__(self, cluster: Type[Converter], ep: int = 1):
        self.cluster = cluster.zigbee
        self.ep = ep

    def encode(self, device: "XDevice", payload: dict, gateway):
        cmd = zdo_bind(
            device.nwk, self.ep, self.cluster, device.mac[2:], gateway.ieee
        )
        payload.setdefault("commands", []).extend(cmd)


class ZReportConf(Config):
    def __init__(
            self, conv: Type[ZConverter], mint: int, maxt: int, change: int,
            ep: int = 1
    ):
        self.cluster = conv.zigbee
        self.attr = conv.zattr
        self.mint = mint
        self.maxt = maxt
        self.change = change
        self.ep = ep

    def encode(self, device: "XDevice", payload: dict, gateway):
        cmd = zdb_report(
            device.nwk, self.ep, self.cluster, self.attr, self.mint, self.maxt,
            self.change
        )
        payload.setdefault("commands", []).extend(cmd)


class ZHueConf(Config):
    def encode(self, device: "XDevice", payload: dict, gateway):
        # Thanks to zigbee2mqtt and ZHA (some unknown magic)
        cmd = zcl_write(
            device.nwk, 2, cluster="basic", attr=0x0031, data=0x000B,
            mfg=0x100B, type=0x19
        )
        payload.setdefault("commands", []).extend(cmd)


ZBindOnOff = ZBindConf(ZOnOffConv)