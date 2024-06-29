from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

from custom_components.xiaomi_gateway3.core.converters import silabs
from custom_components.xiaomi_gateway3.core.converters.silabs import zcl_write


def test_silabs_decode():
    p = silabs.decode({"clusterId": "0x0006", "APSPlayload": "0x18000A00001001"})
    assert p == {"cluster": "on_off", "general_command_id": 10, 0: 1}

    p = silabs.decode({"clusterId": "0x0006", "APSPlayload": "0x08080A04803001"})
    assert p == {"cluster": "on_off", "general_command_id": 10, 32772: 1}

    p = silabs.decode({"clusterId": "0x0006", "APSPlayload": "0x010AFD02"})
    assert p == {"cluster": "on_off", "cluster_command_id": 253, "value": b"\x02"}

    p = silabs.decode({"clusterId": "0x0500", "APSPlayload": "0x096700210000000000"})
    assert p == {
        "cluster": "ias_zone",
        "cluster_command_id": 0,
        "value": {"delay": 0, "extended_status": 0, "zone_id": 0, "zone_status": 33},
    }

    p = silabs.decode({"clusterId": "0x000A", "APSPlayload": "0x102D000000"})
    assert p == {"attribute_ids": [0], "cluster": "time", "general_command_id": 0}

    p = silabs.decode({"clusterId": "0x0400", "APSPlayload": "0x18E30A0000212200"})
    assert p == {"cluster": "illuminance", "general_command_id": 10, 0: 34}

    p = silabs.decode({"clusterId": "0x0402", "APSPlayload": "0x18DC0A0000291F08"})
    assert p == {"cluster": "temperature", "general_command_id": 10, 0: 2079}

    p = silabs.decode(
        {"clusterId": "0x0403", "APSPlayload": "0x18DE0A000029E003140028FF100029C526"}
    )
    assert p == {
        "cluster": "pressure",
        "general_command_id": 10,
        0: 992,
        20: -1,
        16: 9925,
    }

    p = silabs.decode({"clusterId": "0x0405", "APSPlayload": "0x18DD0A000021480D"})
    assert p == {"cluster": "humidity", "general_command_id": 10, 0: 3400}

    p = silabs.decode({"clusterId": "0x0406", "APSPlayload": "0x18E40A00001801"})
    assert p == {"cluster": "occupancy", "general_command_id": 10, 0: 1}

    p = silabs.decode({"clusterId": "0x0102", "APSPlayload": "0x08680A08002000"})
    assert p == {"cluster": "window_covering", "general_command_id": 10, 8: 0}

    p = silabs.decode({"clusterId": "0x0001", "APSPlayload": "0x08690A200020FF"})
    assert p == {"cluster": "power", "general_command_id": 10, 32: 255}

    p = silabs.decode(
        {"clusterId": "0xFCC0", "APSPlayload": "0x1D6E12B003080401010401000000"}
    )
    assert p == {
        "cluster": "manufacturer_specific",
        "cluster_command_id": 3,
        "value": b"\x08\x04\x01\x01\x04\x01\x00\x00\x00",
    }


def test_aqara_gas():
    p = silabs.decode(
        {
            "clusterId": "0x0500",
            "APSPlayload": "0x1C5F111A01F0FF00270800013800000102",
        }
    )
    assert p == {
        "cluster": "ias_zone",
        "general_command_id": 1,
        65520: 0x0201000038010008,
    }

    p = silabs.decode(
        {
            "clusterId": "0x0500",
            "APSPlayload": "0x1C5F113301F0FF00270800013800000202",
        }
    )
    assert p == {
        "cluster": "ias_zone",
        "general_command_id": 1,
        65520: 0x0202000038010008,
    }

    p = silabs.decode(
        {
            "clusterId": "0x0500",
            "APSPlayload": "0x1C5F113501F0FF00270800013800000302",
        }
    )
    assert p == {
        "cluster": "ias_zone",
        "general_command_id": 1,
        65520: 0x0203000038010008,
    }


def test_aqara_smoke():
    p = silabs.decode({"clusterId": "0x0001", "APSPlayload": "0x183B01210086"})
    assert p == {"cluster": "power", "general_command_id": 1, 33: None}

    p = silabs.decode(
        {
            "clusterId": "0x0500",
            "APSPlayload": "0x1C5F115501F0FF00270200011100000101",
        }
    )
    assert p == {
        "cluster": "ias_zone",
        "general_command_id": 1,
        0xFFF0: 0x101000011010002,
    }

    p = silabs.decode(
        {
            "clusterId": "0x0500",
            "APSPlayload": "0x1C5F115701F0FF00270300011100000201",
        }
    )
    assert p == {
        "cluster": "ias_zone",
        "general_command_id": 1,
        0xFFF0: 0x102000011010003,
    }

    p = silabs.decode(
        {
            "clusterId": "0x0500",
            "APSPlayload": "0x1C5F115B01F0FF00270200011100000301",
        }
    )
    assert p == {
        "cluster": "ias_zone",
        "general_command_id": 1,
        0xFFF0: 0x103000011010002,
    }


