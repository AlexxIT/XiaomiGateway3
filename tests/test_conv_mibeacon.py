from homeassistant.components.sensor import DOMAIN

from custom_components.xiaomi_gateway3.core.device import XDevice, BLE

assert DOMAIN  # fix circular import

DID = "blt.3.abc"
MAC = "112233aabbcc"
DID2 = "123456789"  # locks have nubm did


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


def test_new_th():
    device = XDevice(BLE, 4611, DID, MAC)
    assert device.info.name == "Xiaomi TH Sensor"
    device.setup_converters()

    p = device.decode("mibeacon", {'eid': 19464, 'edata': 'cdcc3e42'})
    assert p == {'humidity': 47.7}
    p = device.decode("mibeacon", {'eid': 19457, 'edata': 'cdcca841'})
    assert p == {'temperature': 21.1}


def test_lock():
    device = XDevice(BLE, 1694, DID2, MAC)
    assert device.info.name == "Aqara Door Lock N100 (Bluetooth)"
    device.setup_converters()

    p = device.decode("mibeacon", {'eid': 4106, 'edata': '329aaecd62'})
    assert p == {'battery': 50}

    p = device.decode("mibeacon", {"eid": 11, "edata": "a400000000b8aecd62"})
    assert p

    p = device.decode("mibeacon", {"eid": 7, "edata": "00c5aecd62"})
    assert p

    p = device.decode("mibeacon", {"eid": 7, "edata": "01cbaecd62"})
    assert p

    p = device.decode("mibeacon", {"eid": 11, "edata": "2002000180c4aecd62"})
    assert p

    p = device.decode("mibeacon", {"eid": 6, "edata": "ffffffff00"})
    assert p
