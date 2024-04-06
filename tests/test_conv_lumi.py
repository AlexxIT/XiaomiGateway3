from custom_components.xiaomi_gateway3.core.device import XDevice


def test_plug_heartbeat():
    device = XDevice("lumi.plug")
    assert device.market_name == "Xiaomi Plug CN"

    params = [
        {"res_name": "4.1.85", "value": 1},
        {"res_name": "8.0.2006", "value": 39},
        {"res_name": "0.12.85", "value": 14.56},
        {"res_name": "0.13.85", "value": 357696.31},
        {"res_name": "8.0.2002", "value": 24},
        {"res_name": "8.0.2231", "value": 0},
        {"res_name": "8.0.2022", "value": 90},
        {"res_name": "8.0.2023", "value": 19},
        {"res_name": "8.0.2228", "value": 4367},
        {"res_name": "8.0.2007", "value": 160},
    ]
    assert device.decode(params) == {
        "8.0.2228": 4367,
        "8.0.2231": 0,
        "chip_temperature": 39,
        "energy": 357.7,
        "fw_ver": 90,
        "hw_ver": 19,
        "lqi": 160,
        "plug": True,
        "power": 14.56,
        "resets": 24,
    }


def test_sensor_ht_heartbeat():
    device = XDevice("lumi.sensor_ht")
    assert device.market_name == "Xiaomi TH Sensor"

    p = device.decode(
        [
            {"res_name": "8.0.2008", "value": 2955},
            {"res_name": "8.0.2001", "value": 59},
            {"res_name": "8.0.2011", "value": 1},
            {"res_name": "8.0.2010", "value": 3},
            {"res_name": "8.0.2012", "value": 10},
            {"res_name": "8.0.2013", "value": 1},
            {"res_name": "8.0.2002", "value": 11651},
            {"res_name": "8.0.2003", "value": 2},
            {"res_name": "8.0.2004", "value": 0},
            {"res_name": "8.0.2005", "value": 0},
            {"res_name": "8.0.2033", "value": 0},
            {"res_name": "0.1.85", "value": 2384},
            {"res_name": "0.2.85", "value": 4509},
            {"res_name": "8.0.2036", "value": ""},
            {"res_name": "8.0.2022", "value": 0},
            {"res_name": "8.0.2023", "value": 0},
            {"res_name": "8.0.2007", "value": 216},
        ]
    )
    assert p == {
        "battery": 51,
        "battery_voltage": 2955,
        "resets": 11651,
        "temperature": 23.84,
        "humidity": 45.09,
        "fw_ver": 0,
        "battery_original": 59,
        "hw_ver": 0,
        "lqi": 216,
        "parent": "",
        "send_all_cnt": 2,
        "send_fail_cnt": 0,
        "send_retry_cnt": 0,
    }


def test_sensor_motion():
    device = XDevice("lumi.sensor_motion.aq2")
    assert device.market_name == "Aqara Motion Sensor"

    p = device.decode(
        [
            {"res_name": "0.3.85", "value": 6},
            {"res_name": "0.4.85", "value": 6},
            {"res_name": "3.1.85", "value": 1},
        ]
    )
    assert p == {"illuminance": 6, "motion": True}


def test_sensor_motion_e1():
    device = XDevice("lumi.motion.acn001")
    assert device.market_name == "Aqara Motion Sensor E1"

    p = device.decode(
        [{"siid": 2, "eiid": 1, "arguments": [{"siid": 2, "piid": 1, "value": 9}]}]
    )
    assert p == {"illuminance": 9, "motion": True}

    p = device.decode([{"siid": 2, "piid": 1, "value": 10, "code": 0}])
    assert p == {"illuminance": 10}


def test_opple_buttons():
    device = XDevice("lumi.remote.b686opcn01")
    assert device.market_name == "Aqara Opple Six Button CN"

    p = device.decode([{"res_name": "13.1.85", "value": 1}])
    assert p == {"action": "button_1_single", "button_1": 1}

    p = device.decode([{"res_name": "13.2.85", "value": 16}])
    assert p == {"action": "button_2_hold", "button_2": 16}


def test_light():
    device = XDevice("ikea.light.led1650r5")
    assert device.market_name == "IKEA Bulb GU10 400 lm"

    p = device.decode([{"res_name": "14.1.85", "value": 80}])
    assert p == {"brightness": 204.0}


def test_lock_s2():
    device = XDevice("lumi.lock.acn02")
    assert device.market_name == "Aqara Door Lock S2 CN"

    p = device.decode([{"res_name": "13.16.85", "value": 17}])
    assert p == {"square": False, "reverse": True, "latch": False}

    p = device.decode(
        [
            {"res_name": "13.1.85", "value": 65536},
            {"res_name": "13.15.85", "value": 1},
        ]
    )
    assert p == {"action": "lock", "key_id": 65536, "method": "fingerprint"}


