import time
from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING

from .const import BUTTON, BUTTON_BOTH, UNKNOWN

if TYPE_CHECKING:
    from ..device import XDevice


class Config:
    def encode(self, device: "XDevice", payload: dict, gateway):
        pass

    def __repr__(self):
        return self.__class__.__name__


################################################################################
# Base (global) converters
################################################################################

@dataclass
class Converter:
    attr: str  # hass attribute
    domain: Optional[str] = None  # hass domain

    # hack for old python
    kw_only: bool = None

    mi: Optional[str] = None
    parent: Optional[str] = None

    enabled: Optional[bool] = True  # support: True, False, None (lazy setup)
    poll: bool = False  # hass should_poll

    # don't init with dataclass because no type:
    childs = None  # set or dict? of children attributes
    zigbee = None  # str or set? with zigbee cluster

    def decode(self, device: "XDevice", payload: dict, value: Any):
        payload[self.attr] = value

    def encode(self, device: "XDevice", payload: dict, value: Any):
        if not self.mi:
            payload[self.attr] = value
            return
        if ".p." in self.mi:
            siid, piid = self.mi.split(".p.")
            cmd = {"siid": int(siid), "piid": int(piid), "value": value}
            payload.setdefault("mi_spec", []).append(cmd)
        else:
            cmd = {"res_name": self.mi, "value": value}
            payload.setdefault("params", []).append(cmd)

    def read(self, device: "XDevice", payload: dict):
        if not self.mi:
            return
        if ".p." in self.mi:
            siid, piid = self.mi.split(".p.")
            cmd = {"siid": int(siid), "piid": int(piid)}
            payload.setdefault("mi_spec", []).append(cmd)
        else:
            cmd = {"res_name": self.mi}
            payload.setdefault("params", []).append(cmd)


class BoolConv(Converter):
    def decode(self, device: "XDevice", payload: dict, value: int):
        payload[self.attr] = bool(value)

    def encode(self, device: "XDevice", payload: dict, value: bool):
        super().encode(device, payload, int(value))


@dataclass
class ConstConv(Converter):
    value: Any = None

    def decode(self, device: "XDevice", payload: dict, value: Any):
        payload[self.attr] = self.value


@dataclass
class MapConv(Converter):
    map: dict = None

    def decode(self, device: "XDevice", payload: dict, value: int):
        payload[self.attr] = self.map.get(value)

    def encode(self, device: "XDevice", payload: dict, value: Any):
        value = next(k for k, v in self.map.items() if v == value)
        super().encode(device, payload, value)


@dataclass
class MathConv(Converter):
    max: float = float("inf")
    min: float = -float("inf")
    multiply: float = 0
    round: int = None

    def decode(self, device: "XDevice", payload: dict, value: float):
        if self.min <= value <= self.max:
            if self.multiply:
                value *= self.multiply
            if self.round is not None:
                value = round(value, self.round)
            payload[self.attr] = value

    def encode(self, device: "XDevice", payload: dict, value: float):
        if self.multiply:
            value /= self.multiply
        super().encode(device, payload, value)


@dataclass
class BrightnessConv(Converter):
    max: float = 100.0

    def decode(self, device: "XDevice", payload: dict, value: float):
        payload[self.attr] = value / self.max * 255.0

    def encode(self, device: "XDevice", payload: dict, value: float):
        super().encode(device, payload, value / 255.0 * self.max)


@dataclass
class ColorTempKelvin(Converter):
    # 2700..6500 => 370..153
    mink: int = 2700
    maxk: int = 6500

    def decode(self, device: "XDevice", payload: dict, value: int):
        """Convert degrees kelvin to mired shift."""
        payload[self.attr] = int(1000000.0 / value)

    def encode(self, device: "XDevice", payload: dict, value: int):
        value = int(1000000.0 / value)
        if value < self.mink:
            value = self.mink
        if value > self.maxk:
            value = self.maxk
        super().encode(device, payload, value)


@dataclass
class BatteryConv(Converter):
    childs = {"battery_voltage", "battery_original"}
    min = 2700
    max = 3200

    def decode(self, device: "XDevice", payload: dict, value: int):
        payload["battery_voltage"] = value

        if value <= self.min:
            payload[self.attr] = 0
        elif value >= self.max:
            payload[self.attr] = 100
        else:
            payload[self.attr] = int(
                100.0 * (value - self.min) / (self.max - self.min)
            )


class ButtonConv(Converter):
    def decode(self, device: "XDevice", payload: dict, value: int):
        payload[self.attr] = value
        if self.attr == "button":
            payload["action"] = BUTTON.get(value, UNKNOWN)
        elif self.attr.startswith("button_both"):
            both = BUTTON_BOTH.get(value, UNKNOWN)
            payload["action"] = self.attr + "_" + both

        elif self.attr.startswith("button"):
            payload["action"] = self.attr + "_" + BUTTON.get(value, UNKNOWN)


