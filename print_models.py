import re

from custom_components.xiaomi_gateway3.core.converters.devices import DEVICES
from custom_components.xiaomi_gateway3.core.converters.stats import BLEStats

columns = [
    "Brand", "Name", "Model", "Default entities", "Optional entities", "S"
]
header = ["---"] * len(columns)

devices = {}

for device in DEVICES:
    # skip devices with bad support
    if device.get("support", 3) < 3:
        continue

    for k, v in device.items():
        if not isinstance(v, list) or k in ("required", "optional", "config"):
            continue

        brand, name, model = v

        optional = device.get("optional", [])

        if isinstance(k, str):
            if "gateway" in k:
                type = "Gateways"
            elif k.startswith("lumi.") or k.startswith("ikea."):
                type = "Xiaomi Zigbee"
            else:
                type = "Other Zigbee"
        elif BLEStats in optional:
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
            req = ", ".join([
                conv.attr + "*" if conv.lazy else conv.attr
                for conv in device["required"] if conv.domain
            ])
        else:
            req = "*"

        opt = ", ".join([
            conv.attr for conv in device.get("optional", []) if conv.domain
        ])

        support = str(device.get("support", ""))

        model = f'[{model}]({link})'

        items.append([brand, name, model, req, opt, support])

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
