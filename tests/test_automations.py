from custom_components.xiaomi_gateway3.device_trigger import get_actions

from custom_components.xiaomi_gateway3.core.device import XDevice


def test_buttons():
    device = XDevice("lumi.sensor_switch")
    p = get_actions(device.human_model)
    assert p == ["single", "double", "triple", "hold", "release"]

    device = XDevice("lumi.ctrl_ln2")
    p = get_actions(device.human_model)
    assert p == [
        "button_1_single",
        "button_1_double",
        "button_1_triple",
        "button_1_hold",
        "button_1_release",
        "button_2_single",
        "button_2_double",
        "button_2_triple",
        "button_2_hold",
        "button_2_release",
        "button_both_single",
        "button_both_double",
        "button_both_triple",
        "button_both_hold",
        "button_both_release",
    ]

    device = XDevice("lumi.switch.l3acn3")
    p = get_actions(device.human_model)
    assert p == [
        "button_1_single",
        "button_1_double",
        "button_1_triple",
        "button_1_hold",
        "button_1_release",
        "button_2_single",
        "button_2_double",
        "button_2_triple",
        "button_2_hold",
        "button_2_release",
        "button_3_single",
        "button_3_double",
        "button_3_triple",
        "button_3_hold",
        "button_3_release",
        "button_both_12_single",
        "button_both_12_double",
        "button_both_12_triple",
        "button_both_12_hold",
        "button_both_12_release",
        "button_both_13_single",
        "button_both_13_double",
        "button_both_13_triple",
        "button_both_13_hold",
        "button_both_13_release",
        "button_both_23_single",
        "button_both_23_double",
        "button_both_23_triple",
        "button_both_23_hold",
        "button_both_23_release",
    ]

    device = XDevice("lumi.remote.acn004")
    p = get_actions(device.human_model)
    assert p == [
        "button_1_single",
        "button_1_double",
        "button_1_hold",
        "button_2_single",
        "button_2_double",
        "button_2_hold",
        "button_both_single",
    ]

    device = XDevice(1983)
    p = get_actions(device.human_model)
    assert p == ["single", "double", "hold"]

    device = XDevice(1946)
    p = get_actions(device.human_model)
    assert p == ["button_1_single", "button_2_single"]


def test_buttons_6473():
    device = XDevice(6473)
    p = get_actions(device.human_model)
    assert p == [
        "button_1_single",
        "button_2_single",
        "button_both_single",
        "button_1_double",
        "button_2_double",
        "button_1_hold",
        "button_2_hold",
    ]
