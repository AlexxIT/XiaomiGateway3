import re

from custom_components.xiaomi_gateway3.core.converters.devices import DEVICES
from custom_components.xiaomi_gateway3.core.converters.mibeacon import MiBeacon

columns = [
    "Brand", "Name", "Model", "Entities", "S"
]
header = ["---"] * len(columns)

devices = {}

for device in DEVICES:
    # skip devices with bad support
    if device.get("support", 3) < 3:
        continue

    for k, v in device.items():
        if not isinstance(v, list) or k in ("spec", "config"):
            continue

        brand, name, model = v if len(v) == 3 else v + [k]

        if isinstance(k, str):
            if "gateway" in k:
                type = "Gateways"
            elif k.startswith("lumi.") or k.startswith("ikea."):
                type = "Xiaomi Zigbee"
            else:
                type = "Other Zigbee"
        elif MiBeacon in device["spec"]:
            type = "Xiaomi BLE"
        else:
            type = "Xiaomi Mesh"

        if type != "Other Zigbee":
            link = f"https://home.miot-spec.com/s/{k}"
        else:
            link = f"https://www.zigbee2mqtt.io/supported-devices/#s={model}"

        items = devices.setdefault(type, [])

        # skip if model already exists
        if any(True for i in items if model in i[2]):
            continue

        # skip BLE with unknown spec
        if "default" not in device:
            spec = ", ".join([
                conv.attr + "*" if conv.enabled is None else conv.attr
                for conv in device["spec"] if conv.domain
            ])
        else:
            spec = "*"

        support = str(device.get("support", ""))

        model = f'[{model}]({link})'

        items.append([brand, name, model, spec, support])

out = "<!--supported-->\n"
for k, v in devices.items():
    out += f"## Supported {k}\n\nTotal devices: {len(v)}\n\n"
    out += "|".join(columns) + "\n"
    out += "|".join(header) + "\n"
    for line in sorted(v):
        out += "|".join(line) + "\n"
    out += "\n"
out += "<!--supported-->"

raw = open("README.md", "r", encoding="utf-8").read()
raw = re.sub(
    r"<!--supported-->(.+?)<!--supported-->", out, raw, flags=re.DOTALL
)
open("README.md", "w", encoding="utf-8").write(raw)
