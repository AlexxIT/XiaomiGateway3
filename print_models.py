from custom_components.xiaomi_gateway3.core.bluetooth import DEVICES as BT
from custom_components.xiaomi_gateway3.core.utils import DEVICES as ZB

zigbee = {}

for device in ZB:
    for k, v in device.items():
        if k in ('params', 'mi_spec') or v[1] == 'Gateway 3' or len(v) < 3:
            continue
        name = f"{v[0]} {v[1]}"
        zigbee.setdefault(name, []).append(v[2])

print('Zigbee')
for k, v in sorted(zigbee.items(), key=lambda kv: kv[0]):
    models = ','.join(sorted(set(v)))
    print(f"- {k} ({models})")

ble = []
mesh = []

for v in BT.values():
    if len(v) < 3:
        continue
    name = f"- {v[0]} {v[1]} ({v[2]})"
    if 'Mesh' in name:
        mesh.append(name)
    else:
        ble.append(name)

print('BLE')
print('\n'.join(sorted(ble)))
print('Mesh')
print('\n'.join(sorted(mesh)))
