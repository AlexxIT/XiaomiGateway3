import logging
from logging import FileHandler, Formatter
from typing import Optional

# https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/devices.js#L390
# https://slsys.io/action/devicelists.html
# Zigbee Model: [Manufacturer, Device Name, Device Model]
# params: [lumi res name, xiaomi prop name, hass attr name, hass domain]
DEVICES = [{
    'lumi.gateway.mgl03': ["Xiaomi", "Gateway 3", "ZNDMWG03LM"],
    'params': [
        ['8.0.2081', None, 'pairing_stop', None],
        ['8.0.2082', None, 'removed_did', None],
        ['8.0.2084', None, 'added_device', None],  # new devices added (info)
        ['8.0.2103', None, 'device_model', None],  # new device model
        ['8.0.2109', None, 'pairing_start', None],
        ['8.0.2110', None, 'discovered_mac', None],  # new device discovered
        ['8.0.2111', None, 'pair_command', None],  # add new device
        ['8.0.2155', None, 'cloud', None],  # {"cloud_link":0}
        [None, None, 'pair', 'remote'],
    ]
}, {
    # on/off, power measurement
    'lumi.plug': ["Xiaomi", "Plug", "ZNCZ02LM"],  # tested
    'lumi.plug.mitw01': ["Xiaomi", "Plug TW", "ZNCZ03LM"],
    'lumi.plug.mmeu01': ["Xiaomi", "Plug EU", "ZNCZ04LM"],
    'lumi.plug.maus01': ["Xiaomi", "Plug US", "ZNCZ12LM"],
    'lumi.ctrl_86plug': ["Aqara", "Socket", "QBCZ11LM"],
    'lumi.ctrl_86plug.aq1': ["Aqara", "Socket", "QBCZ11LM"],
    'lumi.ctrl_ln1': ["Aqara", "Wall Single Switch", "QBKG11LM"],
    'lumi.ctrl_ln1.aq1': ["Aqara", "Wall Single Switch", "QBKG11LM"],
    'lumi.switch.b1nacn02': ["Aqara", "D1 Wall Single Switch", "QBKG23LM"],
    'params': [
        ['0.12.85', 'load_power', 'power', 'sensor'],
        ['0.13.85', None, 'consumption', 'sensor'],
        ['4.1.85', 'neutral_0', 'switch', 'switch'],  # or channel_0?
    ]
}, {
    # dual channel on/off, power measurement
    'lumi.relay.c2acn01': ["Aqara", "Relay", "LLKZMK11LM"],  # tested
    'lumi.ctrl_ln2': ["Aqara", "Wall Double Switch", "QBKG12LM"],
    'lumi.ctrl_ln2.aq1': ["Aqara", "Wall Double Switch", "QBKG12LM"],
    'lumi.switch.b2nacn02': ["Aqara", "D1 Wall Double Switch", "QBKG24LM"],
    'params': [
        # ['0.11.85', 'load_voltage', 'power', 'sensor'],  # 0
        ['0.12.85', 'load_power', 'power', 'sensor'],
        ['0.13.85', None, 'consumption', 'sensor'],
        # ['0.14.85', None, '?', 'sensor'],  # 5.01, 6.13
        ['4.1.85', 'channel_0', 'channel 1', 'switch'],
        ['4.2.85', 'channel_1', 'channel 2', 'switch'],
        # [?, 'enable_motor_mode', 'interlock', None]
    ]
}, {
    # on/off
    'lumi.ctrl_neutral1': ["Aqara", "Wall Single Switch", "QBKG04LM"],
    'lumi.switch.b1lacn02': ["Aqara", "D1 Wall Single Switch", "QBKG21LM"],
    'params': [
        ['4.1.85', 'channel_0', 'switch', 'switch'],  # or neutral_0?
    ]
}, {
    # dual channel on/off
    'lumi.ctrl_neutral2': ["Aqara", "Wall Double Switch", "QBKG03LM"],
    'lumi.switch.b2lacn02': ["Aqara", "D1 Wall Single Switch", "QBKG22LM"],
    'params': [
        ['4.1.85', 'channel_0', 'channel 1', 'switch'],
        ['4.2.85', 'channel_1', 'channel 2', 'switch'],
    ]
}, {
    # triple channel on/off
    'lumi.switch.l3acn3': ["Aqara", "D1 Wall Triple Switch", "QBKG25LM"],
    'params': [
        ['4.1.85', 'channel_0', 'channel 1', 'switch'],
        ['4.2.85', 'channel_1', 'channel 2', 'switch'],
        ['4.3.85', 'channel_2', 'channel 3', 'switch'],
    ]
}, {
    # cube action, no retain
    'lumi.sensor_cube': ["Aqara", "Cube", "MFKZQ01LM"],
    'lumi.sensor_cube.aqgl01': ["Aqara", "Cube", "MFKZQ01LM"],  # tested
    'params': [
        # ['0.2.85', '?', '?', '?'],
        ['0.3.85', None, 'angle', None],
        ['13.1.85', None, 'action', 'sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # light with brightness
    'lumi.light.aqcn02': ["Aqara", "Bulb", "ZNLDP12LM"],
    'lumi.light.cwopcn02': ["Aqara", "Opple MX650", "XDD12LM"],
    'lumi.light.cwopcn03': ["Aqara", "Opple MX480", "XDD13LM"],
    'ikea.light.led1649c5': ["IKEA", "Bulb E14"],  # tested
    'params': [
        ['4.1.85', 'power_status', 'light', 'light'],
        ['14.1.85', 'light_level', 'brightness', None],
    ]
}, {
    # button action, no retain
    'lumi.sensor_switch': ["Xiaomi", "Button", "WXKG01LM"],
    'lumi.sensor_switch.aq2': ["Aqara", "Button", "WXKG11LM"],
    'lumi.remote.b1acn01': ["Aqara", "Button", "WXKG11LM"],
    'lumi.sensor_switch.aq3': ["Aqara", "Shake Button", "WXKG12LM"],
    'lumi.sensor_86sw1': ["Aqara", "Single Wall Button", "WXKG03LM"],
    'lumi.remote.b186acn01': ["Aqara", "Single Wall Button", "WXKG03LM"],
    'lumi.remote.b186acn02': ["Aqara", "D1 Single Wall Button", "WXKG06LM"],
    'params': [
        ['13.1.85', None, 'button', None],
        [None, None, 'action', 'sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # multi button action, no retain
    'lumi.sensor_86sw2': ["Aqara", "Double Wall Button", "WXKG02LM"],
    'lumi.remote.b286acn01': ["Aqara", "Double Wall Button", "WXKG02LM"],
    'lumi.sensor_86sw2.es1': ["Aqara", "Double Wall Button", "WXKG02LM"],
    'lumi.remote.b286acn02': ["Aqara", "D1 Double Wall Button", "WXKG07LM"],
    'lumi.remote.b286opcn01': ["Aqara", "Opple Two Button", "WXCJKG11LM"],
    'lumi.remote.b486opcn01': ["Aqara", "Opple Four Button", "WXCJKG12LM"],
    'lumi.remote.b686opcn01': ["Aqara", "Opple Six Button", "WXCJKG13LM"],
    'params': [
        ['13.1.85', None, 'button_1', None],
        ['13.2.85', None, 'button_2', None],
        ['13.3.85', None, 'button_3', None],
        ['13.4.85', None, 'button_4', None],
        ['13.5.85', None, 'button_both', None],
        ['13.6.85', None, 'button_5', None],
        ['13.7.85', None, 'button_6', None],
        [None, None, 'action', 'sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # temperature and humidity sensor
    'lumi.sensor_ht': ["Xiaomi", "TH Sensor", "WSDCGQ01LM"],
    'params': [
        ['0.1.85', 'temperature', 'temperature', 'sensor'],
        ['0.2.85', 'humidity', 'humidity', 'sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # temperature, humidity and pressure sensor
    'lumi.weather': ["Aqara", "TH Sensor", "WSDCGQ11LM"],
    'lumi.sensor_ht.agl02': ["Aqara", "TH Sensor", "WSDCGQ12LM"],
    'params': [
        ['0.1.85', 'temperature', 'temperature', 'sensor'],
        ['0.2.85', 'humidity', 'humidity', 'sensor'],
        ['0.3.85', 'pressure', 'pressure', 'sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # door window sensor
    'lumi.sensor_magnet': ["Xiaomi", "Door Sensor", "MCCGQ01LM"],
    'lumi.sensor_magnet.aq2': ["Aqara", "Door Sensor", "MCCGQ11LM"],
    'params': [
        ['3.1.85', 'status', 'contact', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # motion sensor
    'lumi.sensor_motion': ["Xiaomi", "Motion Sensor", "RTCGQ01LM"],
    'params': [
        ['3.1.85', None, 'motion', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # motion sensor with illuminance
    'lumi.sensor_motion.aq2': ["Aqara", "Motion Sensor", "RTCGQ11LM"],
    'params': [
        ['0.4.85', 'illumination', 'illuminance', 'sensor'],
        ['3.1.85', None, 'motion', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # water leak sensor
    'lumi.sensor_wleak.aq1': ["Aqara", "Water Leak Sensor", "SJCGQ11LM"],
    'params': [
        ['3.1.85', 'alarm', 'moisture', 'binary_sensor'],
    ]
}, {
    # vibration sensor
    'lumi.vibration.aq1': ["Aqara", "Vibration Sensor", "DJT11LM"],
    'params': [
        ['0.1.85', None, 'bed_activity', None],
        ['0.2.85', None, 'final_tilt_angle', None],
        ['0.3.85', None, 'vibrate_intensity', None],
        ['13.1.85', None, 'vibration', None],
        ['14.1.85', None, 'vibration_level', None],
        [None, None, 'action', 'sensor']
    ]
}, {  # OTHER MANUFACTURERS
    'TRADFRI bulb E27 W opal 1000lm': ["IKEA", "Bulb E27"],
    'LWB010': ["Philips", "Hue Bulb E27"],
    'FNB56-ZSC01LX1.2': ["Ali", "Dimmer"],
    'params': [
        [None, None, 'light', 'light'],
    ]
}, {
    'MS01': ["Sonoff", "Motion Sensor"],
    'params': [
        [None, None, 'motion', 'binary_sensor'],
    ]
}]

GLOBAL_PROP = {
    '8.0.2001': 'battery',
    '8.0.2002': 'reset_cnt',
    '8.0.2003': 'send_all_cnt',
    '8.0.2004': 'send_fail_cnt',
    '8.0.2005': 'send_retry_cnt',
    '8.0.2006': 'chip_temperature',
    '8.0.2007': 'lqi',
    '8.0.2008': 'voltage',
    '8.0.2009': 'pv_state',
    '8.0.2010': 'cur_state',
    '8.0.2011': 'pre_state',
    '8.0.2012': 'power_tx',
    '8.0.2013': 'CCA',
    '8.0.2014': 'protect',
    '8.0.2015': 'power',
    '8.0.2022': 'fw_ver',
    '8.0.2023': 'hw_ver',
    '8.0.2030': 'poweroff_memory',
    '8.0.2031': 'charge_protect',
    '8.0.2032': 'en_night_tip_light',
    '8.0.2034': 'load_s0',  # ctrl_dualchn
    '8.0.2035': 'load_s1',  # ctrl_dualchn
    '8.0.2036': 'parent',
    '8.0.2041': 'model',
    '8.0.2042': 'max_power',
    '8.0.2044': 'plug_detection',
    '8.0.2101': 'nl_invert',  # ctrl_86plug
    '8.0.9001': 'battery_end_of_life'
}


def get_device(zigbee_model: str) -> Optional[dict]:
    # the model has an extra tail when added
    if zigbee_model.endswith(('.v1', '.v2')):
        zigbee_model = zigbee_model[:-3]

    for device in DEVICES:
        if zigbee_model in device:
            desc = device[zigbee_model]
            return {
                # 'model': zigbee_model,
                'device_manufacturer': desc[0],
                'device_name': desc[0] + ' ' + desc[1],
                'device_model': zigbee_model + ' ' + desc[2]
                if len(desc) > 2 else zigbee_model,
                'params': device['params']
            }

    return None


def get_logger(filename: str):
    fmt = Formatter('%(asctime)s %(message)s')

    hdlt = FileHandler(filename)
    hdlt.setFormatter(fmt)

    log = logging.getLogger('mqtt')
    log.propagate = False
    log.setLevel(logging.DEBUG)
    log.addHandler(hdlt)

    return log
