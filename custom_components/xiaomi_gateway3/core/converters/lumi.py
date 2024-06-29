from dataclasses import dataclass
from typing import TYPE_CHECKING

from .base import BaseConv
from .const import BUTTON, UNKNOWN, BUTTON_BOTH

if TYPE_CHECKING:
    from ..device import XDevice


class ResetsConv(BaseConv):
    # noinspection PyTypedDict
    def decode(self, device: "XDevice", payload: dict, value: int):
        if "resets" in device.params and value > device.params["resets"]:
            device.extra.setdefault("new_resets", 0)
            device.extra["new_resets"] += value - device.params["resets"]

        super().decode(device, payload, value)


class BatVoltConv(BaseConv):
    childs = {"battery_voltage", "battery_original"}
    min: int = 2700
    max: int = 3200

    def decode(self, device: "XDevice", payload: dict, value: int):
        payload["battery_voltage"] = value

        if value <= self.min:
            payload[self.attr] = 0
        elif value >= self.max:
            payload[self.attr] = 100
        else:
            payload[self.attr] = int(100.0 * (value - self.min) / (self.max - self.min))


class ButtonConv(BaseConv):
    def decode(self, device: "XDevice", payload: dict, value: int):
        payload[self.attr] = value
        if self.attr == "button":
            payload["action"] = BUTTON.get(value, UNKNOWN)
        elif self.attr.startswith("button_both"):
            both = BUTTON_BOTH.get(value, UNKNOWN)
            payload["action"] = self.attr + "_" + both

        elif self.attr.startswith("button"):
            payload["action"] = self.attr + "_" + BUTTON.get(value, UNKNOWN)

    def encode_read(self, device: "XDevice", payload: dict):
        pass


class VibrationConv(BaseConv):
    def decode(self, device: "XDevice", payload: dict, value: int):
        payload[self.attr] = value
        # skip tilt and wait tilt_angle
        if value == 1:
            payload["action"] = "vibration"
        elif value == 3:
            payload["action"] = "drop"


class TiltAngleConv(BaseConv):
    def decode(self, device: "XDevice", payload: dict, value: int):
        payload["action"] = "tilt"
        payload["angle"] = value
        payload["vibration"] = 2


class ClimateConv(BaseConv):
    hvac = {"off": 0x01, "heat": 0x10, "cool": 0x11}
    fan = {"low": 0x00, "medium": 0x10, "high": 0x20, "auto": 0x30}

    def decode(self, device: "XDevice", payload: dict, value: int):
        # use payload to push data to climate entity
        # use device extra to pull data on encode
        # noinspection PyTypedDict
        payload[self.attr] = device.extra[self.attr] = value

    def encode(self, device: "XDevice", payload: dict, value: dict):
        if self.attr not in device.extra:
            return
        # noinspection PyTypedDict
        b = bytearray(device.extra[self.attr].to_bytes(4, "big"))
        if "hvac_mode" in value:
            b[0] = self.hvac[value["hvac_mode"]]
        if "fan_mode" in value:
            b[1] = self.fan[value["fan_mode"]]
        if "target_temp" in value:
            b[2] = int(value["target_temp"])
        value = int.from_bytes(b, "big")
        super().encode(device, payload, value)


class ClimateTempConv(BaseConv):
    def decode(self, device: "XDevice", payload: dict, value: int):
        payload[self.attr] = value if value < 255 else 0


# we need get pos with one property and set pos with another
class CurtainPosConv(BaseConv):
    def encode(self, device: "XDevice", payload: dict, value):
        conv = next(c for c in device.converters if c.attr == "target_position")
        conv.encode(device, payload, value)


@dataclass
class LockActionConv(BaseConv):
    map: dict = None

    def decode(self, device: "XDevice", payload: dict, value):
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
class LockConv(BaseConv):
    mask: int = 0

    def decode(self, device: "XDevice", payload: dict, value: int):
        # Hass: On means open (unlocked), Off means closed (locked)
        payload[self.attr] = not bool(value & self.mask)


class AqaraDNDTimeConv(BaseConv):
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


# global props
LUMI_GLOBALS: dict[str, BaseConv] = {
    "8.0.2001": BaseConv("battery_original"),
    "8.0.2002": ResetsConv("resets"),
    "8.0.2003": BaseConv("send_all_cnt"),
    "8.0.2004": BaseConv("send_fail_cnt"),
    "8.0.2005": BaseConv("send_retry_cnt"),
    "8.0.2006": BaseConv("chip_temperature"),
    "8.0.2007": BaseConv("lqi"),
    "8.0.2008": BaseConv("battery_voltage"),
    "8.0.2022": BaseConv("fw_ver"),
    "8.0.2023": BaseConv("hw_ver"),
    "8.0.2036": BaseConv("parent"),
    "8.0.2041": BaseConv("8.0.2041"),  # =55
    "8.0.2091": BaseConv("8.0.2091"),  # ota_progress?
    "8.0.2156": BaseConv("nwk"),
    "8.0.2228": BaseConv("8.0.2228"),  # =4367
    "8.0.2231": BaseConv("8.0.2231"),  # =0
    # skip online state
    # "8.0.2102": OnlineConv("online", "binary_sensor"),
    # "8.0.2156": Converter("nwk", "sensor"),
}
