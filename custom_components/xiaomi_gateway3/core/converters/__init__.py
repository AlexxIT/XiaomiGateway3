import logging
from dataclasses import dataclass
from typing import List, Optional

from .base import Converter, LUMI_GLOBALS, parse_time
from .const import GATEWAY, ZIGBEE, BLE, MESH, MESH_GROUP_MODEL
from .devices import DEVICES
from .stats import STAT_GLOBALS

try:
    # loading external converters
    # noinspection PyUnresolvedReferences
    from xiaomi_gateway3 import DEVICES
except ModuleNotFoundError:
    pass
except:
    logging.getLogger(__name__).exception("Can't load external converters")


@dataclass
class XDeviceInfo:
    manufacturer: str
    model: str
    name: str
    url: str
    spec: List[Converter]
    ttl: float


def is_mihome_zigbee(model: str) -> bool:
    return model.startswith(("lumi.", "ikea."))


def get_device_info(model: str, type: str) -> Optional[XDeviceInfo]:
    """Type is used to select the default spec if the model didn't match
    earlier. Should be the latest spec in the list.
    """
    for desc in DEVICES:
        if model not in desc and desc.get("default") != type:
            continue
        info = desc.get(model) or ["Unknown", type.upper(), None]
        brand, name, market = info if len(info) == 3 else info + [None]

        if type == ZIGBEE and not is_mihome_zigbee(model):
            url = "https://www.zigbee2mqtt.io/supported-devices/#s=" + market \
                if market else None
        else:
            url = f"https://home.miot-spec.com/s/{model}"

        if market and type == ZIGBEE:
            market = f"{type} {market} ({model})"
        elif market:
            market = f"{type} {market}"
        else:
            market = f"{type} ({model})"

        ttl = desc.get("ttl")
        if isinstance(ttl, str):
            ttl = parse_time(ttl)

        return XDeviceInfo(
            manufacturer=brand,
            model=market,
            name=f"{brand} {name}",
            url=url,
            spec=desc["spec"],
            ttl=ttl
        )
    raise RuntimeError


def get_zigbee_buttons(model: str) -> Optional[list]:
    for device in DEVICES:
        if model not in device:
            continue
        buttons = [
            conv.attr for conv in device["required"]
            if conv.attr.startswith("button")
        ]
        return sorted(set(buttons))
    return None
