from custom_components.xiaomi_gateway3.core import zigbee


def test_device_trigger():
    buttons = zigbee.get_buttons('lumi.ctrl_neutral2 XXX')
    assert buttons == ['button_1', 'button_2', 'button_both']

    buttons = zigbee.get_buttons('lumi.switch.b2lc04 XXX')
    assert buttons == ['button_1', 'button_2', 'button_both']
