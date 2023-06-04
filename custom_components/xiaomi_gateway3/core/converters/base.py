import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, TYPE_CHECKING

from homeassistant.components.number.const import DEFAULT_STEP

from .const import *

if TYPE_CHECKING:
    from ..device import XDevice


def parse_time(value: str) -> float:
    """Conver string time to float time (seconds).
    @type value: 15s or 30m or 24h or 1d
    """
    return float(value[:-1]) * TIME[value[-1]]


###############################################################################
# Base (global) converters
###############################################################################


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
class EventConv(Converter):
    value: any = None

    def decode(self, device: "XDevice", payload: dict, value: list):
        payload[self.attr] = self.value
        if len(value) > 0:
            payload.update(device.decode_lumi(value))


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
    step: float = DEFAULT_STEP

    def decode(self, device: "XDevice", payload: dict, value: float):
        if self.min <= value <= self.max:
            if self.multiply:
                value *= self.multiply
            if self.round is not None:
                # convert to int when round is zero
                value = round(value, self.round or None)
            payload[self.attr] = value

    def encode(self, device: "XDevice", payload: dict, value: float):
        if self.multiply:
            value /= self.multiply
        super().encode(device, payload, value)


@dataclass
class MaskConv(Converter):
    mask: int = 0

    def decode(self, device: "XDevice", payload: dict, value: int):
        device.extra[self.attr] = value
        payload[self.attr] = bool(value & self.mask)

    def encode(self, device: "XDevice", payload: dict, value: bool):
        new_value = device.extra.get(self.attr, 0)
        new_value = new_value | self.mask if value else new_value & ~self.mask
        super().encode(device, payload, new_value)


@dataclass
class BrightnessConv(Converter):
    max: float = 100.0

    def decode(self, device: "XDevice", payload: dict, value: int):
        payload[self.attr] = value / self.max * 255.0

    def encode(self, device: "XDevice", payload: dict, value: float):
        value = round(value / 255.0 * self.max)
        super().encode(device, payload, int(value))


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
            payload[self.attr] = int(100.0 * (value - self.min) / (self.max - self.min))


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


###############################################################################
# Device converters
###############################################################################


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
    def decode(self, device: "XDevice", payload: dict, value: str):
        if isinstance(value, str):
            value = json.loads(value)["cloud_link"]
        payload[self.attr] = bool(value)


class ResetsConv(Converter):
    def decode(self, device: "XDevice", payload: dict, value: int):
        if "resets0" not in device.extra:
            device.extra["resets0"] = value
        payload["new_resets"] = value - device.extra["resets0"]
        super().decode(device, payload, value)


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
        b = bytearray(device.extra[self.attr].to_bytes(4, "big"))
        if "hvac_mode" in value:
            b[0] = self.hvac[value["hvac_mode"]]
        if "fan_mode" in value:
            b[1] = self.fan[value["fan_mode"]]
        if "target_temp" in value:
            b[3] = int(value["target_temp"])
        value = int.from_bytes(b, "big")
        super().encode(device, payload, value)


class ClimateTempConv(Converter):
    def decode(self, device: "XDevice", payload: dict, value: int):
        payload[self.attr] = value if value < 255 else 0


# we need get pos with one property and set pos with another
class CurtainPosConv(Converter):
    def encode(self, device: "XDevice", payload: dict, value: Any):
        conv = next(c for c in device.converters if c.attr == "target_position")
        conv.encode(device, payload, value)


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
        elif self.attr in ("error", "method"):
            payload[self.attr] = self.map.get(value)


@dataclass
class LockConv(Converter):
    mask: int = 0

    def decode(self, device: "XDevice", payload: dict, value: int):
        # Hass: On means open (unlocked), Off means closed (locked)
        payload[self.attr] = not bool(value & self.mask)


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


class AqaraTimePatternConv(Converter):
    """
    Encoding format:
        Period: <START_HOUR>:<START_MINUTE> - <END_HOUR>:<END_MINUTE>
        Encoded: AAAAAAAA BBBBBBBB CCCCCCCC DDDDDDDD
            (Each character represents 1 bit)
            AAAAAAAA = binary number of <END_MINUTE>
            BBBBBBBB = binary number of <END_HOUR>
            CCCCCCCC = binary number of <START_MIN>
            DDDDDDDD = binary number of <START_HOUR>

    Example:
        Period: 23:59 - 10:44
        Encoded: 00101100 00001010 00111011 00010111
            00101100 = 44 <END_MINUTE>
            00001010 = 10 <END_HOUR>
            00111011 = 59 <START_MIN>
            00010111 = 23 <START_HOUR>
    """

    pattern = "^[0-2][0-9]:[0-5][0-9]-[0-2][0-9]:[0-5][0-9]$"

    def decode(self, device: "XDevice", payload: dict, v: int):
        payload[self.attr] = (
            f"{v & 0xFF:02d}:{(v >> 8) & 0xFF:02d}-"
            f"{(v >> 16) & 0xFF:02d}:{(v >> 24) & 0xFF:02d}"
        )

    def encode(self, device: "XDevice", payload: dict, v: str):
        v = int(v[:2]) | int(v[3:5]) << 8 | int(v[6:8]) << 16 | int(v[9:11]) << 24
        super().encode(device, payload, v)


class GiotTimePatternConv(Converter):
    """
    Period encoding:
    8-digit number: HHMMhhmm
        HH = start hour
        MM = start minute
        hh = end hour
        mm = end minute
    Example:
        Period: 23:59 - 10:44
        Encoded: 23591044
    """

    pattern = "^[0-2][0-9]:[0-5][0-9]-[0-2][0-9]:[0-5][0-9]$"

    def decode(self, device: "XDevice", payload: dict, v: int):
        payload[self.attr] = f"{v[:2]}:{v[2:4]}-{v[4:6]}:{v[6:]}"

    def encode(self, device: "XDevice", payload: dict, v: str):
        v = v.replace(":", "").replace("-", "")
        super().encode(device, payload, v)


