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
    req_converters: List[Converter]
    opt_converters: List[Converter]
    config: List[Config]


def get_device_info(model: str, type: str) -> Optional[XDeviceInfo]:
    """Type is used to select the default spec if the model didn't match
    earlier. Should be the latest spec in the list.
    """
    for spec in DEVICES:
        if model not in spec and spec.get("default") != type:
            continue
        info = spec.get(model) or ["Unknown", type.upper(), model]

        if type == GATEWAY:
            market = f"Wi-Fi {info[2]}"
        elif type == ZIGBEE:
            market = f"Zigbee {info[2]} ({model})"
        elif type == BLE:
            market = f"BLE {info[2]}"
        elif type == MESH:
            market = f"Mesh {info[2]}"
        else:
            raise RuntimeError

        return XDeviceInfo(
            manufacturer=info[0],
            model=market,
            name=f"{info[0]} {info[1]}",
            req_converters=spec["required"],
            opt_converters=spec.get("optional"),
            config=spec.get("config"),
        )
    return None


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
