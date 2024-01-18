DOMAIN = "xiaomi_gateway3"
TITLE = "Xiaomi Gateway 3"

PID_WIFI = 0
PID_BLE = 6
PID_WIFI_BLE = 8


def source_hash() -> str:
    if source_hash.__doc__:
        return source_hash.__doc__

    try:
        return _extracted_from_source_hash_6(source_hash)
    except Exception as e:
        return f"{type(e).__name__}: {e}"


# TODO Rename this here and in `source_hash`
def _extracted_from_source_hash_6(source_hash):
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
