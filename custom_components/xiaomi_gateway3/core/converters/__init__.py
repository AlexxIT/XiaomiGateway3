import logging
from dataclasses import dataclass
from typing import List, Optional

from .base import Config, Converter, LUMI_GLOBALS
from .const import GATEWAY, ZIGBEE, BLE, MESH, MESH_GROUP_MODEL, UNKNOWN
from .devices import DEVICES

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
    config: List[Config]


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

        return XDeviceInfo(
            manufacturer=brand,
            model=market,
            name=f"{brand} {name}",
            url=url,
            spec=desc["spec"],
            config=desc.get("config"),
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
