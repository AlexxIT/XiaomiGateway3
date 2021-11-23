"""
Each device has a specification:

    {
        "<model>": ["<brand>", "<name>", "<market model>"],
        "required": [<default converters>],
        "optional": [<optional converters>],
        "config": [<optional configs>],
        "support": <from 1 to 5>
    }

- model - `lumi.xxx` for Zigbee devices, number (pdid) for BLE and Mesh devices
- required - all converters will be init with device by default
- optional - converters will be init if user select them in settings
- config - optional actions on first join (useful for 3rd party zigbee)
- support - optional score of support from 5 to 1

Each converter has:

    Converter(<attribute name>, <hass domain>, <mi name>)

- attribute - required, entity or attribute name in Hass
- domain - optional, hass entity type (`sensor`, `switch`, `binary_sensor`, etc)
- mi - optional, item name in Lumi spec (`8.0.2012`) or MIoT spec (`2.p.1`)

Old Zigbee devices uses Lumi format, new Zigbee 3 and Mesh devices uses MIoT
format. MIoT can be `siid.property.piid` or `siid.event.piid`.

Converter may have different types:

- Converter - default, don't change/convert value
- BoolConv - converts int to bool on decode and bool to int on encode
- ConstConv - set constant value on any input
- MapConv - translate value using mapping: `{0: "disarmed", 1: "armed_home"}`
- MathConv - support multiply, round value and min/max borders
- BrightnessConv - converts `0..<max>` to `0..255`, support set `max` value
- and many others...

For MIoT bool properties you should use `Converter`. For MIoT uint8 properties
you should use `BoolConv`.

By default, the entity is updated only if the decoded payload has its attribute.
But one entity can process multiple attributes, example bulb: `light`,
`brightness`, `color_temp`. In this case you should set `parent` attribute name:

    BoolConv("light", "light", "4.1.85", "power_status")
    BrightnessConv("brightness", mi="14.1.85", parent="light")
    Converter("color_temp", mi="14.2.85", parent="light")

Another case: one converter may generate multiple attributes, so you should
set `childs` for it. By default `sensor` and `binary_sensor` with childs will
adds its values to its attributes.

If converter marked as lazy - it will work, but entity will setup only with
first data from device. Useful if we don't know exact spec of device. Example,
battery not exist on some firmwares of some devices.

The name of the attribute defines the device class, icon and unit of measure.
Recommended attributes names:

- motion - the sensor can only send motion detection (timeout in Hass)
- occupancy - the sensor can send motion start and motion stop
- plug - for sockets with male connector
- outlet - for sockets with only female connector (wall installation)
- switch - for relays and switches with buttons (wall installation, remotes)
- led - control device led light
- smart - change mode from wired to wireless (decoupled)
- power_on_state - default state when electricity is supplied
- contact - for contact sensor
- moisture - for water leak sensor

Support levels:
- 5 - The device can do everything it can do
- 4 - The device works well, missing some settings
- 3 - The device works, but it missing some functionality
- 2 - The device does not work well, it is not recommended to use
- 1 - The device does not work at all

Nice project with MIoT spec description: https://home.miot-spec.com/
"""
from .base import *
from .const import *
from .mibeacon import *
from .stats import *
from .zigbee import *

################################################################################
# Gateways
################################################################################

DEVICES = [{
    "lumi.gateway.mgl03": ["Xiaomi", "Gateway 3", "ZNDMWG03LM"],
    "support": 5,
    "required": [
        # write pair=60 => report discovered_mac => report 8.0.2166? =>
        # write pair_command => report added_device => write pair=0
        MapConv("pair", mi="8.0.2109", map={60: True, 0: False}, parent="data"),
        MapConv("alarm", "alarm_control_panel", mi="3.p.1", map=GATE_ALARM),
        BoolConv("alarm_trigger", mi="3.p.22", parent="alarm"),

        Converter("discovered_mac", mi="8.0.2110", parent="data"),
        Converter("pair_command", mi="8.0.2111", parent="data"),
        Converter("added_device", mi="8.0.2084", parent="data"),
        Converter("remove_did", mi="8.0.2082", parent="data"),

        # also updated from child devices OTAConv
        Converter("ota_progress", parent="data"),

        # support change with remote.send_command
        Converter("power_tx", mi="8.0.2012"),
        Converter("channel", mi="8.0.2024"),

        MapConv("command", "select", map=GW3_COMMANDS),
        Converter("data", "select"),

        GatewayStats,

        # Converter("device_model", mi="8.0.2103"),  # very rare
        # ConstConv("pair", mi="8.0.2081", value=False),  # legacy pairing_stop
    ],
    "optional": [
        CloudLinkConv("cloud_link", "binary_sensor"),
        BoolConv("led", "switch", mi="6.p.6"),
    ]
}, {
    "lumi.gateway.aqcn02": ["Aqara", "Hub E1 (CN)", "ZHWG16LM"],
    "support": 3,
    "required": [
        MapConv("pair", mi="8.0.2109", map={60: True, 0: False}, parent="data"),

        Converter("discovered_mac", mi="8.0.2110", parent="data"),
        Converter("pair_command", mi="8.0.2111", parent="data"),
        Converter("added_device", mi="8.0.2084", parent="data"),
        Converter("remove_did", mi="8.0.2082", parent="data"),

        # also updated from child devices OTAConv
        Converter("ota_progress", parent="data"),

        # support change with remote.send_command
        Converter("power_tx", mi="8.0.2012"),
        Converter("channel", mi="8.0.2024"),

        MapConv("command", "select", map=GATE_COMMANDS),
        Converter("data", "select"),

        GatewayStats
    ],
    "optional": [],
}, {
    "lumi.gateway.aqcn03": ["Aqara", "Hub E1 (EU)", "HE1-G01"],
    "support": 1,
}]

################################################################################
# Zigbee
################################################################################