def test_silabs_decode_zdo():
    p = silabs.decode(
        {
            "clusterId": "0x8000",
            "sourceEndpoint": "0x00",
            "APSPlayload": "0x0200FFEECC03008D15002723",
        }
    )
    assert p == {
        "ieee": "00:15:8d:00:03:cc:ee:ff",
        "nwk": "0x2327",
        "status": "SUCCESS",
        "zdo_command": "NWK_addr_rsp",
    }


def test_xiaomi_basic():
    p = silabs.decode(
        {
            "clusterId": "0x0000",
            "APSPlayload": "0x1C5F11460A01FF42220121D10B0328190421A8430521090006240100000000082104020A210000641000",
        }
    )
    assert p == {
        "cluster": "basic",
        "general_command_id": 10,
        0xFF01: {1: 3025, 3: 25, 4: 17320, 5: 9, 6: 1, 8: 516, 10: 0, 100: 0},
    }

    p = silabs.decode(
        {
            "clusterId": "0x0000",
            "APSPlayload": "0x18370A01FF42280121F90B03281B0421A84305211A00062401000000000A21000008210410642002962300000000",
        }
    )
    assert p == {
        "cluster": "basic",
        "general_command_id": 10,
        0xFF01: {1: 3065, 3: 27, 4: 17320, 5: 26, 6: 1, 8: 4100, 10: 0, 100: 2, 150: 0},
    }

    # no leak (100=0)
    p = silabs.decode(
        {
            "clusterId": "0x0000",
            "APSPlayload": "0x1C5F11520A050042156C756D692E73656E736F725F776C65616B2E61713101FF42220121D10B03281C0421A8430521080006240000000000082104020A210000641000",
        }
    )
    assert p == {
        "cluster": "basic",
        "general_command_id": 10,
        5: "lumi.sensor_wleak.aq1",
        0xFF01: {1: 3025, 3: 28, 4: 17320, 5: 8, 6: 0, 8: 516, 10: 0, 100: 0},
    }

    # leak detected (100=1)
    p = silabs.decode(
        {
            "clusterId": "0x0000",
            "APSPlayload": "0x1C5F11560A050042156C756D692E73656E736F725F776C65616B2E61713101FF42220121D10B03281C0421A8430521080006240300000000082104020A210000641001",
        }
    )
    assert p == {
        "cluster": "basic",
        "general_command_id": 10,
        5: "lumi.sensor_wleak.aq1",
        65281: {1: 3025, 3: 28, 4: 17320, 5: 8, 6: 3, 8: 516, 10: 0, 100: 1},
    }

    p = silabs.decode(
        {
            "clusterId": "0x0000",
            "APSPlayload": "0x1C5F119F0A01FF421B03282D05214B00082108210921020464200B962300000000",
        }
    )
    assert p == {
        "cluster": "basic",
        "general_command_id": 10,
        65281: {3: 45, 5: 75, 8: 8456, 9: 1026, 100: 11, 150: 0},
    }


def test_zcl_read():
    p = silabs.zcl_read("0x1234", 1, OnOff.cluster_id, OnOff.AttributeDefs.on_off.id)
    assert p == [
        {"commandcli": "zcl global read 6 0"},
        {"commandcli": "send 0x1234 1 1"},
    ]

    p = silabs.zcl_write("0x1234", 1, 0xFCC0, 9, 1, type_id=0x20, mfg=0x115F)
    assert p == [
        {"commandcli": "zcl mfg-code 4447"},
        {"commandcli": "zcl global write 64704 9 32 {01}"},
        {"commandcli": "send 0x1234 1 1"},
    ]


def test_zcl_write():
    p = zcl_write("0x1234", 1, 6, 0, 1)
    assert p == [
        {"commandcli": "zcl global write 6 0 16 {01}"},
        {"commandcli": "send 0x1234 1 1"},
    ]


def test_zdo():
    # {"commands":[{"commandcli":"zdo ieee 0xe984"}]}
    p = silabs.decode(
        {
            "clusterId": "0x8001",
            "sourceEndpoint": "0x00",
            "APSPlayload": "0x2E00888888881044EF5484E9",
        }
    )
    s = [f"{k}: {v}" for k, v in p.items()]
    assert s == [
        "zdo_command: IEEE_addr_rsp",
        "status: <Status.SUCCESS: 0>",
        "ieee: 54:ef:44:10:88:88:88:88",
        "nwk: 0xE984",
    ]


def test_general_4():
    p = silabs.decode({"clusterId": "0x0000", "APSPlayload": "0x1C5F11760400"})
    assert p == {"cluster": "basic", "general_command_id": 4, None: 0}
