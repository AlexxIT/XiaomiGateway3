from dataclasses import dataclass
from typing import Any, TYPE_CHECKING, Optional

import zigpy.device
import zigpy.quirks
from zigpy.const import SIG_ENDPOINTS
from zigpy.device import Device

from .base import Converter, parse_time
from .const import *
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

    # noinspection PyTypeChecker
    device = Device(None, None, 0)
    device.manufacturer = manufacturer
    device.model = model

    quirk: zigpy.quirks.CustomDevice = quirks[0]
    if SIG_ENDPOINTS in quirk.replacement:
        for endpoint_id in quirk.replacement[SIG_ENDPOINTS].keys():
            device.add_endpoint(endpoint_id)

    return quirks[0](None, None, 0, device)


###############################################################################
# Base (global) converters
###############################################################################


@dataclass
class ZConverter(Converter):
    """Basic zigbee converter."""

    ep: int = 1
    zattr = None
    bind: bool = None
    report: str = None

    def decode(self, device: "XDevice", payload: dict, value: dict):
        if value["endpoint"] == self.ep and self.zattr in value:
            payload[self.attr] = value[self.zattr]

    def read(self, device: "XDevice", payload: dict):
        cmd = zcl_read(device.nwk, self.ep, self.zigbee, self.zattr)
        payload.setdefault("commands", []).extend(cmd)

    def config(self, device: "XDevice", payload: dict, gateway):
        if self.bind:
            cmd = zdo_bind(
                device.nwk, self.ep, self.zigbee, device.mac[2:], gateway.ieee
            )
            payload.setdefault("commands", []).extend(cmd)

        if self.report:
            mint, maxt, change = self.report.split(" ")
            mint = int(parse_time(mint))
            maxt = int(parse_time(maxt))
            change = int(change)
            cmd = zdb_report(
                device.nwk,
                self.ep,
                self.zigbee,
                self.zattr,
                mint,
                maxt,
                change,
            )
            payload.setdefault("commands", []).extend(cmd)


class ZBoolConv(ZConverter):
    """Basic zigbee bool converter."""

    def decode(self, device: "XDevice", payload: dict, value: dict):
        if value["endpoint"] == self.ep and self.zattr in value:
            payload[self.attr] = bool(value[self.zattr])

    def encode(self, device: "XDevice", payload: dict, value: bool):
        cmd = zcl_write(
            device.nwk, self.ep, self.zigbee, self.zattr, int(value), type=0x10
        )
        payload.setdefault("commands", []).extend(cmd)


class ZMapConv(ZConverter):
    map = {}

    def decode(self, device: "XDevice", payload: dict, value: dict):
        if self.zattr in value:
            payload[self.attr] = self.map.get(value[self.zattr])

    def encode(self, device: "XDevice", payload: dict, value: str):
        v = next(k for k, v in self.map.items() if v == value)
        cmd = zcl_write(device.nwk, self.ep, self.zigbee, self.zattr, v, type=0x30)
        payload.setdefault("commands", []).extend(cmd)


@dataclass
class ZMathConv(ZConverter):
    multiply: float = 1

    def decode(self, device: "XDevice", payload: dict, value: dict):
        if value["endpoint"] == self.ep and self.zattr in value:
            payload[self.attr] = value[self.zattr] * self.multiply


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


class ZElectricalConv(ZMathConv):
    zigbee = "electrical_measurement"

    def read(self, device: "XDevice", payload: dict):
        # we can read three attrs from one cluster with single call
        cmd = zcl_read(
            device.nwk,
            self.ep,
            self.zigbee,
            "rms_voltage",
            "rms_current",
            "active_power",
        )
        payload.setdefault("commands", []).extend(cmd)


class ZVoltageConv(ZElectricalConv):
    zattr = "rms_voltage"


class ZCurrentConv(ZElectricalConv):
    zattr = "rms_current"


class ZPowerConv(ZElectricalConv):
    zattr = "active_power"


class ZEnergyConv(ZMathConv):
    zigbee = "smartenergy_metering"
    zattr = "current_summ_delivered"


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