DEVICES += [{
    # don"t work: protect 8.0.2014, power 8.0.2015, plug_detection 8.0.2044
    "lumi.plug": ["Xiaomi", "Plug", "ZNCZ02LM"],  # tested
    "support": 5,
    "required": [PlugN0, Power],
    "optional": [
        ZigbeeStats, Energy,
        Converter("chip_temperature", "sensor", mi="8.0.2006"),
        BoolConv("poweroff_memory", "switch", mi="8.0.2030"),
        BoolConv("charge_protect", "switch", mi="8.0.2031"),
        BoolConv("led", "switch", mi="8.0.2032"),
        Converter("max_power", "sensor", mi="8.0.2042"),
    ],
}, {
    "lumi.plug.mitw01": ["Xiaomi", "Plug TW", "ZNCZ03LM"],
    "lumi.plug.maus01": ["Xiaomi", "Plug US", "ZNCZ12LM"],
    "required": [PlugN0, Power],
    "optional": [ZigbeeStats, Energy]
}, {
    "lumi.plug.mmeu01": ["Xiaomi", "Plug EU", "ZNCZ04LM"],
    "required": [PlugN0, Power, Voltage],
    "optional": [ZigbeeStats, Energy],
}, {
    "lumi.ctrl_86plug.aq1": ["Aqara", "Wall Outlet", "QBCZ11LM"],
    "lumi.ctrl_86plug": ["Aqara", "Wall Outlet", "QBCZ11LM"],
    "required": [
        BoolConv("outlet", "switch", mi="4.1.85"),
        Power,
    ],
    "optional": [ZigbeeStats, Energy],
}, {
    "lumi.ctrl_ln1.aq1": ["Aqara", "Single Wall Switch", "QBKG11LM"],
    "lumi.ctrl_ln1": ["Aqara", "Single Wall Switch", "QBKG11LM"],
    "lumi.switch.b1nacn02": ["Aqara", "Single Wall Switch D1", "QBKG23LM"],
    "required": [
        BoolConv("switch", "switch", mi="4.1.85"),
        Power, Energy, Action, Button,
    ],
    "optional": [ZigbeeStats],
}, {
    "lumi.ctrl_neutral1": ["Aqara", "Single Wall Switch", "QBKG04LM"],
    "lumi.switch.b1lacn02": ["Aqara", "Single Wall Switch D1", "QBKG21LM"],
    "required": [
        BoolConv("switch", "switch", mi="4.1.85"),
        Action, Button,
    ],
    "optional": [ZigbeeStats],
}, {
    # dual channel on/off, power measurement
    "lumi.ctrl_ln2.aq1": ["Aqara", "Double Wall Switch", "QBKG12LM"],
    "lumi.ctrl_ln2": ["Aqara", "Double Wall Switch", "QBKG12LM"],
    "lumi.switch.b2nacn02": ["Aqara", "Double Wall Switch D1", "QBKG24LM"],
    "required": [
        ChannelC1, ChannelC2, Power,
        Action, Button1, Button2, ButtonBoth,

    ],
    "optional": [ZigbeeStats, Energy],
}, {
    "lumi.relay.c2acn01": ["Aqara", "Relay", "LLKZMK11LM"],  # tested
    "required": [
        ChannelC1, ChannelC2, Current, Power, Voltage,
        Action, Button1, Button2, ButtonBoth,
    ],
    "optional": [
        ZigbeeStats, Energy,
        Converter("interlock", "switch", mi="4.9.85"),
    ]
}, {
    "lumi.ctrl_neutral2": ["Aqara", "Double Wall Switch", "QBKG03LM"],
    "required": [ChannelN1, ChannelN2, Action, Button1, Button2, ButtonBoth],
    "optional": [ZigbeeStats],
}, {
    "lumi.switch.b2lacn02": ["Aqara", "Double Wall Switch D1", "QBKG22LM"],
    "required": [ChannelC1, ChannelC2, Action, Button1, Button2, ButtonBoth],
    "optional": [ZigbeeStats],
}, {
    # triple channel on/off, no neutral wire
    "lumi.switch.l3acn3": ["Aqara", "Triple Wall Switch D1", "QBKG25LM"],
    "required": [
        ChannelN1, ChannelN2, ChannelN3,
        Action, Button1, Button2, Button3, Button12, Button13, Button23,
    ],
    "optional": [ZigbeeStats],
}, {
    # with neutral wire, thanks @Mantoui
    "lumi.switch.n3acn3": ["Aqara", "Triple Wall Switch D1", "QBKG26LM"],
    "required": [
        ChannelC1, ChannelC2, ChannelC3, Power, Voltage,
        Action, Button1, Button2, Button3, Button12, Button13, Button23,
    ],
    "optional": [ZigbeeStats, Energy],
}, {
    # we using lumi+zigbee covnerters for support heartbeats and transition
    # light with brightness and color temp
    "lumi.light.cwopcn02": ["Aqara", "Opple MX650", "XDD12LM"],
    "lumi.light.cwopcn03": ["Aqara", "Opple MX480", "XDD13LM"],
    "ikea.light.led1545g12": ["IKEA", "Bulb E27 980 lm", "LED1545G12"],
    "ikea.light.led1546g12": ["IKEA", "Bulb E27 950 lm", "LED1546G12"],
    "ikea.light.led1536g5": ["IKEA", "Bulb E14 400 lm", "LED1536G5"],
    "ikea.light.led1537r6": ["IKEA", "Bulb GU10 400 lm", "LED1537R6"],
    "required": [
        BoolConv("light", "light", mi="4.1.85"),
        ZXiaomiBrightnessConv("brightness", mi="14.1.85", parent="light"),
        ZXiaomiColorTempConv("color_temp", mi="14.2.85", parent="light")
    ],
    "optional": [ZigbeeStats],
}, {
    "lumi.light.aqcn02": ["Aqara", "Bulb", "ZNLDP12LM"],
    "required": [
        BoolConv("light", "light", mi="4.1.85"),
        ZXiaomiBrightnessConv("brightness", mi="14.1.85", parent="light"),
        ZXiaomiColorTempConv("color_temp", mi="14.2.85", parent="light")
    ],
    "optional": [
        ZigbeeStats,
        MapConv("power_on_state", "select", mi="8.0.2030", map={
            0: "on", 1: "previous"
        })
    ],
}, {
    # light with brightness
    "ikea.light.led1623g12": ["IKEA", "Bulb E27 1000 lm", "LED1623G12"],
    "ikea.light.led1650r5": ["IKEA", "Bulb GU10 400 lm", "LED1650R5"],
    "ikea.light.led1649c5": ["IKEA", "Bulb E14", "LED1649C5"],  # tested
    "required": [
        BoolConv("light", "light", mi="4.1.85"),
        ZXiaomiBrightnessConv("brightness", mi="14.1.85", parent="light"),
    ],
    "optional": [ZigbeeStats],
}, {
    # button action, no retain
    "lumi.sensor_switch": ["Xiaomi", "Button", "WXKG01LM"],
    "lumi.remote.b1acn01": ["Aqara", "Button", "WXKG11LM"],
    "lumi.sensor_switch.aq2": ["Aqara", "Button", "WXKG11LM"],
    "lumi.sensor_switch.aq3": ["Aqara", "Shake Button", "WXKG12LM"],
    "lumi.remote.b186acn01": ["Aqara", "Single Wall Button", "WXKG03LM"],
    "lumi.remote.b186acn02": ["Aqara", "Single Wall Button D1", "WXKG06LM"],
    "lumi.sensor_86sw1": ["Aqara", "Single Wall Button", "WXKG03LM"],
    "required": [Action, Button, Battery],
    "optional": [ZigbeeStats, BatteryPer],
}, {
    # multi button action, no retain
    "lumi.sensor_86sw2.es1": ["Aqara", "Double Wall Button", "WXKG02LM"],
    "lumi.sensor_86sw2": ["Aqara", "Double Wall Button", "WXKG02LM"],
    "lumi.remote.b286acn01": ["Aqara", "Double Wall Button", "WXKG02LM"],
    "lumi.remote.b286acn02": ["Aqara", "Double Wall Button D1", "WXKG07LM"],
    "lumi.remote.b286opcn01": ["Aqara", "Opple Two Button", "WXCJKG11LM"],
    "lumi.remote.b486opcn01": ["Aqara", "Opple Four Button", "WXCJKG12LM"],
    "lumi.remote.b686opcn01": ["Aqara", "Opple Six Button", "WXCJKG13LM"],
    "required": [
        Action, Button1, Button2, Button3, Button4, Button5, Button6,
        ButtonBoth, Battery
    ],
    "optional": [ZigbeeStats, BatteryPer],
}, {
    # temperature and humidity sensor
    "lumi.sensor_ht": ["Xiaomi", "TH Sensor", "WSDCGQ01LM"],
    "required": [Temperature, Humidity, Battery],
    "optional": [ZigbeeStats, BatteryPer],
}, {
    # temperature, humidity and pressure sensor
    "lumi.weather": ["Aqara", "TH Sensor", "WSDCGQ11LM"],
    "lumi.sensor_ht.agl02": ["Aqara", "TH Sensor", "WSDCGQ12LM"],
    "required": [
        Temperature, Humidity, Battery,
        MathConv("pressure", "sensor", mi="0.3.85", multiply=0.01),
    ],
    "optional": [ZigbeeStats, BatteryPer],
}, {
    # door window sensor
    "lumi.sensor_magnet": ["Xiaomi", "Door/Window Sensor", "MCCGQ01LM"],
    "lumi.sensor_magnet.aq2": ["Aqara", "Door/Window Sensor", "MCCGQ11LM"],
    "required": [
        # hass: On means open, Off means closed
        BoolConv("contact", "binary_sensor", mi="3.1.85"),
        Battery,
    ],
    "optional": [ZigbeeStats, BatteryPer],
}, {
    # motion sensor
    "lumi.sensor_motion": ["Xiaomi", "Motion Sensor", "RTCGQ01LM"],
    "required": [
        BoolConv("motion", "binary_sensor", mi="3.1.85"),
        Battery,
    ],
    "optional": [ZigbeeStats, BatteryPer],
}, {
    # motion sensor with illuminance
    "lumi.sensor_motion.aq2": ["Aqara", "Motion Sensor", "RTCGQ11LM"],
    "required": [
        BoolConv("motion", "binary_sensor", mi="3.1.85"),
        # Converter("illuminance_lux", None, "0.3.85", "lux"),
        Converter("illuminance", "sensor", mi="0.4.85"),
        Battery,
    ],
    "optional": [ZigbeeStats, BatteryPer],
}, {
    # water leak sensor
    "lumi.sensor_wleak.aq1": ["Aqara", "Water Leak Sensor", "SJCGQ11LM"],
    "required": [
        BoolConv("moisture", "binary_sensor", mi="3.1.85"),
        Battery,
    ],
    "optional": [ZigbeeStats, BatteryPer],
}, {
    # vibration sensor
    "lumi.vibration.aq1": ["Aqara", "Vibration Sensor", "DJT11LM"],
    "support": 2,  # TODO: need some tests
    "required": [
        Action, Battery,
        Converter("bed_activity", mi="0.1.85"),
        TiltAngleConv("tilt_angle", mi="0.2.85"),
        Converter("vibrate_intensity", mi="0.3.85"),
        VibrationConv("vibration", mi="13.1.85"),
        Converter("vibration_level", mi="14.1.85"),
    ],
    "optional": [ZigbeeStats],
}, {
    # cube action, no retain
    "lumi.sensor_cube.aqgl01": ["Aqara", "Cube", "MFKZQ01LM"],  # tested
    "lumi.sensor_cube": ["Aqara", "Cube", "MFKZQ01LM"],
    "support": 3,  # TODO: need some tests
    "required": [
        ZAqaraCubeMain("action", "sensor"),
        # ZAqaraCubeRotate("angle"),
        # Converter("action", mi="13.1.85"),
        Converter("duration", mi="0.2.85", parent="action"),
        Converter("angle", mi="0.3.85", parent="action"),
        Battery,
    ],
    "optional": [ZigbeeStats, BatteryPer],
}, {
    "lumi.sensor_smoke": ["Honeywell", "Smoke Sensor", "JTYJ-GD-01LM/BW"],
    "required": [
        Converter("smoke_density", "sensor", mi="0.1.85"),
        BoolConv("smoke", "binary_sensor", mi="13.1.85"),
        Battery,
    ],
    "optional": [ZigbeeStats, BatteryPer],
}, {
    "lumi.sensor_natgas": ["Honeywell", "Gas Sensor", "JTQJ-BF-01LM/BW"],
    "support": 4,  # TODO: selftest?
    "required": [
        Converter("gas_density", "sensor", mi="0.1.85"),
        BoolConv("gas", "binary_sensor", mi="13.1.85"),
    ],
    "optional": [
        ZigbeeStats,
        GasSensitivityReadConv("sensitivity", "select", mi="14.2.85"),
        GasSensitivityWriteConv("sensitivity", mi="14.1.85"),
    ],
}, {
    "lumi.curtain": ["Aqara", "Curtain", "ZNCLDJ11LM"],
    "lumi.curtain.aq2": ["Aqara", "Roller Shade", "ZNGZDJ11LM"],
    "required": [
        MapConv("motor", "cover", mi="14.2.85", map=MOTOR),
        Converter("position", mi="1.1.85", parent="motor"),
        MapConv("run_state", mi="14.4.85", map=RUN_STATE),
    ],
    "optional": [ZigbeeStats],
}, {
    "lumi.curtain.hagl04": ["Aqara", "Curtain B1", "ZNCLDJ12LM"],
    "required": [
        MapConv("motor", "cover", mi="14.2.85", map=MOTOR),
        Converter("position", mi="1.1.85", parent="motor"),
        MapConv("run_state", mi="14.4.85", map=RUN_STATE),
        Converter("battery", "sensor", mi="8.0.2001"),
    ],
    "optional": [ZigbeeStats],
}, {
    "lumi.lock.aq1": ["Aqara", "Door Lock S1", "ZNMS11LM"],
    "lumi.lock.acn02": ["Aqara", "Door Lock S2", "ZNMS12LM"],
    "required": [
        Action, Battery,
        LockConv("key_id", "sensor", mi="13.1.85"),
        BoolConv("lock", "binary_sensor", mi="13.20.85")
    ],
    "optional": [ZigbeeStats],
}, {
    "lumi.lock.acn03": ["Aqara", "Door Lock S2 Pro", "ZNMS12LM*"],
    "required": [
        Action,
        BoolConv("lock", "binary_sensor", mi="3.1.85"),
        # lumi: 0-open, 1-close, 2-ajar / hass: True - open, False - closed
        MapConv("door", "binary_sensor", mi="13.26.85", map={
            0: True, 1: False, 2: True
        }),
        Converter("battery", "sensor", mi="8.0.2001"),
        LockConv("key_id", "sensor", mi="13.1.85"),
        BoolConv("open_verified", mi="13.15.85"),
        Converter("tongue_state", mi="13.16.85"),
        LockConv("lock_control", mi="13.25.85", map=LOCK_CONTROL),
        LockConv("lock_state", mi="13.28.85", map=LOCK_STATE),
    ],
    "optional": [ZigbeeStats],
}, {
    # https://github.com/AlexxIT/XiaomiGateway3/issues/101
    "lumi.airrtc.tcpecn02": ["Aqara", "Thermostat S2", "KTWKQ03ES"],
    "required": [
        # BoolConv("power", mi="3.1.85", xiaomi="power_status"),
        ClimateConv("climate", "climate", mi="14.2.85"),
        Converter("current_temp", mi="3.2.85"),
        MapConv("hvac_mode", mi="14.8.85", map={
            0: "heat", 1: "cool", 15: "off"
        }),
        MapConv("fan_mode", mi="14.10.85", map={
            0: "low", 1: "medium", 2: "high", 3: "auto"
        }),
        ClimateTempConv("target_temp", mi="14.9.85"),
    ],
    "optional": [ZigbeeStats],
}, {
    "lumi.airrtc.vrfegl01": ["Xiaomi", "VRF Air Conditioning"],
    "support": 1,
    "required": [
        Converter("channels", "sensor", mi="13.1.85"),
    ],
    "optional": [ZigbeeStats],
}]