@dataclass
class ButtonMIConv(ButtonConv):
    value: int = None

    def decode(self, device: "XDevice", payload: dict, value: int):
        super().decode(device, payload, self.value)


################################################################################
# Device converters
################################################################################

class VibrationConv(Converter):
    def decode(self, device: "XDevice", payload: dict, value: int):
        payload[self.attr] = value
        # skip tilt and wait tilt_angle
        if value == 1:
            payload["action"] = "vibration"
        elif value == 3:
            payload["action"] = "drop"


class TiltAngleConv(Converter):
    def decode(self, device: "XDevice", payload: dict, value: int):
        payload["action"] = "tilt"
        payload["angle"] = value
        payload["vibration"] = 2


class CloudLinkConv(Converter):
    def decode(self, device: "XDevice", payload: dict, value: dict):
        # zero means online
        # {"offline_time":1634407495,"offline_reason":30,"offline_ip":123,"offline_port":80}
        payload[self.attr] = value["offline_time"] == 0


class ClimateConv(Converter):
    hvac = {"off": 0x01, "heat": 0x10, "cool": 0x11}
    fan = {"low": 0x00, "medium": 0x10, "high": 0x20, "auto": 0x30}

    def decode(self, device: "XDevice", payload: dict, value: Any):
        # use payload to push data to climate entity
        # use device extra to pull data on encode
        payload[self.attr] = device.extra[self.attr] = value

    def encode(self, device: "XDevice", payload: dict, value: dict):
        if self.attr not in device.extra:
            return
        b = bytearray(device.extra[self.attr].to_bytes(4, 'big'))
        if "hvac_mode" in value:
            b[0] = self.hvac[value["hvac_mode"]]
        if "fan_mode" in value:
            b[1] = self.fan[value["fan_mode"]]
        if "target_temp" in value:
            b[3] = int(value["target_temp"])
        value = int.from_bytes(b, 'big')
        super().encode(device, payload, value)


class ClimateTempConv(Converter):
    def decode(self, device: "XDevice", payload: dict, value: int):
        payload[self.attr] = value if value < 255 else 0


@dataclass
class LockActionConv(Converter):
    map: dict = None

    def decode(self, device: "XDevice", payload: dict, value: Any):
        if self.attr in ("lock_control", "door_state", "lock_state"):
            payload["action"] = "lock"
            payload[self.attr] = self.map.get(value)
        elif self.attr == "key_id":
            payload["action"] = "lock"
            payload[self.attr] = value
        elif self.attr == "alarm":
            v = self.map.get(value)
            if v != "doorbell":
                payload["action"] = self.attr
                payload[self.attr] = v
            else:
                payload["action"] = v
        elif self.attr.endswith("_wrong"):
            payload["action"] = "error"
            payload["error"] = self.attr
            payload[self.attr] = value


@dataclass
class LockConv(Converter):
    mask: int = 0

    def decode(self, device: "XDevice", payload: dict, value: int):
        payload[self.attr] = bool(value & self.mask)


# to get natgas sensitivity value - write: {"res_name": "4.1.85", "value": 1}
# then it's report: {"res_name": "14.2.85", "value": <1 to 3>}
class GasSensitivityReadConv(Converter):
    map = {1: "low", 2: "medium", 3: "high"}

    def decode(self, device: "XDevice", payload: dict, value: int):
        payload[self.attr] = self.map.get(value)

    def encode(self, device: "XDevice", payload: dict, value: str):
        pass

    def read(self, device: "XDevice", payload: dict):
        payload["cmd"] = "write"
        cmd = {"res_name": "4.1.85", "value": 1}  # read spec
        payload.setdefault("params", []).append(cmd)


# to write natgas sensitivity value - write: {"res_name": "4.1.85", "value": x}
# then it's report {"res_name": "14.1.85", "value": x}
class GasSensitivityWriteConv(Converter):
    map = {0x4010000: "low", 0x4020000: "medium", 0x4030000: "high"}

    def decode(self, device: "XDevice", payload: dict, value: int):
        payload[self.attr] = self.map.get(value)

    def encode(self, device: "XDevice", payload: dict, value: str):
        value = next(k for k, v in self.map.items() if v == value)
        super().encode(device, payload, value)

    def read(self, device: "XDevice", payload: dict):
        pass


class ParentConv(Converter):
    def decode(self, device: "XDevice", payload: dict, value: str):
        try:
            # value in did format
            device: "XDevice" = device.gateways[0].devices[value]
            payload[self.attr] = device.nwk
        except:
            payload[self.attr] = "-"