class ParentConv(Converter):
    def decode(self, device: "XDevice", payload: dict, value: str):
        try:
            # value in did format
            device: "XDevice" = device.gateways[0].devices[value]
            payload[self.attr] = device.nwk
        except Exception:
            payload[self.attr] = "-"


@dataclass
class BLEEvent(Converter):
    map: dict = None

    def decode(self, device: "XDevice", payload: dict, value: list):
        try:
            payload[self.attr] = self.map.get(value[0]["value"])
        except:
            pass


class OTAConv(Converter):
    def decode(self, device: "XDevice", payload: dict, value: Any):
        super().decode(device, payload, value)

        # forward update percents to gateway, so it can show it in GUI
        try:
            # noinspection PyUnresolvedReferences
            device.gateways[0].device.update(payload)
        except Exception:
            pass


class OnlineConv(Converter):
    def decode(self, device: "XDevice", payload: dict, value: dict):
        dt = value["time"]
        new_ts = time.time() - dt
        # if the device will be on two gateways (by accident), the online time
        # from "wrong" gateway could be wrong
        if new_ts < device.decode_ts:
            return

        device.available = dt < device.available_timeout
        device.decode_ts = new_ts

        payload[self.attr] = value["status"] == "online"
        payload["zigbee"] = datetime.now(timezone.utc) - timedelta(seconds=dt)


class RemoveDIDConv(Converter):
    def decode(self, device: "XDevice", payload: dict, value: Any):
        # two formats:
        # "res_name":"8.0.2082","value":{"did":"lumi.1234567890"}"
        # "res_name":"8.0.2082","value":"lumi.1234567890"
        if isinstance(value, dict):
            value = value["did"]
        super().decode(device, payload, value)


###############################################################################
# Final converter classes
###############################################################################

# https://github.com/Koenkk/zigbee2mqtt/issues/798
# https://www.maero.dk/aqara-temperature-humidity-pressure-sensor-teardown/
Temperature = MathConv(
    "temperature", "sensor", mi="0.1.85", multiply=0.01, min=-4000, max=12500
)
Humidity = MathConv("humidity", "sensor", mi="0.2.85", multiply=0.01, min=0, max=10000)
# Pressure = MathConv("pressure", "sensor", mi="0.3.85", multiply=0.01)

# Motion = BoolConv("motion", "binary_sensor", mi="3.1.85")

# power measurements
Voltage = MathConv("voltage", "sensor", mi="0.11.85", multiply=0.001, round=2)
Power = MathConv("power", "sensor", mi="0.12.85", round=2)
Energy = MathConv("energy", "sensor", mi="0.13.85", multiply=0.001, round=2)
Current = MathConv("current", "sensor", mi="0.14.85", multiply=0.001, round=2)

ChipTemp = Converter("chip_temperature", "sensor", mi="8.0.2006", enabled=False)

# switches and relays
Outlet = BoolConv("outlet", "switch", mi="4.1.85")
Plug = BoolConv("plug", "switch", mi="4.1.85")
Switch = BoolConv("switch", "switch", mi="4.1.85")
Channel1 = BoolConv("channel_1", "switch", mi="4.1.85")
Channel2 = BoolConv("channel_2", "switch", mi="4.2.85")
Channel3 = BoolConv("channel_3", "switch", mi="4.3.85")

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

PowerOffMemory = MapConv(
    "power_on_state", "switch", mi="8.0.2030", map=POWEROFF_MEMORY, enabled=False
)
ChargeProtect = BoolConv("charge_protect", "switch", mi="8.0.2031", enabled=False)
Led = BoolConv("led", "switch", mi="8.0.2032", enabled=False)

Wireless = BoolConv("wireless", "switch", mi="4.10.85", enabled=False)
Wireless1 = BoolConv("wireless_1", "switch", mi="4.10.85", enabled=False)
Wireless2 = BoolConv("wireless_2", "switch", mi="4.11.85", enabled=False)
Wireless3 = BoolConv("wireless_3", "switch", mi="4.12.85", enabled=False)

# Light = BoolConv("light", "light", mi="4.1.85")
# Brightness = BrightnessConv("brightness", mi="14.1.85", parent="light")
# ColorTemp = Converter("color_temp", mi="14.2.85", parent="light")

# RunState = MapConv("run_state", mi="14.4.85", map=RUN_STATE)

# converts voltage to percent and shows voltage in attributes
# users can adds separate voltage sensor or original percent sensor
Battery = BatteryConv("battery", "sensor", mi="8.0.2008")
BatteryLow = BoolConv("battery_low", "binary_sensor", mi="8.0.9001", enabled=False)
BatteryOrig = Converter("battery_original", mi="8.0.2001", enabled=False)

# zigbee3 devices

# Switch_MI21 = Converter("switch", "switch", mi="2.p.1")
Channel1_MI21 = Converter("channel_1", "switch", mi="2.p.1")
Channel2_MI31 = Converter("channel_2", "switch", mi="3.p.1")

# global props
LUMI_GLOBALS = {
    "8.0.2002": ResetsConv("resets", "sensor"),
    "8.0.2022": Converter("fw_ver", "sensor"),
    "8.0.2036": ParentConv("parent", "sensor"),
    "8.0.2091": OTAConv("ota_progress", "sensor"),
    "8.0.2102": OnlineConv("online", "binary_sensor"),
    # "8.0.2156": Converter("nwk", "sensor"),
}