DEVICES += [{
    "lumi.sen_ill.mgl01": ["Xiaomi", "Light Sensor", "GZCGQ01LM"],
    "support": 5,
    "required": [
        Converter("illuminance", "sensor", mi="2.p.1"),
        BatteryConv("battery", "sensor", mi="3.p.1"),  # voltage, mV
    ],
    "optional": [
        ZigbeeStats,
        Converter("battery_voltage", "sensor", mi="3.p.1"),
    ]
}, {
    # no N, https://www.aqara.com/en/single_switch_T1_no-neutral.html
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:switch:0000A003:lumi-l0agl1:1
    "lumi.switch.l0agl1": ["Aqara", "Relay T1", "SSM-U02"],
    "required": [
        Converter("switch", "switch", mi="2.p.1")
    ],
    "optional": [
        ZigbeeStats,
        Converter("chip_temperature", "sensor", mi="2.p.6"),
    ],
}, {
    # with N, https://www.aqara.com/en/single_switch_T1_with-neutral.html
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:switch:0000A003:lumi-n0agl1:1
    "lumi.switch.n0agl1": ["Aqara", "Relay T1", "SSM-U01"],  # no spec
    "lumi.switch.n0acn2": ["Aqara", "Relay T1", "DLKZMK11LM"],
    "support": 5,
    "required": [
        Converter("switch", "switch", mi="2.p.1"),
        MathConv("energy", "sensor", mi="3.p.1", multiply=0.001, round=2),
        MathConv("power", "sensor", mi="3.p.2", round=2),
    ],
    "optional": [
        ZigbeeStats,
        BoolConv("led", "switch", mi="4.p.1"),  # uint8
        MapConv("power_on_state", "select", mi="5.p.1", map=POWEROFF_MEMORY),
    ],
}, {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:outlet:0000A002:lumi-maeu01:1
    "lumi.plug.maeu01": ["Aqara", "Plug", "SP-EUC01"],  # no spec
    "support": 5,
    "required": [
        Converter("plug", "switch", mi="2.p.1"),
        MathConv("energy", "sensor", mi="3.p.1", multiply=0.001, round=2),
        MathConv("power", "sensor", mi="3.p.2", round=2),
    ],
    "optional": [
        ZigbeeStats,
        BoolConv("led", "switch", mi="4.p.1"),  # uint8
        MapConv("power_on_state", "select", mi="5.p.1", map=POWEROFF_MEMORY),
    ],
}, {
    # https://home.miot-spec.com/spec?type=urn:miot-spec-v2:device:motion-sensor:0000A014:lumi-agl04:1:0000C813
    # for spec names Fibaro has good example: https://manuals.fibaro.com/motion-sensor/
    "lumi.motion.agl04": ["Aqara", "Precision Motion Sensor", "RTCGQ13LM"],
    "support": 4,  # TODO: blind_time number setting
    "required": [
        ConstConv("motion", "binary_sensor", mi="4.e.1", value=True),
        BatteryConv("battery", "sensor", mi="3.p.1"),  # voltage, mV
    ],
    "optional": [
        ZigbeeStats,
        MapConv("sensitivity", "select", mi="8.p.1", map={
            1: "low", 2: "medium", 3: "high"
        }),
        Converter("blind_time", mi="10.p.1"),  # from 2 to 180
        MapConv("battery_low", "binary_sensor", mi="5.p.1", map=BATTERY_LOW),
    ],
}, {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-monitor:0000A008:lumi-acn01:1
    "lumi.airmonitor.acn01": [
        "Aqara", "TVOC Air Quality Monitor", "VOCKQJK11LM"  # no spec
    ],
    "support": 5,
    "required": [
        Converter("temperature", "sensor", mi="3.p.1"),  # celsius
        Converter("humidity", "sensor", mi="3.p.2"),  # percentage
        Converter("tvoc", "sensor", mi="3.p.3"),  # ppb
        BatteryConv("battery", "sensor", mi="4.p.2"),  # voltage, mV
    ],
    "optional": [
        ZigbeeStats,
        MapConv("battery_low", "binary_sensor", mi="4.p.1", map=BATTERY_LOW),
        MapConv("display_unit", "select", mi="6.p.1", map={
            0: "℃, mg/m³", 1: "℃, ppb", 16: "℉, mg/m³", 17: "℉, ppb"
        })
    ],
}, {
    "lumi.switch.b1lc04": ["Aqara", "Single Wall Switch E1", "QBKG38LM"],
    "support": 5,
    "required": [
        Converter("switch", "switch", mi="2.p.1"),
        ButtonMIConv("button", mi="6.e.1", value=1),
        ButtonMIConv("button", mi="6.e.2", value=2),
        Action,
    ],
    "optional": [
        ZigbeeStats,
        BoolConv("smart", "switch", mi="6.p.1"),
        BoolConv("led", "switch", mi="3.p.1"),  # uint8
        MapConv("power_on_state", "select", mi="5.p.1", map=POWEROFF_MEMORY),
        MapConv("mode", "select", mi="10.p.1", map=SWITCH_MODE)
    ],
}, {
    "lumi.switch.b2lc04": ["Aqara", "Double Wall Switch E1", "QBKG39LM"],
    "support": 5,
    "required": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        ButtonMIConv("button_1", mi="7.e.1", value=1),
        ButtonMIConv("button_1", mi="7.e.2", value=2),
        ButtonMIConv("button_2", mi="8.e.1", value=1),
        ButtonMIConv("button_2", mi="8.e.2", value=2),
        ButtonMIConv("button_both", mi="9.e.1", value=4),
        Action,
    ],
    "optional": [
        ZigbeeStats,
        BoolConv("smart_1", "switch", mi="7.p.1"),
        BoolConv("smart_2", "switch", mi="8.p.1"),
        BoolConv("led", "switch", mi="4.p.1"),  # uint8
        MapConv("power_on_state", "select", mi="5.p.1", map=POWEROFF_MEMORY),
        MapConv("mode", "select", mi="15.p.1", map=SWITCH_MODE)
    ],
}, {
    # with neutral wire
    "lumi.switch.b1nc01": ["Aqara", "Single Wall Switch E1", "QBKG40LM"],
    # without neutral wire
    "lumi.switch.l1aeu1": ["Aqara", "Single Wall Switch H1", "WS-EUK01"],
    "required": [
        Converter("switch", "switch", mi="2.p.1"),
        ButtonMIConv("button", mi="7.e.1", value=1),
        ButtonMIConv("button", mi="7.e.2", value=2),
        Action,
    ],
    "optional": [ZigbeeStats],
}, {
    # with neutral wire
    "lumi.switch.b2nc01": ["Aqara", "Double Wall Switch E1", "QBKG41LM"],
    # without neutral wire
    "lumi.switch.l2aeu1": ["Aqara", "Double Wall Switch H1", "WS-EUK02"],
    "required": [
        Channel1_MI21, Channel2_MI31, Action,
        ButtonMIConv("button_1", mi="8.e.1", value=1),
        ButtonMIConv("button_1", mi="8.e.2", value=2),
        ButtonMIConv("button_2", mi="9.e.1", value=1),
        ButtonMIConv("button_2", mi="9.e.2", value=2),
        ButtonMIConv("button_both", mi="10.e.1", value=4),
    ],
    "optional": [ZigbeeStats],
}, {
    # required switch firmware 0.0.0_0030
    "lumi.switch.b2naus01": ["Aqara", "Double Wall Switch US", "WS-USC04"],
    "required": [
        Channel1_MI21, Channel2_MI31, Action,
        MathConv("energy", "sensor", mi="4.p.1", multiply=0.001, round=2),
        MathConv("power", "sensor", mi="4.p.2", round=2),
        ButtonMIConv("button_1", mi="7.e.1", value=1),
        ButtonMIConv("button_1", mi="7.e.2", value=2),
        ButtonMIConv("button_2", mi="8.e.1", value=1),
        ButtonMIConv("button_2", mi="8.e.2", value=2),
        ButtonMIConv("button_both", mi="9.e.1", value=4),
    ],
    "optional": [ZigbeeStats],
}, {
    "lumi.remote.acn003": ["Aqara", "Single Wall Button E1", "WXKG16LM"],
    "required": [
        Action,
        ButtonMIConv("button", mi="2.e.1", value=1),  # single
        ButtonMIConv("button", mi="2.e.2", value=2),  # double
        ButtonMIConv("button", mi="2.e.3", value=16),  # long
        Converter("battery", "sensor", mi="3.p.2"),
    ],
    "optional": [ZigbeeStats],
}, {
    "lumi.remote.acn004": ["Aqara", "Double Wall Button E1", "WXKG17LM"],
    "required": [
        Action,
        ButtonMIConv("button_1", mi="2.e.1", value=1),  # single
        ButtonMIConv("button_1", mi="2.e.2", value=2),  # double
        ButtonMIConv("button_1", mi="2.e.3", value=16),  # long
        ButtonMIConv("button_2", mi="7.e.1", value=1),  # single
        ButtonMIConv("button_2", mi="7.e.2", value=2),  # double
        ButtonMIConv("button_2", mi="7.e.3", value=16),  # long
        ButtonMIConv("button_both", mi="8.e.1", value=4),  # single
        Converter("battery", "sensor", mi="3.p.2"),
    ],
    "optional": [ZigbeeStats],
}, {
    "lumi.curtain.acn002": ["Aqara", "Roller Shade E1", "ZNJLBL01LM"],
    "support": 5,
    "required": [
        MapConv("motor", "cover", mi="2.p.2", map={
            0: "stop", 1: "close", 2: "open"
        }),
        Converter("target_position", mi="2.p.4"),
        Converter("position", mi="2.p.5"),
        MapConv("run_state", mi="2.p.6", map=RUN_STATE),
        Converter("battery", "sensor", mi="3.p.4"),  # percent
    ],
    "optional": [
        ZigbeeStats,
        BoolConv("fault", "sensor", mi="2.p.1"),
        Converter("motor_reverse", "switch", mi="2.p.7"),
        MapConv("battery_low", "binary_sensor", mi="3.p.1", map=BATTERY_LOW),
        Converter("battery_voltage", "sensor", mi="3.p.2"),
        MapConv("battery_charging", "binary_sensor", mi="3.p.3", map={
            0: False, 1: True, 2: False
        }),
        MapConv("motor_speed", "select", mi="5.p.5", map={
            0: "low", 1: "mid", 2: "high"
        }),
        # Converter("mode", "sensor", mi="2.p.3"),  # only auto
    ]
}]

