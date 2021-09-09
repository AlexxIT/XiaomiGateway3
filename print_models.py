from custom_components.xiaomi_gateway3.core.bluetooth import DEVICES as BT
from custom_components.xiaomi_gateway3.core.zigbee import DEVICES as ZB


def print_list(items: list):
    uniq = {}

    for v in items:
        uniq.setdefault(f"{v[0]} {v[1]}", []).append(v[2])

    for k, v in sorted(uniq.items(), key=lambda kv: kv[0]):
        models = ','.join(sorted(set(v)))
        print(f"- {k} ({models})")


print("Zigbee")
print_list([
    v for device in ZB
    for k, v in device.items()
    if len(v) == 3 and k not in ('lumi_spec', 'miot_spec')
])

print("BLE")
print_list([
    v for k, v in BT[0].items()
    if len(v) == 3
])

print("Mesh Bulbs")
print_list([
    v for k, v in BT[1].items()
    if len(v) == 3 and k != 'miot_spec' and v[0] != 'Unknown'
])

print("Mesh Switches")
print_list([
    v for d in BT[2:]
    for k, v in d.items()
    if len(v) == 3 and k != 'miot_spec' and v[0] != 'Unknown'
])
