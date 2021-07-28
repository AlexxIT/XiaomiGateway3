import re
from typing import Optional

# https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/devices.js#L390
# https://slsys.io/action/devicelists.html
# All lumi models:
#   https://github.com/rytilahti/python-miio/issues/699#issuecomment-643208618
# Zigbee Model: [Manufacturer, Device Name, Device Model]
# params: [lumi res name, xiaomi prop name, hass attr name, hass domain]
# old devices uses lumi_spec, new devices uses miot_spec
# for miot_spec events you can use yaml in attr name field
DEVICES = [{
    'lumi.gateway.mgl03': ["Xiaomi", "Gateway 3", "ZNDMWG03LM"],
    'lumi_spec': [
        ['8.0.2012', None, 'power_tx', None],
        ['8.0.2024', None, 'channel', None],
        ['8.0.2081', None, 'pairing_stop', None],
        ['8.0.2082', None, 'removed_did', None],
        ['8.0.2084', None, 'added_device', None],  # new devices added (info)
        ['8.0.2103', None, 'device_model', None],  # new device model
        ['8.0.2109', None, 'pairing_start', None],
        ['8.0.2110', None, 'discovered_mac', None],  # new device discovered
        ['8.0.2111', None, 'pair_command', None],  # add new device
        ['8.0.2155', None, 'cloud', None],  # {"cloud_link":0}
        [None, None, 'pair', 'remote'],
        [None, None, 'firmware lock', 'switch'],  # firmware lock
    ],
    'miot_spec': [
        # different format from bluetooth Mesh Device :(
        [3, 1, 'alarm', 'alarm_control_panel'],
        [3, 22, 'alarm_trigger', None],
    ]
}, {
    # on/off, power measurement
    'lumi.plug': ["Xiaomi", "Plug", "ZNCZ02LM"],  # tested
    'lumi.plug.mitw01': ["Xiaomi", "Plug TW", "ZNCZ03LM"],
    'lumi.plug.mmeu01': ["Xiaomi", "Plug EU", "ZNCZ04LM"],
    'lumi.plug.maus01': ["Xiaomi", "Plug US", "ZNCZ12LM"],
    'lumi.ctrl_86plug': ["Aqara", "Socket", "QBCZ11LM"],
    # 'lumi.plug.maeu01': ["Aqara", "Plug EU", "SP-EUC01"],
    'lumi_spec': [
        ['0.12.85', 'load_power', 'power', 'sensor'],
        ['0.13.85', None, 'consumption', 'sensor'],
        ['4.1.85', 'neutral_0', 'switch', 'switch'],  # or channel_0?
    ]
}, {
    'lumi.ctrl_86plug.aq1': ["Aqara", "Socket", "QBCZ11LM"],
    'lumi_spec': [
        ['0.12.85', 'load_power', 'power', 'sensor'],
        ['0.13.85', None, 'consumption', 'sensor'],
        ['4.1.85', 'channel_0', 'switch', 'switch'],  # @to4ko
    ]
}, {
    'lumi.ctrl_ln1': ["Aqara", "Single Wall Switch", "QBKG11LM"],
    'lumi.ctrl_ln1.aq1': ["Aqara", "Single Wall Switch", "QBKG11LM"],
    'lumi.switch.b1nacn02': ["Aqara", "Single Wall Switch D1", "QBKG23LM"],
    'lumi_spec': [
        ['0.12.85', 'load_power', 'power', 'sensor'],
        ['0.13.85', None, 'consumption', 'sensor'],
        ['4.1.85', 'neutral_0', 'switch', 'switch'],  # or channel_0?
        ['13.1.85', None, 'button', None],
        [None, None, 'action', 'sensor'],
    ]
}, {
    # dual channel on/off, power measurement
    'lumi.relay.c2acn01': ["Aqara", "Relay", "LLKZMK11LM"],  # tested
    'lumi.ctrl_ln2': ["Aqara", "Double Wall Switch", "QBKG12LM"],
    'lumi.ctrl_ln2.aq1': ["Aqara", "Double Wall Switch", "QBKG12LM"],
    'lumi.switch.b2nacn02': ["Aqara", "Double Wall Switch D1", "QBKG24LM"],
    'lumi_spec': [
        # ['0.11.85', 'load_voltage', 'power', 'sensor'],  # 0
        ['0.12.85', 'load_power', 'power', 'sensor'],
        ['0.13.85', None, 'consumption', 'sensor'],
        # ['0.14.85', None, '?', 'sensor'],  # 5.01, 6.13
        ['4.1.85', 'channel_0', 'channel 1', 'switch'],
        ['4.2.85', 'channel_1', 'channel 2', 'switch'],
        # [?, 'enable_motor_mode', 'interlock', None]
        ['13.1.85', None, 'button_1', None],
        ['13.2.85', None, 'button_2', None],
        ['13.5.85', None, 'button_both', None],
        [None, None, 'action', 'sensor'],
    ]
}, {
    'lumi.ctrl_neutral1': ["Aqara", "Single Wall Switch", "QBKG04LM"],
    'lumi_spec': [
        ['4.1.85', 'neutral_0', 'switch', 'switch'],  # @vturekhanov
        ['13.1.85', None, 'button', None],
        [None, None, 'action', 'sensor'],
    ]
}, {
    # on/off
    'lumi.switch.b1lacn02': ["Aqara", "Single Wall Switch D1", "QBKG21LM"],
    'lumi_spec': [
        ['4.1.85', 'channel_0', 'switch', 'switch'],  # or neutral_0?
        ['13.1.85', None, 'button', None],
        [None, None, 'action', 'sensor'],
    ]
}, {
    # dual channel on/off
    'lumi.ctrl_neutral2': ["Aqara", "Double Wall Switch", "QBKG03LM"],
    'lumi_spec': [
        ['4.1.85', 'neutral_0', 'channel 1', 'switch'],  # @to4ko
        ['4.2.85', 'neutral_1', 'channel 2', 'switch'],  # @to4ko
        ['13.1.85', None, 'button_1', None],
        ['13.2.85', None, 'button_2', None],
        ['13.5.85', None, 'button_both', None],
        [None, None, 'action', 'sensor'],
    ]
}, {
    'lumi.switch.b2lacn02': ["Aqara", "Double Wall Switch D1", "QBKG22LM"],
    'lumi_spec': [
        ['4.1.85', 'channel_0', 'channel 1', 'switch'],
        ['4.2.85', 'channel_1', 'channel 2', 'switch'],
        ['13.1.85', None, 'button_1', None],
        ['13.2.85', None, 'button_2', None],
        ['13.5.85', None, 'button_both', None],
        [None, None, 'action', 'sensor'],
    ]
}, {
    # triple channel on/off, no neutral wire
    'lumi.switch.l3acn3': ["Aqara", "Triple Wall Switch D1", "QBKG25LM"],
    'lumi_spec': [
        ['4.1.85', 'neutral_0', 'channel 1', 'switch'],  # @to4ko
        ['4.2.85', 'neutral_1', 'channel 2', 'switch'],  # @to4ko
        ['4.3.85', 'neutral_2', 'channel 3', 'switch'],  # @to4ko
        ['13.1.85', None, 'button_1', None],
        ['13.2.85', None, 'button_2', None],
        ['13.3.85', None, 'button_3', None],
        ['13.5.85', None, 'button_both_12', None],
        ['13.6.85', None, 'button_both_13', None],
        ['13.7.85', None, 'button_both_23', None],
        [None, None, 'action', 'sensor'],
    ]
}, {
    # with neutral wire, thanks @Mantoui
    'lumi.switch.n3acn3': ["Aqara", "Triple Wall Switch D1", "QBKG26LM"],
    'lumi_spec': [
        ['0.12.85', 'load_power', 'power', 'sensor'],
        ['0.13.85', None, 'consumption', 'sensor'],
        ['4.1.85', 'channel_0', 'channel 1', 'switch'],
        ['4.2.85', 'channel_1', 'channel 2', 'switch'],
        ['4.3.85', 'channel_2', 'channel 3', 'switch'],
        ['13.1.85', None, 'button_1', None],
        ['13.2.85', None, 'button_2', None],
        ['13.3.85', None, 'button_3', None],
        ['13.5.85', None, 'button_both_12', None],
        ['13.6.85', None, 'button_both_13', None],
        ['13.7.85', None, 'button_both_23', None],
        [None, None, 'action', 'sensor'],
    ]
}, {
    # cube action, no retain
    'lumi.sensor_cube': ["Aqara", "Cube", "MFKZQ01LM"],
    'lumi.sensor_cube.aqgl01': ["Aqara", "Cube", "MFKZQ01LM"],  # tested
    'lumi_spec': [
        ['0.2.85', None, 'duration', None],
        ['0.3.85', None, 'angle', None],
        ['13.1.85', None, 'action', 'sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # light with brightness and color temp
    'lumi.light.aqcn02': ["Aqara", "Bulb", "ZNLDP12LM"],
    'lumi.light.cwopcn02': ["Aqara", "Opple MX650", "XDD12LM"],
    'lumi.light.cwopcn03': ["Aqara", "Opple MX480", "XDD13LM"],
    'ikea.light.led1545g12': ["IKEA", "Bulb E27 980 lm", "LED1545G12"],
    'ikea.light.led1546g12': ["IKEA", "Bulb E27 950 lm", "LED1546G12"],
    'ikea.light.led1536g5': ["IKEA", "Bulb E14 400 lm", "LED1536G5"],
    'ikea.light.led1537r6': ["IKEA", "Bulb GU10 400 lm", "LED1537R6"],
    'lumi_spec': [
        ['4.1.85', 'power_status', 'light', 'light'],
        ['14.1.85', 'light_level', 'brightness', None],
        ['14.2.85', 'colour_temperature', 'color_temp', None],
    ]
}, {
    # light with brightness
    'ikea.light.led1623g12': ["IKEA", "Bulb E27 1000 lm", "LED1623G12"],
    'ikea.light.led1650r5': ["IKEA", "Bulb GU10 400 lm", "LED1650R5"],
    'ikea.light.led1649c5': ["IKEA", "Bulb E14", "LED1649C5"],  # tested
    'lumi_spec': [
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
    'lumi.remote.b186acn02': ["Aqara", "Single Wall Button D1", "WXKG06LM"],
    'lumi_spec': [
        ['13.1.85', None, 'button', None],
        [None, None, 'action', 'sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # multi button action, no retain
    'lumi.sensor_86sw2': ["Aqara", "Double Wall Button", "WXKG02LM"],
    'lumi.remote.b286acn01': ["Aqara", "Double Wall Button", "WXKG02LM"],
    'lumi.sensor_86sw2.es1': ["Aqara", "Double Wall Button", "WXKG02LM"],
    'lumi.remote.b286acn02': ["Aqara", "Double Wall Button D1", "WXKG07LM"],
    'lumi.remote.b286opcn01': ["Aqara", "Opple Two Button", "WXCJKG11LM"],
    'lumi.remote.b486opcn01': ["Aqara", "Opple Four Button", "WXCJKG12LM"],
    'lumi.remote.b686opcn01': ["Aqara", "Opple Six Button", "WXCJKG13LM"],
    'lumi_spec': [
        ['13.1.85', None, 'button_1', None],
        ['13.2.85', None, 'button_2', None],
        ['13.3.85', None, 'button_3', None],
        ['13.4.85', None, 'button_4', None],
        ['13.6.85', None, 'button_5', None],
        ['13.7.85', None, 'button_6', None],
        ['13.5.85', None, 'button_both', None],
        [None, None, 'action', 'sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # temperature and humidity sensor
    'lumi.sensor_ht': ["Xiaomi", "TH Sensor", "WSDCGQ01LM"],
    'lumi_spec': [
        ['0.1.85', 'temperature', 'temperature', 'sensor'],
        ['0.2.85', 'humidity', 'humidity', 'sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # temperature, humidity and pressure sensor
    'lumi.weather': ["Aqara", "TH Sensor", "WSDCGQ11LM"],
    'lumi.sensor_ht.agl02': ["Aqara", "TH Sensor", "WSDCGQ12LM"],
    'lumi_spec': [
        ['0.1.85', 'temperature', 'temperature', 'sensor'],
        ['0.2.85', 'humidity', 'humidity', 'sensor'],
        ['0.3.85', 'pressure', 'pressure', 'sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # door window sensor
    'lumi.sensor_magnet': ["Xiaomi", "Door Sensor", "MCCGQ01LM"],
    'lumi.sensor_magnet.aq2': ["Aqara", "Door Sensor", "MCCGQ11LM"],
    'lumi_spec': [
        ['3.1.85', 'status', 'contact', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # motion sensor
    'lumi.sensor_motion': ["Xiaomi", "Motion Sensor", "RTCGQ01LM"],
    'lumi_spec': [
        ['3.1.85', None, 'motion', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # motion sensor with illuminance
    'lumi.sensor_motion.aq2': ["Aqara", "Motion Sensor", "RTCGQ11LM"],
    'lumi_spec': [
        ['0.3.85', 'lux', 'illuminance_lux', None],
        ['0.4.85', 'illumination', 'illuminance', 'sensor'],
        ['3.1.85', None, 'motion', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # water leak sensor
    'lumi.sensor_wleak.aq1': ["Aqara", "Water Leak Sensor", "SJCGQ11LM"],
    'lumi_spec': [
        ['3.1.85', 'alarm', 'moisture', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # vibration sensor
    'lumi.vibration.aq1': ["Aqara", "Vibration Sensor", "DJT11LM"],
    'lumi_spec': [
        ['0.1.85', None, 'bed_activity', None],
        ['0.2.85', None, 'tilt_angle', None],
        ['0.3.85', None, 'vibrate_intensity', None],
        ['13.1.85', None, 'vibration', None],
        ['14.1.85', None, 'vibration_level', None],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
        [None, None, 'action', 'sensor']
    ]
}, {
    'lumi.sen_ill.mgl01': ["Xiaomi", "Light Sensor", "GZCGQ01LM"],
    'miot_spec': [
        ['2.1', '2.1', 'illuminance', 'sensor'],
        ['3.1', '3.1', 'battery', 'sensor'],
    ]
}, {
    'lumi.sensor_smoke': ["Honeywell", "Smoke Sensor", "JTYJ-GD-01LM/BW"],
    'lumi_spec': [
        ['0.1.85', 'density', 'smoke density', 'sensor'],
        ['13.1.85', 'alarm', 'smoke', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    'lumi.sensor_natgas': ["Honeywell", "Gas Sensor", "JTQJ-BF-01LM/BW"],
    'lumi_spec': [
        ['0.1.85', 'density', 'gas density', 'sensor'],
        ['13.1.85', 'alarm', 'gas', 'binary_sensor'],
    ]
}, {
    'lumi.curtain': ["Aqara", "Curtain", "ZNCLDJ11LM"],
    'lumi.curtain.aq2': ["Aqara", "Roller Shade", "ZNGZDJ11LM"],
    'lumi_spec': [
        ['1.1.85', 'curtain_level', 'position', None],
        ['14.2.85', None, 'motor', 'cover'],
        ['14.3.85', 'cfg_param', 'cfg_param', None],
        ['14.4.85', 'run_state', 'run_state', None],
    ]
}, {
    'lumi.curtain.hagl04': ["Aqara", "Curtain B1", "ZNCLDJ12LM"],
    'lumi_spec': [
        ['1.1.85', 'curtain_level', 'position', None],
        ['14.2.85', None, 'motor', 'cover'],
        ['14.3.85', 'cfg_param', 'cfg_param', None],
        ['14.4.85', 'run_state', 'run_state', None],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    'lumi.lock.aq1': ["Aqara", "Door Lock S1", "ZNMS11LM"],
    'lumi.lock.acn02': ["Aqara", "Door Lock S2", "ZNMS12LM"],
    'lumi.lock.acn03': ["Aqara", "Door Lock S2 Pro", "ZNMS12LM"],
    'lumi_spec': [
        ['13.1.85', None, 'key_id', 'sensor'],
        ['13.20.85', 'lock_state', 'lock', 'binary_sensor'],
        ['8.0.2001', 'battery', 'battery', 'sensor'],
    ]
}, {
    # https://github.com/AlexxIT/XiaomiGateway3/issues/101
    'lumi.airrtc.tcpecn02': ["Aqara", "Thermostat S2", "KTWKQ03ES"],
    'lumi_spec': [
        ['3.1.85', 'power_status', 'power', None],
        ['3.2.85', None, 'current_temperature', None],
        ['14.2.85', 'ac_state', 'climate', 'climate'],
        ['14.8.85', None, 'mode', None],
        ['14.9.85', None, 'target_temperature', None],
        ['14.10.85', None, 'fan_mode', None],
    ]
}, {
    'lumi.airrtc.vrfegl01': ["Xiaomi", "VRF Air Conditioning"],
    'lumi_spec': [
        ['13.1.85', None, 'channels', 'sensor']
    ]
}, {
    # no N, https://www.aqara.com/en/single_switch_T1_no-neutral.html
    'lumi.switch.l0agl1': ["Aqara", "Relay T1", "SSM-U02"],
    'miot_spec': [
        ['2.1', '2.1', 'switch', 'switch'],
    ]
}, {
    # with N, https://www.aqara.com/en/single_switch_T1_with-neutral.html
    'lumi.switch.n0agl1': ["Aqara", "Relay T1", "SSM-U01"],
    'lumi.plug.maeu01': ["Aqara", "Plug", "SP-EUC01"],
    'miot_spec': [
        ['2.1', '2.1', 'switch', 'switch'],
        ['3.1', '3.1', 'consumption', 'sensor'],
        ['3.2', '3.2', 'power', 'sensor'],
        # ['5.7', '5.7', 'voltage', 'sensor'],
    ]
}, {
    'lumi.motion.agl04': ["Aqara", "Precision Motion Sensor", "RTCGQ13LM"],
    'miot_spec': [
        [None, None, 'motion', 'binary_sensor'],
        ['3.1', '3.1', 'battery', 'sensor'],
        ['4.1', None, 'motion: 1', None],
    ]
}, {
    'lumi.airmonitor.acn01': ["Aqara", "TVOC Air Quality Monitor",
                              "VOCKQJK11LM"],
    'miot_spec': [
        ['3.1', '3.1', 'temperature', 'sensor'],
        ['3.2', '3.2', 'humidity', 'sensor'],
        ['3.3', '3.3', 'tvoc', 'sensor'],
        ['4.1', '4.1', 'tvoc_level', 'binary_sensor'],
        ['4.2', '4.2', 'battery', 'sensor'],
    ]
}, {
    'lumi.switch.b1lc04': ["Aqara", "Single Wall Switch E1", "QBKG38LM"],
    'miot_spec': [
        ['2.1', '2.1', 'switch', 'switch'],
        ['6.1', None, 'button: 1', None],
        ['6.2', None, 'button: 2', None],
        [None, None, 'action', 'sensor'],
    ]
}, {
    'lumi.switch.b2lc04': ["Aqara", "Double Wall Switch E1", "QBKG39LM"],
    'miot_spec': [
        ['2.1', '2.1', 'channel 1', 'switch'],
        ['3.1', '3.1', 'channel 2', 'switch'],
        ['7.1', None, 'button_1: 1', None],
        ['7.2', None, 'button_1: 2', None],
        ['8.1', None, 'button_2: 1', None],
        ['8.2', None, 'button_2: 2', None],
        ['9.1', None, 'button_both: 4', None],
        [None, None, 'action', 'sensor'],
    ]
}, {
    # with neutral wire
    'lumi.switch.b1nc01': ["Aqara", "Single Wall Switch E1", "QBKG40LM"],
    'miot_spec': [
        ['2.1', '2.1', 'switch', 'switch'],
        ['7.1', None, 'button: 1', None],
        ['7.2', None, 'button: 2', None],
        [None, None, 'action', 'sensor'],
    ]
}, {
    # with neutral wire
    'lumi.switch.b2nc01': ["Aqara", "Double Wall Switch E1", "QBKG41LM"],
    'miot_spec': [
        ['2.1', '2.1', 'channel 1', 'switch'],
        ['3.1', '3.1', 'channel 2', 'switch'],
        ['8.1', None, 'button_1: 1', None],
        ['8.2', None, 'button_1: 2', None],
        ['9.1', None, 'button_2: 1', None],
        ['9.2', None, 'button_2: 2', None],
        ['10.1', None, 'button_both: 4', None],
        [None, None, 'action', 'sensor'],
    ]
}, {
    # required switch firmware 0.0.0_0030
    'lumi.switch.b2naus01': ["Aqara", "Double Wall Switch US", "WS-USC04"],
    'miot_spec': [
        ['2.1', '2.1', 'channel 1', 'switch'],
        ['3.1', '3.1', 'channel 2', 'switch'],
        ['4.1', None, 'consumption', None],
        ['4.2', 'load_power', 'power', 'sensor'],
        ['7.1', None, 'button_1: 1', None],
        ['7.2', None, 'button_1: 2', None],
        ['8.1', None, 'button_2: 1', None],
        ['8.2', None, 'button_2: 2', None],
        ['9.1', None, 'button_both: 4', None],
        [None, None, 'action', 'sensor'],
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
    '8.0.2102': 'alive',
    '8.0.2157': 'network_pan_id',
    '8.0.9001': 'battery_end_of_life'
}

CLUSTERS = {
    0x0000: 'Basic',
    0x0001: 'PowerCfg',
    0x0003: 'Identify',
    0x0006: 'OnOff',
    0x0008: 'LevelCtrl',
    0x000A: 'Time',
    0x000C: 'AnalogInput',  # cube, gas sensor
    0x0012: 'Multistate',
    0x0019: 'OTA',  # illuminance sensor
    0x0101: 'DoorLock',
    0x0400: 'Illuminance',  # motion sensor
    0x0402: 'Temperature',
    0x0403: 'Pressure',
    0x0405: 'Humidity',
    0x0406: 'Occupancy',  # motion sensor
    0x0500: 'IasZone',  # gas sensor
    0x0B04: 'ElectrMeasur',
    0xFCC0: 'Xiaomi'
}

RE_ZIGBEE_MODEL_TAIL = re.compile(r'\.v\d$')


def get_device(zigbee_model: str) -> Optional[dict]:
    # the model has an extra tail when added (v1, v2, v3)
    if RE_ZIGBEE_MODEL_TAIL.search(zigbee_model):
        zigbee_model = zigbee_model[:-3]

    for device in DEVICES:
        if zigbee_model in device:
            desc = device[zigbee_model]
            return {
                # 'model': zigbee_model,
                'device_manufacturer': desc[0],
                'device_name': desc[0] + ' ' + desc[1],
                'device_model': (
                    zigbee_model + ' ' + desc[2]
                    if len(desc) > 2 else zigbee_model
                ),
                'lumi_spec': device.get('lumi_spec'),
                'miot_spec': device.get('miot_spec')
            }

    return {
        'device_name': 'Zigbee',
        'device_mode': zigbee_model,
        'lumi_spec': [],
        'miot_spec': []
    }


def fix_xiaomi_props(model, params) -> dict:
    for k, v in params.items():
        if k in ('temperature', 'humidity', 'pressure'):
            if model != 'lumi.airmonitor.acn01':
                params[k] = v / 100.0
        elif v in ('on', 'open'):
            params[k] = 1
        elif v in ('off', 'close'):
            params[k] = 0
        elif k == 'battery' and v and v > 1000:
            params[k] = round((min(v, 3200) - 2500) / 7)
        elif k == 'run_state':
            # https://github.com/AlexxIT/XiaomiGateway3/issues/139
            if v == 'offing':
                params[k] = 0
            elif v == 'oning':
                params[k] = 1
            else:
                params[k] = 2

    return params


def get_buttons(model: str):
    model, _ = model.split(' ', 1)
    for device in DEVICES:
        if model in device:
            return [
                param[2] for param in device['lumi_spec']
                if param[2].startswith('button')
            ]
    return None
