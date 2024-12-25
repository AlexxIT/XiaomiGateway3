from custom_components.xiaomi_gateway3.core.devices import DEVICES

columns = ["Brand", "Name", "Model", "Entities"]
header = ["---"] * len(columns)

devices = {}
models = set()

is_ble = True

for i, device in enumerate(DEVICES):
    # skip devices with bad support
    if device.pop("support", 3) < 3:
        continue

    spec = device.pop("spec")

    # skip BLE with unknown spec
    if "default" not in device:
        spec = ", ".join([conv.attr for conv in spec if conv.domain])
    else:
        spec = "*"

    for model, info in device.items():
        if not isinstance(info, list):
            continue

        if model in models:
            print("duplicate:", model)
        else:
            models.add(model)

        if isinstance(model, str) and model not in info:
            info.append(model)

        market_brand = info[0] or "~"
        market_name = info[1]
        market_model = ", ".join(info[2:]) if len(info) > 2 else ""

        if isinstance(model, str):
            if "gateway" in model:
                kind = "Gateways"
            elif model.startswith(("lumi.", "ikea.")):
                kind = "Xiaomi Zigbee"
            elif model.startswith("matter."):
                kind = "Matter"
            else:
                kind = "Other Zigbee"
        elif isinstance(model, int):
            if is_ble:
                kind = "Xiaomi BLE"
            else:
                kind = "Xiaomi Mesh"
        else:
            kind = "Unknown"

        devices.setdefault(kind, []).append(
            [market_brand, market_name, market_model, spec]
        )

    if device.get("default") == "ble":
        is_ble = False

out = f"# Supported devices\n\nTotal devices: {len(models)}\n\n"
for k, v in devices.items():
    out += f"## Supported {k}\n\nTotal devices: {len(v)}\n\n"
    out += "|" + "|".join(columns) + "|\n"
    out += "|" + "|".join(header) + "|\n"
    for line in sorted(v):
        out += "|" + "|".join(line) + "|\n"
    out += "\n"

open("DEVICES.md", "w", encoding="utf-8").write(out)