################################################################################
# 3rd party zigbee
################################################################################

DEVICES += [{
    # only one attribute with should_poll
    "TS0121": ["BlitzWolf", "Plug", "BW-SHP13"],
    "support": 5,
    "required": [
        ZOnOffConv("plug", "switch"),
        ZCurrent, ZPower, ZVoltagePoll,  # once per 60 seconds
    ],
    "optional": [
        ZigbeeStats, ZTuyaPowerOn,
        ZEnergyConv("energy", "sensor", multiply=0.01),  # once per 5 minutes
    ],
}, {
    "TS0115": ["UseeLink", "Power Strip", "SM-SO306E"],
    "support": 5,
    "required": [
        ZOnOffConv("channel_1", "switch", ep=1),
        ZOnOffConv("channel_2", "switch", ep=2),
        ZOnOffConv("channel_3", "switch", ep=3),
        ZOnOffConv("channel_4", "switch", ep=4),
        ZOnOffConv("usb", "switch", ep=7),
    ],
    "optional": [ZigbeeStats, ZTuyaPowerOn],
}, {
    "01MINIZB": ["Sonoff", "Mini", "ZBMINI"],
    "Lamp_01": ["Ksentry Electronics", "OnOff Controller", "KS-SM001"],
    "SA-003-Zigbee": ["eWeLink", "Zigbee OnOff Controller", "SA-003-Zigbee"],
    "support": 5,
    "required": [ZOnOffConv("switch", "switch")],
    "optional": [ZigbeeStats],
}, {
    "WB01": ["Sonoff", "Button", "SNZB-01"],
    "support": 5,
    "required": [
        ZSonoffButtonConv("action", "sensor"),
        ZBatteryConv("battery", "sensor"),
    ],
    "optional": [ZigbeeStats],
    "config": [
        ZBindConf(clusters={6}, ep=1),
    ]
}, {
    "MS01": ["Sonoff", "Motion Sensor", "SNZB-03"],
    "support": 5,
    "required": [
        ZIASZoneConv("occupancy", "binary_sensor"),
        ZBatteryConv("battery", "sensor"),
    ],
    "optional": [ZigbeeStats],
}, {
    # wrong zigbee model (ewelink bug)
    "TH01": ["Sonoff", "Door/Window Sensor", "SNZB-04"],
    "support": 5,
    "required": [
        ZIASZoneConv("contact", "binary_sensor"),
        ZBatteryConv("battery", "sensor"),
    ],
    "optional": [ZigbeeStats],
}, {
    "FNB56-ZSC01LX1.2": ["Unknown", "Dimmer", "LXZ8-02A"],
    "support": 3,  # TODO: tests, effect?
    "TRADFRI bulb E27 W opal 1000lm": [
        "IKEA", "Bulb E27 1000 lm", "LED1623G12"
    ],
    "required": [
        ZOnOffConv("light", "light"),
        ZBrightnessConv("brightness", parent="light"),
    ],
    "optional": [ZigbeeStats],
}, {
    "SML001": ["Philips", "Hue motion sensor", "9290012607"],
    "support": 4,  # TODO: sensitivity, occupancy_timeout, led
    "required": [
        ZOccupancyConv("occupancy", "binary_sensor", ep=2),
        ZIlluminance("illuminance", "sensor", ep=2),
        ZTemperatureConv("temperature", "sensor", ep=2),
        ZBatteryConv("battery", "sensor", ep=2),
        # ZHueLed("led", "switch"),
    ],
    "optional": [ZigbeeStats],
    "config": [
        ZBindConf(clusters={1, 0x400, 0x402, 0x406}, ep=2),
        ZReportConf(type="battery_percentage_remaining", ep=2),
        ZReportConf(type="occupancy", ep=2),
        ZReportConf(type="temperature", ep=2),
        ZReportConf(type="illuminance", ep=2),
    ]
}, {
    "LWB010": ["Philips", "Hue white 806 lm", "9290011370B"],
    "support": 2,  # TODO: state change, effect?
    "required": [
        ZOnOffConv("light", "light", ep=11),
        ZBrightnessConv("brightness", parent="light", ep=11),
    ],
    "optional": [ZigbeeStats],
}, {
    "LCT001": ["Philips", "Hue Color 600 lm", "9290012573A"],
    "support": 2,  # TODO: state change, effect?
    "required": [
        ZOnOffConv("light", "light", ep=11),
        ZBrightnessConv("brightness", parent="light", ep=11),
        ZColorTempConv("color_temp", parent="light", ep=11),
    ],
    "optional": [ZigbeeStats],
}, {
    "RWL021": ["Philips", "Hue dimmer switch", "324131137411"],
    "support": 2,  # TODO: multiple clicks, tests
    "required": [
        ZHueDimmerOnConv("action", "sensor"),
        ZHueDimmerLevelConv("action", "sensor"),
    ],
    "optional": [ZigbeeStats],
    "config": [
        ZBindConf(clusters={6, 8}, ep=1),
        ZBindConf(clusters={1, 64512}, ep=2),
        ZHueConf(),
    ]
}, {
    "default": "zigbee",  # default zigbee device
    "required": [
        ZOnOffConv("switch", "switch", ep=1, lazy=True),
        ZOnOffConv("channel_2", "switch", ep=2, lazy=True),
        ZOnOffConv("channel_3", "switch", ep=3, lazy=True),
        ZOnOffConv("channel_4", "switch", ep=4, lazy=True),
    ],
    "optional": [ZigbeeStats],
    "config": [
        ZBindConf(clusters={6, 8}, ep=1),  # maybe button
    ]
}]