def test_lock_s2_pro():
    device = XDevice("lumi.lock.acn03")
    assert device.market_name == "Aqara Door Lock S2 Pro CN"

    p = device.decode(
        [
            {"res_name": "13.16.85", "value": 81},
            {"res_name": "3.1.85", "value": 0},
            {"res_name": "13.28.85", "value": 3},
        ]
    )
    assert p == {
        "lock": False,
        "square": False,
        "reverse": True,
        "latch": False,
        "action": "lock",
        "lock_state": "door_locked",
    }

    p = device.decode(
        [
            {"res_name": "13.16.85", "value": 64},
            {"res_name": "13.25.85", "value": 0},
            {"res_name": "13.28.85", "value": 2},
        ]
    )
    assert p == {
        "lock": False,
        "square": True,
        "reverse": True,
        "latch": True,
        "action": "lock",
        "lock_control": "in_unlocked",
        "lock_state": "door_without_lift",
    }

    p = device.decode([{"res_name": "13.5.85", "value": 512}])
    assert p == {"action": "doorbell"}

    p = device.decode(
        [{"res_name": "13.1.85", "value": 131072}, {"res_name": "13.15.85", "value": 2}]
    )
    assert p == {"action": "lock", "key_id": 131072}

    p = device.decode([{"res_name": "13.5.85", "value": 4}])
    assert p == {"action": "alarm", "alarm": "unlocked"}

    p = device.decode(
        [{"res_name": "13.26.85", "value": 2}, {"res_name": "13.28.85", "value": 1}]
    )
    assert p == {"action": "lock", "door_state": "ajar", "lock_state": "door_opened"}

    p = device.decode([{"res_name": "13.4.85", "value": 1}])
    assert p == {"action": "error", "error": "fing_wrong", "fing_wrong": 1}

    p = device.decode([{"res_name": "13.3.85", "value": 3}])
    assert p == {"action": "error", "error": "psw_wrong", "psw_wrong": 3}


def test_climate():
    device = XDevice("lumi.airrtc.tcpecn02")
    assert device.market_name == "Aqara Thermostat S2 CN"

    p = device.decode(
        [
            {"res_name": "14.2.85", "value": 268435455},
            {"res_name": "14.8.85", "value": 15},
            {"res_name": "14.9.85", "value": 255},
            {"res_name": "14.10.85", "value": 15},
            {"res_name": "3.2.85", "value": 63},
            {"res_name": "3.1.85", "value": 0},
        ]
    )
    assert p == {
        "climate": 0xFFFFFFF,
        "hvac_mode": "off",
        "target_temp": 0,
        "current_temp": 63,
        "power": False,
    }

    params = [
        {"res_name": "14.2.85", "value": 288366197},
        {"res_name": "14.8.85", "value": 1},
        {"res_name": "14.9.85", "value": 30},
        {"res_name": "14.10.85", "value": 3},
        {"res_name": "3.2.85", "value": 29},
        {"res_name": "3.1.85", "value": 1},
    ]
    p = device.decode(params)
    assert p == {
        "climate": 0x11301E75,
        "hvac_mode": "cool",
        "target_temp": 30,
        "fan_mode": "auto",
        "current_temp": 29,
        "power": True,
    }

    x = params[0]["value"]
    p = device.encode({"climate": {"climate": x, "fan_mode": "low"}})
    y = p["params"][0]["value"]
    assert x != y
    p = device.encode({"climate": {"climate": y, "fan_mode": "auto"}})
    y = p["params"][0]["value"]
    assert x == y


def test_mi_spec():
    device = XDevice("lumi.sen_ill.mgl01")
    assert device.market_name == "Xiaomi Light Sensor EU"

    p = device.decode([{"siid": 3, "piid": 1, "value": 3100}])
    assert p == {"battery": 80, "battery_voltage": 3100}

    p = device.decode([{"piid": 1, "siid": 2, "value": 33}])
    assert p == {"illuminance": 33}

    device = XDevice("lumi.motion.agl04")
    assert device.market_name == "Aqara Precision Motion Sensor EU"

    p = device.decode([{"siid": 4, "eiid": 1, "arguments": []}])
    assert p == {"motion": True}


def test_lumi_encode():
    device = XDevice("lumi.plug")

    p = device.encode({"plug": True})
    assert p["params"] == [{"res_name": "4.1.85", "value": 1}]

    device = XDevice("lumi.switch.l0agl1")
    assert device.market_name == "Aqara Relay T1 EU (no N)"

    p = device.encode({"switch": True})
    assert p["params"] == [{"did": None, "siid": 2, "piid": 1, "value": True}]


