from custom_components.xiaomi_gateway3.core import utils
from custom_components.xiaomi_gateway3.core.gateway3 import Gateway3


def test_lumi_property():
    device = {'did': 'lumi.xxx', 'model': 'lumi.sensor_motion.aq2'}
    device.update(utils.get_device(device['model']))

    def handler(payload: dict):
        assert payload == {'motion': 1}

    gw = Gateway3('', '', {})
    gw.devices = {'lumi.xxx': device}
    gw.add_update('lumi.xxx', handler)

    payload = {
        'cmd': 'report', 'did': 'lumi.xxx',
        'params': [{'res_name': '3.1.85', 'value': 1}]
    }
    gw.process_message(payload)


def test_wrong_temperature():
    device = {'did': 'lumi.xxx', 'model': 'lumi.sensor_motion.aq2'}
    device.update(utils.get_device(device['model']))

    def handler(payload: dict):
        assert payload == {'0.1.85': 12300}

    gw = Gateway3('', '', {})
    gw.devices = {'lumi.xxx': device}
    gw.add_update('lumi.xxx', handler)

    payload = {
        'cmd': 'report', 'did': 'lumi.xxx',
        'params': [{'res_name': '0.1.85', 'value': 12300}]
    }
    gw.process_message(payload)


def test_mi_spec_property():
    device = {'did': 'lumi.xxx', 'model': 'lumi.sen_ill.mgl01'}
    device.update(utils.get_device(device['model']))

    def handler(payload: dict):
        assert payload == {'battery': 86}

    gw = Gateway3('', '', {})
    gw.devices = {'lumi.xxx': device}
    gw.add_update('lumi.xxx', handler)

    payload = {
        'cmd': 'report', 'did': 'lumi.xxx',
        'mi_spec': [{'siid': 3, 'piid': 1, 'value': 3100}]
    }
    gw.process_message(payload)


def test_mi_spec_event():
    device = {'did': 'lumi.xxx', 'model': 'lumi.motion.agl04'}
    device.update(utils.get_device(device['model']))

    def handler(payload: dict):
        assert payload == {'motion': 1}

    gw = Gateway3('', '', {})
    gw.devices = {'lumi.xxx': device}
    gw.add_update('lumi.xxx', handler)

    payload = {
        'cmd': 'report', 'did': 'lumi.xxx',
        'mi_spec': [{'siid': 4, 'eiid': 1, 'arguments': []}]
    }
    gw.process_message(payload)
