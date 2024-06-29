DOMAIN = "xiaomi_gateway3"

GATEWAY = "gateway"
ZIGBEE = "zigbee"
BLE = "ble"
MESH = "mesh"
GROUP = "group"
MATTER = "matter"

SUPPORTED_MODELS = (
    "lumi.gateway.mgl03",
    "lumi.gateway.aqcn02",
    "lumi.gateway.aqcn03",
    "lumi.gateway.mcn001",
    "lumi.gateway.mgl001",
)

PID_WIFI = 0
PID_BLE = 6
PID_WIFI_BLE = 8


def source_hash() -> str:
    if source_hash.__doc__:
        return source_hash.__doc__

    try:
        import hashlib
        import os

        m = hashlib.md5()
        path = os.path.dirname(os.path.dirname(__file__))
        for root, dirs, files in os.walk(path):
            dirs.sort()
            for file in sorted(files):
                if not file.endswith(".py"):
                    continue
                path = os.path.join(root, file)
                with open(path, "rb") as f:
                    m.update(f.read())

        source_hash.__doc__ = m.hexdigest()[:7]
        return source_hash.__doc__

    except Exception as e:
        return repr(e)
