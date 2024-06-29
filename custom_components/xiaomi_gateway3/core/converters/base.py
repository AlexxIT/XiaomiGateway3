from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..const import BLE, GATEWAY, MATTER, ZIGBEE

if TYPE_CHECKING:
    from ..device import XDevice

TIME = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def decode_time(value: str) -> float:
    """Conver string time to float time (seconds).
    @type value: 15s or 30m or 24h or 1d
    """
    return float(value[:-1]) * TIME[value[-1]]


def encode_time(value: float) -> str:
    s = ""
    if i := int(value / 86400):
        s += f"{i}d"
        value %= 86400
    if i := int(value / 3600):
        s += f"{i}h"
        value %= 3600
    if i := int(value / 60):
        s += f"{i}m"
        value %= 60
    if i := int(value):
        s += f"{i}s"
    return s or "0s"


@dataclass
class BaseConv:
    attr: str
    domain: str = None
    mi: str | int = None
    entity: dict = None

    def decode(self, device: "XDevice", payload: dict, value):
        payload[self.attr] = value

    def encode(self, device: "XDevice", payload: dict, value):
        if not self.mi or device.type == BLE or ".e." in self.mi:
            return
        if ".p." in self.mi:
            s, p = self.mi.split(".p.")
            if device.type == ZIGBEE:
                payload["cmd"] = "write"
                payload["did"] = device.did
                params = {"siid": int(s), "piid": int(p), "value": value}
                payload.setdefault("mi_spec", []).append(params)
            else:
                payload["method"] = "set_properties"
                params = {
                    "did": device.did,
                    "siid": int(s),
                    "piid": int(p),
                    "value": value,
                }
                payload.setdefault("params", []).append(params)
        elif device.type == MATTER:
            payload["method"] = "set_properties_v3"
            params = {"did": device.did, "iid": self.mi, "value": value}
            payload.setdefault("params", []).append(params)
        else:
            payload["cmd"] = "write"
            payload["did"] = device.did if device.type != GATEWAY else "lumi.0"
            params = {"res_name": self.mi, "value": value}
            payload.setdefault("params", []).append(params)

    def encode_read(self, device: "XDevice", payload: dict):
        if not self.mi or device.type == BLE or ".e." in self.mi:
            return
        if ".p." in self.mi:
            s, p = self.mi.split(".p.")
            if device.type == ZIGBEE:
                payload["cmd"] = "read"
                payload["did"] = device.did
                params = {"siid": int(s), "piid": int(p)}
                payload.setdefault("mi_spec", []).append(params)
            else:
                payload["method"] = "get_properties"
                params = {"did": device.did, "siid": int(s), "piid": int(p)}
                payload.setdefault("params", []).append(params)
        elif device.type == MATTER:
            payload["method"] = "get_properties_v3"
            params = {"did": device.did, "iid": self.mi}
            payload.setdefault("params", []).append(params)
        else:
            payload["cmd"] = "read"
            payload["did"] = device.did if device.type != GATEWAY else "lumi.0"
            params = {"res_name": self.mi}
            payload.setdefault("params", []).append(params)


@dataclass
class ConstConv(BaseConv):
    """In any cases set constant value to attribute."""

    value: bool | int | str = None

    def decode(self, device: "XDevice", payload: dict, value):
        payload[self.attr] = self.value


class BoolConv(BaseConv):
    """Decode from int to bool, encode from bool to int."""

    def decode(self, device: "XDevice", payload: dict, value: int):
        payload[self.attr] = bool(value)

    def encode(self, device: "XDevice", payload: dict, value: bool):
        super().encode(device, payload, int(value))


@dataclass
class MapConv(BaseConv):
    map: dict[int, bool | str] = None

    def decode(self, device: "XDevice", payload: dict, value: int):
        if value in self.map:
            payload[self.attr] = self.map[value]

    def encode(self, device: "XDevice", payload: dict, value):
        value = next(k for k, v in self.map.items() if v == value)
        super().encode(device, payload, value)


@dataclass
class MathConv(BaseConv):
    max: float = float("inf")
    min: float = -float("inf")
    multiply: float = 1.0
    round: int = None
    step: float = 1.0

    def decode(self, device: "XDevice", payload: dict, value: float):
        if self.min <= value <= self.max:
            if self.multiply != 1.0:
                value *= self.multiply
            if self.round is not None:
                # convert to int when round is zero
                value = round(value, self.round or None)
            payload[self.attr] = value

    def encode(self, device: "XDevice", payload: dict, value: float):
        if self.multiply != 1.0:
            value /= self.multiply
        super().encode(device, payload, value)


@dataclass
class MaskConv(BaseConv):
    mask: int = 0

    def decode(self, device: "XDevice", payload: dict, value: int):
        # noinspection PyTypedDict
        device.extra[self.attr] = value
        payload[self.attr] = bool(value & self.mask)

    def encode(self, device: "XDevice", payload: dict, value: bool):
        # noinspection PyTypedDict
        new_value = device.extra.get(self.attr, 0)
        new_value = new_value | self.mask if value else new_value & ~self.mask
        super().encode(device, payload, new_value)


@dataclass
class BrightnessConv(BaseConv):
    max: float = 100.0

    def decode(self, device: "XDevice", payload: dict, value: int):
        payload[self.attr] = value / self.max * 255.0

    def encode(self, device: "XDevice", payload: dict, value: float):
        value = round(value / 255.0 * self.max)
        super().encode(device, payload, int(value))


@dataclass
class ColorTempKelvin(BaseConv):
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