################################################################################
# BLE
################################################################################

# https://custom-components.github.io/ble_monitor/by_brand
DEVICES += [{
    152: ["Xiaomi", "Flower Care", "HHCCJCY01"],
    "required": [
        MiBeacon, BLETemperature, BLEMoisture, BLEConductivity, BLEIlluminance,
        BLEBatteryLazy,  # no battery info in new firmwares
    ],
    "optional": [BLEStats],
}, {
    349: ["Xiaomi", "Flower Pot", "HHCCPOT002"],
    "required": [
        MiBeacon, BLEMoisture, BLEConductivity,
        BLEBatteryLazy,  # no battery info in new firmwares
    ],
    "optional": [BLEStats],
}, {
    426: ["Xiaomi", "TH Sensor", "LYWSDCGQ/01ZM"],
    839: ["Xiaomi", "Qingping TH Sensor", "CGG1"],
    903: ["Xiaomi", "ZenMeasure TH", "MHO-C401"],
    1115: ["Xiaomi", "TH Clock", "LYWSD02MMC"],
    1371: ["Xiaomi", "TH Sensor 2", "LYWSD03MMC"],
    1398: ["Xiaomi", "Alarm Clock", "CGD1"],
    1647: ["Xiaomi", "Qingping TH Lite", "CGDK2"],
    1747: ["Xiaomi", "ZenMeasure Clock", "MHO-C303"],
    2888: ["Xiaomi", "Qingping TH Sensor", "CGG1"],  # same model as 839?!
    "required": [
        MiBeacon, BLETemperature, BLEHumidity,
        BLEBatteryLazy,  # no battery info in new firmwares
    ],
    "optional": [BLEStats],
}, {
    2038: ["Xiaomi", "Night Light 2", "MJYD02YL-A"],  # 15,4103,4106,4119,4120
    "required": [MiBeacon, BLEBattery, BLELight, BLEMotion],
    "optional": [BLEStats, BLEIdleTime],
}, {
    131: ["Xiaomi", "Kettle", "YM-K1501"],  # CH, HK, RU version
    275: ["Xiaomi", "Kettle", "YM-K1501"],  # international
    1116: ["Xiaomi", "Viomi Kettle", "V-SK152"],  # international
    "required": [MiBeacon, BLEPower, BLETemperature],
    "optional": [BLEStats],
}, {
    1249: ["Xiaomi", "Magic Cube", "XMMF01JQD"],
    "required": [MiBeacon, Action],
    "optional": [BLEStats],
}, {
    # logs: https://github.com/AlexxIT/XiaomiGateway3/issues/180
    2701: ["Xiaomi", "Motion Sensor 2", "RTCGQ02LM"],  # 15,4119,4120
    "required": [BLEMotion, BLEIlluminance, BLEBattery],
    "optional": [BLEStats, BLEIdleTime, BLEAction],
}, {
    # BLE devices can be supported witout spec. New spec will be added
    # "on the fly" when device sends them. But better to rewrite right spec for
    # each device
    "default": "ble",  # default BLE device
    794: ["Xiaomi", "Door Lock", "MJZNMS02LM"],
    982: ["Xiaomi", "Qingping Door Sensor", "CGH1"],
    1034: ["Xiaomi", "Mosquito Repellent", "WX08ZM"],
    1161: ["Xiaomi", "Toothbrush T500", "MES601"],
    1433: ["Xiaomi", "Door Lock", "MJZNMS03LM"],
    1694: ["Aqara", "Door Lock N100 (Bluetooth)", "ZNMS16LM"],
    1695: ["Aqara", "Door Lock N200", "ZNMS17LM"],
    1983: ["Yeelight", "Button S1", "YLAI003"],
    2147: ["Xiaomi", "Water Leak Sensor", "SJWS01LM"],
    2443: ["Xiaomi", "Door Sensor 2", "MCCGQ02HL"],
    2444: ["Xiaomi", "Door Lock", "XMZNMST02YD"],
    2455: ["Honeywell", "Smoke Alarm", "JTYJ-GD-03MI"],
    2480: ["Xiaomi", "Safe Box", "BGX-5/X1-3001"],
    2691: ["Xiaomi", "Qingping Motion Sensor", "CGPR1"],
    "required": [
        MiBeacon, BLEBatteryLazy,
        # sensors:
        Converter("conductivity", "sensor", lazy=True),
        Converter("formaldehyde", "sensor", lazy=True),
        Converter("humidity", "sensor", lazy=True),
        Converter("idle_time", "sensor", lazy=True),
        Converter("illuminance", "sensor", lazy=True),
        Converter("moisture", "sensor", lazy=True),
        Converter("rssi", "sensor", lazy=True),
        Converter("supply", "sensor", lazy=True),
        Converter("temperature", "sensor", lazy=True),
        # binary_sensors:
        Converter("contact", "binary_sensor", lazy=True),
        Converter("gas", "binary_sensor", lazy=True),
        Converter("light", "binary_sensor", lazy=True),
        Converter("lock", "binary_sensor", lazy=True),
        Converter("motion", "binary_sensor", lazy=True),
        Converter("opening", "binary_sensor", lazy=True),
        Converter("sleep", "binary_sensor", lazy=True),
        Converter("smoke", "binary_sensor", lazy=True),
        Converter("water_leak", "binary_sensor", lazy=True),
    ],
    "optional": [BLEStats]
}]

