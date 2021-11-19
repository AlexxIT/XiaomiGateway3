from custom_components.xiaomi_gateway3.core.device import XDevice, BLE

DID = "blt.3.abc"
MAC = "112233aabbcc"


def test_night_light():
    device = XDevice(BLE, 2038, DID, MAC)
    assert device.info.name == "Xiaomi Night Light 2"
    device.setup_converters()

    p = device.decode("mibeacon", {"eid": 15, "edata": "640000"})
    assert p == {'light': True, 'motion': True}
    p = device.decode("mibeacon", {'eid': 4103, 'edata': '640000'})
    assert p == {'light': True}
    p = device.decode("mibeacon", {'eid': 4106, 'edata': '64'})
    assert p == {'battery': 100}
    p = device.decode("mibeacon", {'eid': 4119, 'edata': '78000000'})
    assert p == {'idle_time': 120}


def test_kettle():
    device = XDevice(BLE, 131, DID, MAC)
    assert device.info.name == "Xiaomi Kettle"
    device.setup_converters()

    p = device.decode("mibeacon", {'eid': 4101, 'edata': '0063'})
    assert p == {'power': False, 'state': 'idle', 'temperature': 99}
    p = device.decode("mibeacon", {'eid': 4101, 'edata': '0154'})
    assert p == {'power': True, 'state': 'heat', 'temperature': 84}