class OTAConv(Converter):
    def decode(self, device: "XDevice", payload: dict, value: Any):
        super().decode(device, payload, value)

        # forward update percents to gateway, so it can show it in GUI
        try:
            # noinspection PyUnresolvedReferences
            device.gateways[0].device.update(payload)
        except:
            pass


class OnlineConv(Converter):
    def decode(self, device: "XDevice", payload: dict, value: dict):
        payload[self.attr] = value["status"] == "online"
        device.last_seen = time.time() - value["time"]


################################################################################
# Final converter classes
################################################################################

# https://github.com/Koenkk/zigbee2mqtt/issues/798
# https://www.maero.dk/aqara-temperature-humidity-pressure-sensor-teardown/
Temperature = MathConv(
    "temperature", "sensor", mi="0.1.85", multiply=0.01, min=-4000, max=12500
)
Humidity = MathConv(
    "humidity", "sensor", mi="0.2.85", multiply=0.01, min=0, max=10000
)
# Pressure = MathConv("pressure", "sensor", mi="0.3.85", multiply=0.01)

# Motion = BoolConv("motion", "binary_sensor", mi="3.1.85")

# power measurements
Voltage = MathConv("voltage", "sensor", mi="0.11.85", multiply=0.001, round=2)
Power = MathConv("power", "sensor", mi="0.12.85", round=2)
Energy = MathConv("energy", "sensor", mi="0.13.85", multiply=0.001, round=2)
Current = MathConv("current", "sensor", mi="0.14.85", multiply=0.001, round=2)

ChipTemp = Converter("chip_temperature", "sensor", mi="8.0.2006", enabled=False)

# switches and relays
PlugN0 = BoolConv("plug", "switch", mi="4.1.85")
# PlugC0 = BoolConv("plug", "switch", "4.1.85", "channel_0")
# SwitchC0 = BoolConv("switch", "switch", "4.1.85", "channel_0")
# SwitchN0 = BoolConv("switch", "switch", "4.1.85", "neutral_0")
ChannelC1 = BoolConv("channel_1", "switch", mi="4.1.85")
ChannelC2 = BoolConv("channel_2", "switch", mi="4.2.85")
ChannelC3 = BoolConv("channel_3", "switch", mi="4.2.85")
ChannelN1 = BoolConv("channel_1", "switch", mi="4.1.85")
ChannelN2 = BoolConv("channel_2", "switch", mi="4.2.85")
ChannelN3 = BoolConv("channel_3", "switch", mi="4.3.85")

Action = Converter("action", "sensor")
Button = ButtonConv("button", mi="13.1.85")
Button1 = ButtonConv("button_1", mi="13.1.85")
Button2 = ButtonConv("button_2", mi="13.2.85")
Button3 = ButtonConv("button_3", mi="13.3.85")
Button4 = ButtonConv("button_4", mi="13.4.85")
Button5 = ButtonConv("button_5", mi="13.6.85")
Button6 = ButtonConv("button_6", mi="13.7.85")
ButtonBoth = ButtonConv("button_both", mi="13.5.85")
Button12 = ButtonConv("button_both_12", mi="13.5.85")
Button13 = ButtonConv("button_both_13", mi="13.6.85")
Button23 = ButtonConv("button_both_23", mi="13.7.85")

# Light = BoolConv("light", "light", mi="4.1.85")
# Brightness = BrightnessConv("brightness", mi="14.1.85", parent="light")
# ColorTemp = Converter("color_temp", mi="14.2.85", parent="light")

# RunState = MapConv("run_state", mi="14.4.85", map=RUN_STATE)

# converts voltage to percent and shows voltage in attributes
# users can adds separate voltage sensor or original percent sensor
Battery = BatteryConv("battery", "sensor", mi="8.0.2008")
BatteryLow = BoolConv(
    "battery_low", "binary_sensor", mi="8.0.9001", enabled=False
)
BatteryOrig = Converter("battery_original", mi="8.0.2001")

# zigbee3 devices

# Switch_MI21 = Converter("switch", "switch", mi="2.p.1")
Channel1_MI21 = Converter("channel_1", "switch", mi="2.p.1")
Channel2_MI31 = Converter("channel_2", "switch", mi="3.p.1")

# global props
LUMI_GLOBALS = {
    "8.0.2002": Converter("resets", "sensor"),
    "8.0.2022": Converter("fw_ver", "sensor"),
    "8.0.2036": ParentConv("parent", "sensor"),
    "8.0.2091": OTAConv("ota_progress", "sensor"),
    "8.0.2102": OnlineConv("online", "binary_sensor"),
    # "8.0.2156": Converter("nwk", "sensor"),
}