def test_lumi_curtain():
    device = XDevice("lumi.curtain")
    assert device.market_name == "Aqara Curtain"

    p = device.decode([{"res_name": "14.2.85", "value": 1}])
    assert p == {"motor": "open"}

    p = device.decode([{"res_name": "1.1.85", "value": 100}])
    assert p == {"position": 100}

    p = device.encode({"motor": "stop"})
    assert p["params"] == [{"res_name": "14.2.85", "value": 2}]

    p = device.encode({"position": 48})
    assert p["params"] == [{"res_name": "1.1.85", "value": 48}]


def test_mi_curtain():
    device = XDevice("lumi.curtain.acn002")
    assert device.market_name == "Aqara Roller Shade E1 CN"

    p = device.decode(
        [
            {"siid": 2, "piid": 1, "value": 0},
            {"siid": 2, "piid": 3, "value": 0},
            {"siid": 2, "piid": 4, "value": 60},
            {"siid": 2, "piid": 5, "value": 60},
        ]
    )
    assert p == {"position": 60, "target_position": 60}

    p = device.decode(
        [
            {"siid": 3, "piid": 1, "value": 1},
            {"siid": 3, "piid": 2, "value": 7317},
            {"siid": 3, "piid": 3, "value": 0},
            {"siid": 3, "piid": 4, "value": 48},
        ]
    )
    assert p == {
        "battery": 48,
        "battery_charging": False,
        "battery_low": False,
        "battery_voltage": 7317,
    }

    p = device.decode([{"siid": 2, "piid": 6, "value": 0}])
    assert p == {"run_state": "closing"}

    p = device.decode([{"siid": 2, "piid": 2, "value": 1}])
    assert p == {"motor": "close"}

    p = device.encode({"motor": "open"})
    assert p["params"] == [{"did": None, "siid": 2, "piid": 2, "value": 2}]

    p = device.encode({"position": 60})
    assert p["params"] == [{"did": None, "siid": 2, "piid": 4, "value": 60}]


def test_gateway():
    device = XDevice("lumi.gateway.mgl03")
    assert device.market_name == "Xiaomi Multimode Gateway"

    p = device.decode([{"res_name": "8.0.2082", "value": "lumi.1234567890"}])
    assert p == {"remove_did": "lumi.1234567890"}

    p = device.decode([{"res_name": "8.0.2082", "value": {"did": "lumi.1234567890"}}])
    assert p == {"remove_did": {"did": "lumi.1234567890"}}


def test_error():
    device = XDevice("lumi.motion.agl04")
    assert device.market_name == "Aqara Precision Motion Sensor EU"

    p = device.decode([{"siid": 10, "piid": 1, "code": -5020}])
    assert p == {}

    device = XDevice("lumi.sensor_magnet.aq2")
    assert device.market_name == "Aqara Door/Window Sensor"

    p = device.decode([{"res_name": "8.0.2102", "error_code": -5020}])
    assert p == {}


def test_resets():
    device = XDevice("lumi.plug")

    p = device.decode({"res_name": "8.0.2002", "value": 24})
    assert p == {"resets": 24}
    device.params.update(p)

    p = device.decode({"res_name": "8.0.2002", "value": 27})
    assert p == {"resets": 27}
    assert device.extra.get("new_resets") == 3


def test_aqara_dnd_time():
    device = XDevice("lumi.switch.acn040")

    p = device.decode([{"piid": 3, "siid": 6, "value": 118030358}])
    assert p == {"led_dnd_time": "22:00-09:07"}

    p = device.encode({"led_dnd_time": "22:00-09:07"})
    assert p["params"] == [{"did": None, "siid": 6, "piid": 3, "value": 118030358}]

    p = device.encode({"led_dnd_time": "23:59-23:59"})
    assert p["params"] == [{"did": None, "siid": 6, "piid": 3, "value": 991378199}]

    p = device.decode([{"piid": 3, "siid": 6, "value": 991378199}])
    assert p == {"led_dnd_time": "23:59-23:59"}


def test_gas():
    device = XDevice("lumi.sensor_natgas")
    # attrs = {"gas", "gas_density", "sensitivity"}
    attrs = {"gas", "gas_density"}
    p = device.encode_read(attrs)
    assert p


def test_aqara_motion_e1():
    device = XDevice("lumi.motion.acn001")
    p = device.decode({"siid": 2, "eiid": 1, "arguments": [{"piid": 1, "value": 179}]})
    assert p == {"illuminance": 179, "motion": True}
