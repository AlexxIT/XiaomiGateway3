import re
from typing import TYPE_CHECKING

from .base import BaseConv

if TYPE_CHECKING:
    from ..device import XDevice


class InductionRange(BaseConv):
    def decode(self, device: "XDevice", payload: dict, value: int):
        mask = "0 0.8 1.5 2.3 3.0 3.8 4.5 5.3 6"
        for i in range(0, 8):
            v = "+" if value & (1 << i) else "_"
            mask = mask.replace(" ", v, 1)
        payload[self.attr] = mask

    def encode(self, device: "XDevice", payload: dict, value: str):
        m = re.findall(r"[+xv_-]", value)
        if len(m) != 8:
            return
        mask = 0
        for i, v in enumerate(m):
            if v in "+xv":
                mask |= 1 << i
        super().encode(device, payload, mask)


class GiotTimePatternConv(BaseConv):
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

    def decode(self, device: "XDevice", payload: dict, value: int):
        value = str(value)
        if len(value) != 8:
            return
        payload[self.attr] = f"{value[:2]}:{value[2:4]}-{value[4:6]}:{value[6:]}"

    def encode(self, device: "XDevice", payload: dict, value: str):
        value = value.replace(":", "").replace("-", "")
        if len(value) != 8:
            return
        super().encode(device, payload, int(value))
