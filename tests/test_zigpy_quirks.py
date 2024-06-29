import zigpy.device
import zigpy.quirks
from zigpy.const import SIG_ENDPOINTS
from zigpy.device import Device


def generate_device(manufacturer: str, model: str) -> Device | None:
    """Generate device from quirks. Should be called earlier:
        zhaquirks.setup()

    Or direct import:
        from zhaquirks.xiaomi.mija.sensor_switch import MijaButton

    Used like a Cluster:
        hdr, value = device.deserialize(<endpoint_id>, <cluster_id>, data)
    """
    quirks = zigpy.quirks.get_quirk_list(manufacturer, model)
    if not quirks:
        return None

    # noinspection PyTypeChecker
    device = Device(None, None, 0)
    device.manufacturer = manufacturer
    device.model = model

    quirk: zigpy.quirks.CustomDevice = quirks[0]
    if SIG_ENDPOINTS in quirk.replacement:
        for endpoint_id in quirk.replacement[SIG_ENDPOINTS].keys():
            device.add_endpoint(endpoint_id)

    return quirks[0](None, None, 0, device)