class ZIASZoneConv(ZConverter):
    zigbee = "ias_zone"

    def decode(self, device: "XDevice", payload: dict, value: dict):
        try:
            payload[self.attr] = (value["value"][0] & 1) > 0
        except Exception:
            pass

    def read(self, device: "XDevice", payload: dict):
        pass


@dataclass
class ZIlluminanceConv(ZMathConv):
    zigbee = "illuminance"
    zattr = "measured_value"
    multiply: float = 0.01


@dataclass
class ZTemperatureConv(ZMathConv):
    zigbee = "temperature"
    zattr = "measured_value"
    multiply: float = 0.01


@dataclass
class ZHumidityConv(ZMathConv):
    zigbee = "humidity"
    zattr = "measured_value"
    multiply: float = 0.01


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
        cmd = zcl_read(device.nwk, self.ep, self.zigbee, self.zattr, "battery_voltage")
        payload.setdefault("commands", []).extend(cmd)


# useful for reporting description
# class ZBatteryVoltConv(ZBatteryConv):
#     zattr = "battery_voltage"
#
#     def decode(self, device: "XDevice", payload: dict, value: dict):
#         if isinstance(value.get("battery_voltage"), int):
#             payload[self.zattr] = value[self.zattr] * 100


###############################################################################
# Specific defices converters
###############################################################################


class ZTuyaChildModeConv(ZBoolConv):
    zigbee = "on_off"
    zattr = 0x8000


class ZTuyaLEDModeConv(ZMapConv):
    zigbee = "on_off"
    zattr = 0x8001
    map = {0: "off", 1: "off/on", 2: "on/off", 3: "on"}


# Thanks to:
# https://github.com/Koenkk/zigbee-herdsman/blob/master/src/zcl/definition/cluster.ts
# moesStartUpOnOff: {ID: 0x8002, type: DataType.enum8},
class ZTuyaPowerOnConv(ZMapConv):
    zigbee = "on_off"
    zattr = 0x8002
    map = {0: "off", 1: "on", 2: "previous"}


class ZTuyaButtonModeConv(ZMapConv):
    zigbee = "on_off"
    zattr = 0x8004
    map = {0: "command", 1: "event"}

    def config(self, device: "XDevice", payload: dict, gateway):
        # set default mode
        self.encode(device, payload, "event")


# Thanks to:
# https://github.com/Koenkk/zigbee-herdsman-converters/blob/910271ae8fccb19305752d3f67381b4765853018/converters/fromZigbee.js#L4537
# https://github.com/Koenkk/zigbee-herdsman/blob/068bbe7636f588394f69f82bc25c8b68a4feada7/src/zcl/definition/cluster.ts#L4284
class ZTuyaPlugModeConv(ZMapConv):
    zigbee = 0xE001
    zattr = 0xD030
    map = {0: "toggle", 1: "state", 2: "momentary"}


class ZTuyaButtonConfig(ZConverter):
    def config(self, device: "XDevice", payload: dict, gateway):
        # some stupid but necessary magic from zigbee2mqtt
        cmd = zcl_read(
            device.nwk, self.ep, "on_off", 0x0004, 0x000, 0x0001, 0x0005, 0x0007, 0xFFFE
        )
        cmd += zcl_read(device.nwk, self.ep, 0xE001, 0xD011)
        payload.setdefault("commands", []).extend(cmd)


class ZTuyaButtonConv(ZConverter):
    zigbee = "on_off"
    zattr = "on_off"
    map = {0: SINGLE, 1: DOUBLE, 2: HOLD}

    def decode(self, device: "XDevice", payload: dict, value: dict):
        # TS004F sends click three times with same seq number
        if device.extra.get("seq") == value["seq"] or value["endpoint"] != self.ep:
            return

        device.extra["seq"] = value["seq"]

        try:
            payload[self.attr] = value = self.map.get(value["value"][0])
            payload["action"] = self.attr + "_" + value
        except Exception:
            pass


