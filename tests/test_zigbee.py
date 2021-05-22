from custom_components.xiaomi_gateway3.core import zigbee
from custom_components.xiaomi_gateway3.core.gateway3 import Gateway3


def _generate_gateway(model: str):
    device = {'did': 'lumi.xxx', 'model': model, 'entities': {}}
    device.update(zigbee.get_device(model))
    gw = Gateway3('', '', {})
    gw.devices = {'lumi.xxx': device}
    return gw


def test_lumi_property():
    gw = _generate_gateway('lumi.sensor_motion.aq2')
    payload = gw.process_message({
        'cmd': 'report', 'did': 'lumi.xxx',
        'params': [{'res_name': '3.1.85', 'value': 1}]
    })
    assert payload == {'motion': 1}


def test_wrong_temperature():
    gw = _generate_gateway('lumi.sensor_motion.aq2')
    payload = gw.process_message({
        'cmd': 'report', 'did': 'lumi.xxx',
        'params': [{'res_name': '0.1.85', 'value': 12300}]
    })
    assert payload == {'0.1.85': 12300}


def test_mi_spec_property():
    gw = _generate_gateway('lumi.sen_ill.mgl01')
    payload = gw.process_message({
        'cmd': 'report', 'did': 'lumi.xxx',
        'mi_spec': [{'siid': 3, 'piid': 1, 'value': 3100}]
    })
    assert payload == {'battery': 83}


def test_mi_spec_event():
    gw = _generate_gateway('lumi.motion.agl04')
    payload = gw.process_message({
        'cmd': 'report', 'did': 'lumi.xxx',
        'mi_spec': [{'siid': 4, 'eiid': 1, 'arguments': []}]
    })
    assert payload == {'motion': 1}


def test_e1_click_event():
    gw = _generate_gateway('lumi.switch.b2lc04')
    payload = gw.process_message({
        'cmd': 'report', 'did': 'lumi.xxx',
        'mi_spec': [{'siid': 8, 'eiid': 2, 'arguments': []}]
    })
    assert payload == {'button_2': 2}

    payload = gw.process_message({
        'cmd': 'report', 'did': 'lumi.xxx',
        'mi_spec': [{'siid': 9, 'eiid': 1, 'arguments': []}]
    })
    assert payload == {'button_both': 4}


def test_online():
    gw = _generate_gateway('lumi.sensor_motion.aq2')
    gw.process_message({
        'cmd': 'report', 'did': 'lumi.xxx',
        'params': [{'res_name': '3.1.85', 'value': 1}]
    })
    assert gw.devices['lumi.xxx']['online']


def test_offline():
    gw = _generate_gateway('lumi.sensor_motion.aq2')
    gw.process_message({
        'cmd': 'report', 'did': 'lumi.xxx',
        'params': [{'res_name': '8.0.2102', 'value': {
            'status': 'offline', 'time': 10800
        }}]
    })
    assert gw.devices['lumi.xxx']['online'] is False


def test_airmonitor_acn01():
    gw = _generate_gateway('lumi.airmonitor.acn01')
    payload = gw.process_message({
        'cmd': 'report', 'did': 'lumi.xxx',
        'mi_spec': [{'siid': 3, 'piid': 1, 'value': 36.6}]
    })
    assert payload == {'temperature': 36.6}


def test_voltage():
    gw = _generate_gateway('lumi.sensor_magnet')
    payload = gw.process_message({
        'cmd': 'heartbeat', 'params': [{
            'did': 'lumi.xxx', 'res_list': [
                {'res_name': '8.0.2008', 'value': 3045},
                {'res_name': '8.0.2001', 'value': 74},
            ]
        }]
    })
    assert payload == {'battery': 74}
