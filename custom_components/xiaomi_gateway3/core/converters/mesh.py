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