# Thanks to zigbee2mqtt:
# https://github.com/Koenkk/zigbee-herdsman/blob/528b7626f2970ba87a0792920590926105a3cb48/src/zcl/definition/cluster.ts#LL460C32-L460C37
# https://github.com/Koenkk/zigbee-herdsman-converters/blob/f9115000807b21dcaa06e58c5b8e69baa4e626fe/converters/fromZigbee.js#L867
class ZPowerOnConv(ZMapConv):
    zigbee = "on_off"
    zattr = 16387
    map = {0: "off", 1: "on", 2: "toggle", 255: "previous"}


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
        elif value & 0x200:
            payload.update({"action": "tap", "side": value & 0b111})
        elif value & 0x100:
            payload.update({"action": "slide", "side": value & 0b111})
        elif value & 0x80:
            payload.update({"action": "flip180", "side": value & 0b111})
        elif value & 0x40:
            payload.update(
                {
                    "action": "flip90",
                    "from_side": (value >> 3) & 0b111,
                    "to_side": value & 0b111,
                }
            )


class ZAqaraCubeRotate(Converter):
    zigbee = "analog_input"
    zattr = "present_value"
    childs = {"duration"}

    def decode(self, device: "XDevice", payload: dict, value: dict):
        payload.update(
            {
                "action": "rotate",
                "angle": round(value["present_value"]),
                "duration": round(value[65285] * 0.001, 2),
            }
        )


class ZSonoffButtonConv(ZConverter):
    zigbee = "on_off"
    zattr = "command_id"
    map = {0: "hold", 1: "double", 2: "single"}

    def decode(self, device: "XDevice", payload: dict, value: dict):
        payload[self.attr] = self.map.get(value[self.zattr])


class ZHueDimmerOnConv(ZConverter):
    zigbee = "on_off"

    def decode(self, device: "XDevice", payload: dict, value: dict):
        if value["command_id"] == 1:
            payload[self.attr] = "button_1_single"
        elif value["command_id"] == 64:
            payload[self.attr] = "button_4_single"

    def read(self, device: "XDevice", payload: dict):
        pass

    def config(self, device: "XDevice", payload: dict, gateway):
        super().config(device, payload, gateway)

        # Thanks to zigbee2mqtt and ZHA (some unknown magic)
        cmd = zcl_write(
            device.nwk,
            2,
            cluster="basic",
            attr=0x0031,
            data=0x000B,
            mfg=0x100B,
            type=0x19,
        )
        payload.setdefault("commands", []).extend(cmd)


class ZHueDimmerLevelConv(ZConverter):
    zigbee = "level"

    def decode(self, device: "XDevice", payload: dict, value: dict):
        if value["command"] == "step":
            if value["value"][0] == 0:
                payload[self.attr] = "button_2_single"
            elif value["value"][0] == 1:
                payload[self.attr] = "button_3_single"

    def read(self, device: "XDevice", payload: dict):
        pass


class ZXiaomiBrightnessConv(Converter):
    """Converter decode and read data in Lumi format for support heartbeats.
    But encode data in Zigbee format for support transition.
    """

    def decode(self, device: "XDevice", payload: dict, value: Any):
        payload[self.attr] = max (0, min(255, round(value / 100.0 * 255.0)))

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
        cmd = zcl_write(device.nwk, 2, self.zigbee, 51, int(value), type=0x10)
        payload.setdefault("commands", []).extend(cmd)

    def read(self, device: "XDevice", payload: dict):
        cmd = zcl_read(device.nwk, 2, self.zigbee, 51)
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


class ZAqaraOppleMode(ZConverter):
    zigbee = 0xFCC0
    map = {0: "binding", 1: "multiclick"}

    def encode(self, device: "XDevice", payload: dict, value: Any):
        value = next(k for k, v in self.map.items() if v == value)
        cmd = zcl_write(
            device.nwk, self.ep, self.zigbee, 9, value, type=0x20, mfg=0x115F
        )
        payload.setdefault("commands", []).extend(cmd)

    def read(self, device: "XDevice", payload: dict):
        pass


###############################################################################
# Final converter classes
###############################################################################

ZSwitch = ZOnOffConv("switch", "switch")

ZLight = ZOnOffConv("light", "light")
ZBrightness = ZBrightnessConv("brightness", parent="light")
ZColorTemp = ZColorTempConv("color_temp", parent="light")

ZPowerOn = ZPowerOnConv("power_on_state", "select", enabled=False)
ZTuyaPowerOn = ZTuyaPowerOnConv("power_on_state", "select", enabled=False)
# ZTuyaMode = ZTuyaModeConv("mode", "select", enabled=False)