################################################################################
# Mesh
################################################################################

DEVICES += [{
    # brightness 1..65535, color_temp 2700..6500
    948: ["Yeelight", "Mesh Downlight", "YLSD01YL"],
    995: ["Yeelight", "Mesh Bulb E14", "YLDP09YL"],
    996: ["Yeelight", "Mesh Bulb E27", "YLDP10YL"],
    997: ["Yeelight", "Mesh Spotlight", "YLSD04YL"],
    1771: ["Xiaomi", "Mesh Bulb", "MJDP09YL"],
    1772: ["Xiaomi", "Mesh Downlight", "MJTS01YL/MJTS003"],
    2076: ["Yeelight", "Mesh Downlight M2", "YLTS02YL/YLTS04YL"],
    2342: ["Yeelight", "Mesh Bulb M2", "YLDP25YL/YLDP26YL"],
    "required": [
        Converter("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", parent="light", max=65535),
        ColorTempKelvin("color_temp", mi="2.p.3", parent="light"),
    ]
}, {
    1054: ["Xiaomi", "Mesh Group", "yeelink.light.mb1grp"],
    "required": [
        Converter("group", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", parent="light", max=65535),
        ColorTempKelvin("color_temp", mi="2.p.3", parent="light"),
    ]
}, {
    2342: ["Yeelight", "Mesh Bulb M2", "YLDP25YL/YLDP26YL"],
    "required": [
        Converter("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", parent="light", max=65535),
        ColorTempKelvin("color_temp", mi="2.p.3", parent="light"),
    ],
    "optional": [
        BoolConv("smart", "binary_sensor", mi="3.p.5"),
        BoolConv("powerup", "binary_sensor", mi="3.p.11"),
    ]
}, {
    # brightness 1..100, color_temp 2700..6500
    3416: ["PTX", "Mesh Downlight", "090615.light.mlig01"],
    "required": [
        Converter("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", parent="light", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", parent="light"),
    ]
}, {
    # brightness 1..100, color_temp 3000..6400
    2293: ["Unknown", "Mesh Lightstrip (RF ready)", "crzm.light.wy0a01"],
    2351: ["Unknown", "Mesh Downlight", "lemesh.light.wy0c05"],
    2584: ["XinGuang", "Smart Light", "LIBMDA09X"],
    3164: ["Unknown", "Mesh Downlight (RF ready)", "lemesh.light.wy0c07"],
    3531: ["Unknown", "ightctl Light", "lemesh.light.wy0c08"],
    "required": [
        Converter("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", parent="light", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", parent="light",
                        mink=3000, maxk=6400),
    ]
}, {
    1945: ["Unknown", "Mesh Wall Switch", "DHKG01ZM"],
    "required": [
        Converter("switch", "switch", mi="2.p.1"),
    ],
    "optional": [
        Converter("led", "switch", mi="10.p.1"),
    ]
}, {
    2007: ["Unknown", "Mesh Switch Controller", "lemesh.switch.sw0a01"],
    3150: ["XinGuang", "Mesh Switch", "wainft.switch.sw0a01"],
    "required": [
        Converter("switch", "switch", mi="2.p.1"),
    ],
}, {
    2258: ["PTX", "Mesh Single Wall Switch", "PTX-SK1M"],
    "required": [
        Converter("switch", "switch", mi="2.p.1"),
    ],
    "optional": [
        BoolConv("led", "switch", mi="8.p.1"),
        BoolConv("smart", "switch", mi="8.p.2"),
    ]
}, {
    # Mesh Switches
    1946: ["Xiaomi", "Mesh Double Wall Switch", "DHKG02ZM"],
    "required": [
        Converter("left_switch", "switch", mi="2.p.1"),
        Converter("right_switch", "switch", mi="3.p.1"),
    ],
    "optional": [
        Converter("led", "switch", mi="10.p.1"),
        BoolConv("left_smart", "switch", mi="2.p.2"),
        BoolConv("right_smart", "switch", mi="3.p.2"),
    ]
}, {
    2257: ["PTX", "Mesh Double Wall Switch", "PTX-SK2M"],
    "required": [
        Converter("left_switch", "switch", mi="2.p.1"),
        Converter("right_switch", "switch", mi="3.p.1"),
    ],
    "optional": [
        BoolConv("led", "switch", mi="8.p.1"),
        BoolConv("left_smart", "switch", mi="8.p.2"),
        BoolConv("right_smart", "switch", mi="8.p.3"),
    ]
}, {
    3083: ["Xiaomi", "Mi Smart Electrical Outlet", "ZNCZ01ZM"],
    "required": [
        Converter("outlet", "switch", mi="2.p.1"),
        MathConv("power", "sensor", mi="3.p.1", multiply=0.01),
    ],
    "optional": [
        Converter("led", "switch", mi="4.p.1"),
        Converter("power_protect", "switch", mi="7.p.1"),
    ]
}, {
    2093: ["PTX", "Mesh Triple Wall Switch", "PTX-TK3/M"],
    3878: ["PTX", "Mesh Triple Wall Switch", "PTX-SK3M"],
    "required": [
        Converter("left_switch", "switch", mi="2.p.1"),
        Converter("middle_switch", "switch", mi="3.p.1"),
        Converter("right_switch", "switch", mi="4.p.1"),
    ],
    "optional": [
        BoolConv("led", "switch", mi="8.p.1"),
        BoolConv("left_smart", "switch", mi="8.p.2"),
        BoolConv("middle_smart", "switch", mi="8.p.3"),
        BoolConv("right_smart", "switch", mi="8.p.4"),
    ]
}, {
    2715: ["Xiaomi", "Mesh Single Wall Switch", "ZNKG01HL"],
    "required": [
        Converter("switch", "switch", mi="2.p.1"),
        Converter("humidity", "sensor", mi="6.p.1"),
        Converter("temperature", "sensor", mi="6.p.7"),
    ]
}, {
    2716: ["Xiaomi", "Mesh Double Wall Switch", "ZNKG02HL"],
    "required": [
        Converter("left_switch", "switch", mi="2.p.1"),
        Converter("right_switch", "switch", mi="3.p.1"),
        Converter("humidity", "sensor", mi="6.p.1"),
        Converter("temperature", "sensor", mi="6.p.7"),
    ]
}, {
    2717: ["Xiaomi", "Mesh Triple Wall Switch", "ZNKG03HL/ISA-KG03HL"],
    "required": [
        Converter("left_switch", "switch", mi="2.p.1"),
        Converter("middle_switch", "switch", mi="3.p.1"),
        Converter("right_switch", "switch", mi="4.p.1"),
        Converter("humidity", "sensor", mi="6.p.1"),
        Converter("temperature", "sensor", mi="6.p.7"),
    ],
    "optional": [
        BoolConv("left_smart", "switch", mi="2.p.2"),
        BoolConv("middle_smart", "switch", mi="3.p.2"),
        BoolConv("right_smart", "switch", mi="4.p.2"),
        Converter("baby_mode", "switch", mi="11.p.1"),
    ]
}, {
    "default": "mesh",  # default Mesh device
    "required": [],
    "optional": [

    ]
}]
