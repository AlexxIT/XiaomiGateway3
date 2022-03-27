"""
Each device has a specification:

    {
        "<model>": ["<brand>", "<name>", "<market model>"],
        "spec": [<list of converters>],
        "support": <from 1 to 5>,
        "ttl": <time to live>
    }

- model - `lumi.xxx` for Zigbee devices, number (pdid) for BLE and Mesh devices
- spec - list of converters
- support - optional score of support from 5 to 1
- ttl - optional available timeout

Each converter has:

    Converter(<attribute name>, <hass domain>, <mi name>)

- attribute - required, entity or attribute name in Hass
- domain - optional, hass entity type (`sensor`, `switch`, `binary_sensor`, etc)
- mi - optional, item name in Lumi spec (`8.0.2012`) or MIoT spec (`2.p.1`)
- enabled - optional, default True:
   - True - entity will be enabled on first setup
   - False - entity and converter! will be disabled on first setup
   - None - converter will be enabled, but entity will be setup with first data

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

    BoolConv("light", "light", "4.1.85")
    BrightnessConv("brightness", mi="14.1.85", parent="light")
    Converter("color_temp", mi="14.2.85", parent="light")

Another case: one converter may generate multiple attributes, so you should
set `childs` for it. By default `sensor` and `binary_sensor` with childs will
adds its values to its attributes.

If converter has `enabled=None` - it will work, but entity will setup only with
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
- wireless - change mode from wired to wireless (decoupled)
- power_on_state - default state when electricity is supplied
- contact - for contact sensor
- moisture - for water leak sensor

Support level should be set only for confirmed devices. For theoretically
supported it should be empty. For unsupported it should be less than 3.

Support levels:
- 5 - The device can do everything it can do
- 4 - The device works well, missing some settings
- 3 - The device works, but it missing some functionality
- 2 - The device does not work well, it is not recommended to use
- 1 - The device does not work at all
- empty - theoretically supported, unconfirmed

Nice project with MIoT spec description: https://home.miot-spec.com/
"""
from .base import *
from .mibeacon import *
from .stats import *
from .zigbee import *

################################################################################
# Gateways
################################################################################

DEVICES = [{
    "lumi.gateway.mgl03": ["Xiaomi", "Gateway 3", "ZNDMWG03LM ZNDMWG02LM"],
    "support": 4,  # @AlexxIT TODO: cloud link
    "spec": [
        # write pair=60 => report discovered_mac => report 8.0.2166? =>
        # write pair_command => report added_device => write pair=0
        MapConv("pair", mi="8.0.2109", map={60: True, 0: False},
                parent="data"),
        MapConv("alarm", "alarm_control_panel", mi="3.p.1", map=GATE_ALARM),
        BoolConv("alarm_trigger", mi="3.p.22", parent="alarm"),

        Converter("discovered_mac", mi="8.0.2110", parent="data"),
        Converter("pair_command", mi="8.0.2111", parent="data"),
        Converter("added_device", mi="8.0.2084", parent="data"),
        RemoveDIDConv("remove_did", mi="8.0.2082", parent="data"),

        # also updated from child devices OTAConv
        Converter("ota_progress", parent="data"),

        # support change with remote.send_command
        Converter("power_tx", mi="8.0.2012"),
        Converter("channel", mi="8.0.2024"),

        MapConv("command", "select", map=GW3_COMMANDS),
        Converter("data", "select"),

        CloudLinkConv(
            "cloud_link", "binary_sensor", mi="8.0.2155", enabled=False
        ),
        BoolConv("led", "switch", mi="6.p.6", enabled=False),

        GatewayStats,

        # Converter("device_model", mi="8.0.2103"),  # very rare
        # ConstConv("pair", mi="8.0.2081", value=False),  # legacy pairing_stop
    ],
}, {
    "lumi.gateway.aqcn02": ["Aqara", "Hub E1 CN", "ZHWG16LM"],
    "lumi.gateway.aqcn03": ["Aqara", "Hub E1 EU", "HE1-G01"],
    "support": 3,  # @AlexxIT
    "spec": [
        MapConv("pair", mi="8.0.2109", map={60: True, 0: False},
                parent="data"),

        Converter("discovered_mac", mi="8.0.2110", parent="data"),
        Converter("pair_command", mi="8.0.2111", parent="data"),
        Converter("added_device", mi="8.0.2084", parent="data"),
        Converter("remove_did", mi="8.0.2082", parent="data"),

        # also updated from child devices OTAConv
        Converter("ota_progress", parent="data"),

        # support change with remote.send_command
        Converter("power_tx", mi="8.0.2012"),
        Converter("channel", mi="8.0.2024"),

        MapConv("command", "select", map=E1_COMMANDS),
        Converter("data", "select"),

        GatewayStats
    ],
}]

################################################################################
# Zigbee
################################################################################

DEVICES += [{
    # don"t work: protect 8.0.2014, power 8.0.2015, plug_detection 8.0.2044
    "lumi.plug": ["Xiaomi", "Plug CN", "ZNCZ02LM"],  # tested
    "lumi.plug.mitw01": ["Xiaomi", "Plug TW", "ZNCZ03LM"],
    "lumi.plug.maus01": ["Xiaomi", "Plug US", "ZNCZ12LM"],
    "support": 5,  # @AlexxIT
    "spec": [
        Plug, Power, Energy, ChipTemp,
        PowerOffMemory, ChargeProtect, Led,
        # Converter("max_power", "sensor", mi="8.0.2042", enabled=False),
    ],
}, {
    "lumi.plug.mmeu01": ["Xiaomi", "Plug EU", "ZNCZ04LM"],
    "spec": [Plug, Power, Voltage, Energy],
}, {
    "lumi.ctrl_86plug.aq1": ["Aqara", "Wall Outlet", "QBCZ11LM"],
    "lumi.ctrl_86plug": ["Aqara", "Wall Outlet", "QBCZ11LM"],
    "spec": [
        Outlet, Power, Energy, ChipTemp,
        PowerOffMemory, ChargeProtect, Led, Wireless,
    ],
}, {
    "lumi.ctrl_ln1.aq1": ["Aqara", "Single Wall Switch", "QBKG11LM"],
    "lumi.ctrl_ln1": ["Aqara", "Single Wall Switch", "QBKG11LM"],
    "lumi.switch.b1nacn02": [
        "Aqara", "Single Wall Switch D1 CN (with N)", "QBKG23LM"
    ],
    "spec": [Switch, Power, Energy, Action, Button, Wireless, Led],
}, {
    "lumi.ctrl_neutral1": ["Aqara", "Single Wall Switch", "QBKG04LM"],
    "lumi.switch.b1lacn02": [
        "Aqara", "Single Wall Switch D1 CN (no N)", "QBKG21LM"
    ],
    "spec": [Switch, Action, Button, Wireless, Led],
}, {
    # dual channel on/off, power measurement
    "lumi.ctrl_ln2.aq1": ["Aqara", "Double Wall Switch", "QBKG12LM"],
    "lumi.ctrl_ln2": ["Aqara", "Double Wall Switch", "QBKG12LM"],
    "lumi.switch.b2nacn02": [
        "Aqara", "Double Wall Switch D1 CN (with N)", "QBKG24LM"
    ],
    "spec": [
        Channel1, Channel2, Power, Energy,
        Action, Button1, Button2, ButtonBoth,
        Wireless1, Wireless2, PowerOffMemory, Led,
    ],
}, {
    "lumi.relay.c2acn01": ["Aqara", "Relay CN", "LLKZMK11LM"],  # tested
    "support": 4,  # @AlexxIT TODO: test load_s0 8.0.2034 load_s1 8.0.2035
    "spec": [
        Channel1, Channel2, Current, Power, Voltage, Energy,
        Action, Button1, Button2, ButtonBoth, ChipTemp,
        BoolConv("interlock", "switch", mi="4.9.85", enabled=False),
    ],
}, {
    "lumi.ctrl_neutral2": ["Aqara", "Double Wall Switch (no N)", "QBKG03LM"],
    "lumi.switch.b2lacn02": [
        "Aqara", "Double Wall Switch D1 CN (no N)", "QBKG22LM"
    ],
    "spec": [
        Channel1, Channel2, Action, Button1, Button2, ButtonBoth,
        Wireless1, Wireless2, Led,
    ]
}, {
    # triple channel on/off, no neutral wire
    "lumi.switch.l3acn3": [
        "Aqara", "Triple Wall Switch D1 CN (no N)", "QBKG25LM"
    ],
    "spec": [
        Channel1, Channel2, Channel3,
        Action, Button1, Button2, Button3, Button12, Button13, Button23,
        Wireless1, Wireless2, Wireless3, PowerOffMemory, Led,
    ],
}, {
    # with neutral wire, thanks @Mantoui
    "lumi.switch.n3acn3": [
        "Aqara", "Triple Wall Switch D1 CN (with N)", "QBKG26LM"
    ],
    "spec": [
        Channel1, Channel2, Channel3, Power, Voltage, Energy,
        Action, Button1, Button2, Button3, Button12, Button13, Button23,
        Wireless1, Wireless2, Wireless3, PowerOffMemory, Led,
    ],
}, {
    # we using lumi+zigbee covnerters for support heartbeats and transition
    # light with brightness and color temp
    "lumi.light.cwopcn02": ["Aqara", "Opple MX650 CN", "XDD12LM"],
    "lumi.light.cwopcn03": ["Aqara", "Opple MX480 CN", "XDD13LM"],
    "ikea.light.led1545g12": ["IKEA", "Bulb E27 980 lm", "LED1545G12"],
    "ikea.light.led1546g12": ["IKEA", "Bulb E27 950 lm", "LED1546G12"],
    "ikea.light.led1536g5": ["IKEA", "Bulb E14 400 lm", "LED1536G5"],
    "ikea.light.led1537r6": ["IKEA", "Bulb GU10 400 lm", "LED1537R6"],
    "spec": [
        BoolConv("light", "light", mi="4.1.85"),
        ZXiaomiBrightnessConv("brightness", mi="14.1.85", parent="light"),
        ZXiaomiColorTempConv("color_temp", mi="14.2.85", parent="light")
    ],
}, {
    "lumi.light.aqcn02": ["Aqara", "Bulb CN", "ZNLDP12LM"],
    "spec": [
        BoolConv("light", "light", mi="4.1.85"),
        ZXiaomiBrightnessConv("brightness", mi="14.1.85", parent="light"),
        ZXiaomiColorTempConv("color_temp", mi="14.2.85", parent="light"),
        MapConv("power_on_state", "select", mi="8.0.2030", map=BULB_MEMORY,
                enabled=False),
    ],
}, {
    # light with brightness
    "ikea.light.led1623g12": ["IKEA", "Bulb E27 1000 lm", "LED1623G12"],
    "ikea.light.led1650r5": ["IKEA", "Bulb GU10 400 lm", "LED1650R5"],
    "ikea.light.led1649c5": ["IKEA", "Bulb E14 400 lm", "LED1649C5"],  # tested
    "spec": [
        BoolConv("light", "light", mi="4.1.85"),
        ZXiaomiBrightnessConv("brightness", mi="14.1.85", parent="light"),
    ],
}, {
    # button action, no retain
    "lumi.sensor_switch": ["Xiaomi", "Button", "WXKG01LM"],
    "lumi.remote.b1acn01": ["Aqara", "Button CN", "WXKG11LM"],
    "lumi.sensor_switch.aq2": ["Aqara", "Button", "WXKG11LM"],
    "lumi.sensor_switch.aq3": ["Aqara", "Shake Button", "WXKG12LM"],
    "lumi.remote.b186acn01": ["Aqara", "Single Wall Button CN", "WXKG03LM"],
    "lumi.remote.b186acn02": ["Aqara", "Single Wall Button D1 CN", "WXKG06LM"],
    "lumi.sensor_86sw1": ["Aqara", "Single Wall Button", "WXKG03LM"],
    "spec": [Action, Button, Battery, BatteryLow, BatteryOrig, ChipTemp],
}, {
    # multi button action, no retain
    "lumi.sensor_86sw2.es1": ["Aqara", "Double Wall Button", "WXKG02LM"],
    "lumi.sensor_86sw2": ["Aqara", "Double Wall Button", "WXKG02LM"],
    "lumi.remote.b286acn01": ["Aqara", "Double Wall Button CN", "WXKG02LM"],
    "lumi.remote.b286acn02": ["Aqara", "Double Wall Button D1 CN", "WXKG07LM"],
    "spec": [
        Action, Button1, Button2, ButtonBoth, Battery, BatteryLow, BatteryOrig,
        ChipTemp
    ],
}, {
    "lumi.remote.b286opcn01": ["Aqara", "Opple Two Button CN", "WXCJKG11LM"],
    "lumi.remote.b486opcn01": ["Aqara", "Opple Four Button CN", "WXCJKG12LM"],
    "lumi.remote.b686opcn01": ["Aqara", "Opple Six Button CN", "WXCJKG13LM"],
    "spec": [
        ZAqaraOppleMode("mode", "select", enabled=False),
        Action, Button1, Button2, Button3, Button4, Button5, Button6,
        ButtonBoth, Battery, BatteryLow, BatteryOrig, ChipTemp,
    ],
}, {
    # temperature and humidity sensor
    "lumi.sensor_ht": ["Xiaomi", "TH Sensor", "WSDCGQ01LM"],
    "spec": [
        Temperature, Humidity, Battery, BatteryLow, BatteryOrig, ChipTemp
    ],
}, {
    # temperature, humidity and pressure sensor
    "lumi.weather": ["Aqara", "TH Sensor", "WSDCGQ11LM"],
    "spec": [
        Temperature, Humidity, Battery, BatteryOrig,
        MathConv("pressure", "sensor", mi="0.3.85", multiply=0.01),
    ],
}, {
    # door window sensor
    "lumi.sensor_magnet": ["Xiaomi", "Door/Window Sensor", "MCCGQ01LM"],
    "lumi.sensor_magnet.aq2": ["Aqara", "Door/Window Sensor", "MCCGQ11LM"],
    "spec": [
        # hass: On means open, Off means closed
        BoolConv("contact", "binary_sensor", mi="3.1.85"),
        Battery, BatteryLow, BatteryOrig, ChipTemp,
    ],
}, {
    # motion sensor
    "lumi.sensor_motion": ["Xiaomi", "Motion Sensor", "RTCGQ01LM"],
    "spec": [
        BoolConv("motion", "binary_sensor", mi="3.1.85"),
        Battery, BatteryLow, BatteryOrig, ChipTemp
    ],
}, {
    # motion sensor with illuminance
    "lumi.sensor_motion.aq2": ["Aqara", "Motion Sensor", "RTCGQ11LM"],
    "spec": [
        BoolConv("motion", "binary_sensor", mi="3.1.85"),
        Converter("illuminance", "sensor", mi="0.3.85"),
        # Converter("illuminance", "sensor", mi="0.4.85"),
        Battery, BatteryOrig
    ],
}, {
    # water leak sensor
    "lumi.sensor_wleak.aq1": ["Aqara", "Water Leak Sensor", "SJCGQ11LM"],
    "spec": [
        BoolConv("moisture", "binary_sensor", mi="3.1.85"),
        Battery, BatteryOrig,
    ],
}, {
    # vibration sensor
    "lumi.vibration.aq1": ["Aqara", "Vibration Sensor", "DJT11LM"],
    "support": 3,  # @AlexxIT TODO: need some tests
    "spec": [
        Action, Battery, BatteryLow, BatteryOrig,
        Converter("bed_activity", mi="0.1.85"),
        TiltAngleConv("tilt_angle", mi="0.2.85"),
        Converter("vibrate_intensity", mi="0.3.85"),
        VibrationConv("vibration", mi="13.1.85"),
        Converter("vibration_level", mi="14.1.85"),  # read/write from 1 to 30
    ],
}, {
    # cube action, no retain
    "lumi.sensor_cube.aqgl01": ["Aqara", "Cube EU", "MFKZQ01LM"],  # tested
    "lumi.sensor_cube": ["Aqara", "Cube", "MFKZQ01LM"],
    "support": 5,  # @AlexxIT
    "spec": [
        ZAqaraCubeMain("action", "sensor"),
        ZAqaraCubeRotate("angle"),
        # Converter("action", mi="13.1.85"),
        # Converter("duration", mi="0.2.85", parent="action"),
        # MathConv("angle", mi="0.3.85", parent="action", multiply=0.001),
        Battery, BatteryOrig
    ],
}, {
    "lumi.sensor_smoke": ["Honeywell", "Smoke Sensor", "JTYJ-GD-01LM/BW"],
    "spec": [
        Converter("smoke_density", "sensor", mi="0.1.85"),
        BoolConv("smoke", "binary_sensor", mi="13.1.85"),
        Battery, BatteryOrig
    ],
}, {
    "lumi.sensor_natgas": ["Honeywell", "Gas Sensor", "JTQJ-BF-01LM/BW"],
    "support": 4,  # @AlexxIT TODO: selftest?
    "spec": [
        Converter("gas_density", "sensor", mi="0.1.85"),
        BoolConv("gas", "binary_sensor", mi="13.1.85"),
        GasSensitivityReadConv(
            "sensitivity", "select", mi="14.2.85", enabled=False
        ),
        GasSensitivityWriteConv("sensitivity", mi="14.1.85"),
    ],
}, {
    "lumi.curtain": ["Aqara", "Curtain", "ZNCLDJ11LM"],
    "lumi.curtain.aq2": ["Aqara", "Roller Shade", "ZNGZDJ11LM"],
    "spec": [
        MapConv("motor", "cover", mi="14.2.85", map=MOTOR),
        Converter("position", mi="1.1.85", parent="motor"),
        MapConv("run_state", mi="14.4.85", map=RUN_STATE, parent="motor"),
    ],
}, {
    "lumi.curtain.hagl04": ["Aqara", "Curtain B1 EU", "ZNCLDJ12LM"],
    "spec": [
        MapConv("motor", "cover", mi="14.2.85", map=MOTOR),
        Converter("position", mi="1.1.85", parent="motor"),
        MapConv("run_state", mi="14.4.85", map=RUN_STATE, parent="motor"),
        Converter("battery", "sensor", mi="8.0.2001"),
        MapConv("power_mode", mi="14.5.85", map={
            1: "adapter", 3: "battery", 4: "charging"
        })
    ],
}, {
    "lumi.lock.aq1": ["Aqara", "Door Lock S1", "ZNMS11LM"],
    "lumi.lock.acn02": ["Aqara", "Door Lock S2 CN", "ZNMS12LM"],
    "spec": [
        # dead_bolt or square_locked or 13.22.85
        LockConv("square", "binary_sensor", mi="13.16.85", mask=0x10),
        # anti_bolt or reverse_locked or 3.1.85
        LockConv("reverse", "binary_sensor", mi="13.16.85", mask=0x04),
        # latch_bolt
        LockConv("latch", "binary_sensor", mi="13.16.85", mask=0x01),
        # other sensors
        Converter("battery", "sensor", mi="8.0.2001"),
        LockActionConv("key_id", "sensor", mi="13.1.85"),
        # BoolConv("lock", "binary_sensor", mi="13.20.85")
        Action,
    ],
}, {
    # it's better to read only one property 13.26.85 and ignore others
    "lumi.lock.acn03": ["Aqara", "Door Lock S2 Pro CN", "ZNMS13LM"],
    "spec": [
        # corner_bolt or door_state or 13.26.85 (only on S2 Pro)
        LockConv("lock", "binary_sensor", mi="13.16.85", mask=0x40),
        # dead_bolt or square_locked or 13.22.85
        LockConv("square", "binary_sensor", mi="13.16.85", mask=0x10),
        # anti_bolt or reverse_locked or 3.1.85
        LockConv("reverse", "binary_sensor", mi="13.16.85", mask=0x04),
        # latch_bolt
        LockConv("latch", "binary_sensor", mi="13.16.85", mask=0x01),
        # other sensors
        Converter("battery", "sensor", mi="8.0.2001"),
        LockActionConv("key_id", mi="13.1.85"),
        LockActionConv("lock_control", mi="13.25.85", map=LOCK_CONTROL),
        LockActionConv("door_state", mi="13.26.85", map=DOOR_STATE),
        LockActionConv("lock_state", mi="13.28.85", map=LOCK_STATE),
        LockActionConv("alarm", mi="13.5.85", map=LOCK_ALARM),
        LockActionConv("card_wrong", mi="13.2.85"),
        LockActionConv("psw_wrong", mi="13.3.85"),
        LockActionConv("fing_wrong", mi="13.4.85"),
        LockActionConv("verified_wrong", mi="13.6.85"),
        Action,
        # BoolConv("reverse_locked", "binary_sensor", mi="3.1.85"),
        # BoolConv("square_locked", mi="13.22.85"),
        # BoolConv("open_verified", mi="13.15.85"),
        # BoolConv("elekey_verified", mi="13.27.85"),
        # BoolConv("key_not_pull", mi="13.35.85"),
    ],
}, {
    # https://github.com/AlexxIT/XiaomiGateway3/issues/101
    "lumi.airrtc.tcpecn02": ["Aqara", "Thermostat S2 CN", "KTWKQ03ES"],
    "spec": [
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
}, {
    "lumi.airrtc.vrfegl01": ["Xiaomi", "VRF Air Conditioning EU"],
    "support": 1,
    "spec": [
        Converter("channels", "sensor", mi="13.1.85"),
    ],
}]

# Xiaomi Zigbee MIoT spec
DEVICES += [{
    "lumi.sen_ill.mgl01": ["Xiaomi", "Light Sensor EU", "GZCGQ01LM"],
    # "support": 5,  # @AlexxIT bug with gw fw 1.5.1
    "spec": [
        Converter("illuminance", "sensor", mi="2.p.1"),
        BatteryConv("battery", "sensor", mi="3.p.1"),  # voltage, mV
        # new gw firmwares has a bug - don't bind power cluster
        # ZBatteryVoltConv("battery", bind=True, report=True),
    ],
}, {
    "lumi.magnet.acn001": ["Aqara", "Door/Window Sensor E1 CN", "MCCGQ14LM"],
    # "support": 5,
    "spec": [
        MapConv("contact", "binary_sensor", mi="2.p.1", map=INVERSE),
        BatteryConv("battery", "sensor", mi="3.p.2"),  # voltage, mV
        MapConv("battery_low", "binary_sensor", mi="3.p.1", map=BATTERY_LOW,
                enabled=False),
    ],
}, {
    "lumi.sensor_ht.agl02": ["Aqara", "TH Sensor T1", "WSDCGQ12LM"],
    "spec": [
        Converter("temperature", "sensor", mi="2.p.1"),  # celsius
        Converter("humidity", "sensor", mi="2.p.2"),  # percentage
        Converter("pressure", "sensor", mi="2.p.3"),  # kilopascal
        BatteryConv("battery", "sensor", mi="3.p.1"),  # voltage, mV
        MapConv("battery_low", "binary_sensor", mi="4.p.1", map=BATTERY_LOW,
                enabled=False),
    ],
}, {
    # https://home.miot-spec.com/spec?type=urn:miot-spec-v2:device:motion-sensor:0000A014:lumi-agl04:1:0000C813
    # for spec names Fibaro has good example: https://manuals.fibaro.com/motion-sensor/
    "lumi.motion.agl04": ["Aqara", "Precision Motion Sensor EU", "RTCGQ13LM"],
    # "support": 5,  # @zvldz
    "spec": [
        ConstConv("motion", "binary_sensor", mi="4.e.1", value=True),
        BatteryConv("battery", "sensor", mi="3.p.1"),  # voltage, mV
        MapConv("sensitivity", "select", mi="8.p.1", map={
            1: "low", 2: "medium", 3: "high"
        }, enabled=False),
        MathConv("blind_time", "number", mi="10.p.1", min=2, max=180,
                 enabled=False),
        MapConv("battery_low", "binary_sensor", mi="5.p.1", map=BATTERY_LOW,
                enabled=False),
        Converter("idle_time", "sensor", mi="6.p.1", enabled=False),
    ],
}, {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-monitor:0000A008:lumi-acn01:1
    "lumi.airmonitor.acn01": [
        "Aqara", "Air Quality Monitor CN", "VOCKQJK11LM"
    ],
    # "support": 5,
    "spec": [
        Converter("temperature", "sensor", mi="3.p.1"),  # celsius
        Converter("humidity", "sensor", mi="3.p.2"),  # percentage
        Converter("tvoc", "sensor", mi="3.p.3"),  # ppb
        BatteryConv("battery", "sensor", mi="4.p.2"),  # voltage, mV
        MapConv("battery_low", "binary_sensor", mi="4.p.1", map=BATTERY_LOW,
                enabled=False),
        MapConv("display_unit", "select", mi="6.p.1", map={
            0: "℃, mg/m³", 1: "℃, ppb", 16: "℉, mg/m³", 17: "℉, ppb"
        }, enabled=False)
    ],
}, {
    "lumi.curtain.acn002": ["Aqara", "Roller Shade E1 CN", "ZNJLBL01LM"],
    # "support": 5,
    "spec": [
        MapConv("motor", "cover", mi="2.p.2", map={
            0: "stop", 1: "close", 2: "open"
        }),
        Converter("target_position", mi="2.p.4"),
        CurtainPosConv("position", mi="2.p.5", parent="motor"),
        MapConv("run_state", mi="2.p.6", map=RUN_STATE, parent="motor"),
        Converter("battery", "sensor", mi="3.p.4"),  # percent
        Converter("motor_reverse", "switch", mi="2.p.7", enabled=False),
        MapConv("battery_low", "binary_sensor", mi="3.p.1", map=BATTERY_LOW,
                enabled=False),
        Converter("battery_voltage", "sensor", mi="3.p.2", enabled=False),
        MapConv("battery_charging", "binary_sensor", mi="3.p.3", map={
            0: False, 1: True, 2: False
        }, enabled=False),
        MapConv("motor_speed", "select", mi="5.p.5", map={
            0: "low", 1: "mid", 2: "high"
        }, enabled=False),
        # BoolConv("fault", "sensor", mi="2.p.1", enabled=False),
        # Converter("mode", "sensor", mi="2.p.3"),  # only auto
    ],
}, {
    "lumi.remote.acn003": ["Aqara", "Single Wall Button E1 CN", "WXKG16LM"],
    "spec": [
        Action,
        ButtonMIConv("button", mi="2.e.1", value=1),  # single
        ButtonMIConv("button", mi="2.e.2", value=2),  # double
        ButtonMIConv("button", mi="2.e.3", value=16),  # long
        BatteryConv("battery", "sensor", mi="3.p.2"),
    ],
}, {
    "lumi.remote.acn004": ["Aqara", "Double Wall Button E1 CN", "WXKG17LM"],
    "spec": [
        Action,
        ButtonMIConv("button_1", mi="2.e.1", value=1),  # single
        ButtonMIConv("button_1", mi="2.e.2", value=2),  # double
        ButtonMIConv("button_1", mi="2.e.3", value=16),  # long
        ButtonMIConv("button_2", mi="7.e.1", value=1),  # single
        ButtonMIConv("button_2", mi="7.e.2", value=2),  # double
        ButtonMIConv("button_2", mi="7.e.3", value=16),  # long
        ButtonMIConv("button_both", mi="8.e.1", value=4),  # single
        BatteryConv("battery", "sensor", mi="3.p.2"),
    ],
}]

# relays and switches
DEVICES += [{
    # https://www.aqara.com/en/single_switch_T1_no-neutral.html
    "lumi.switch.l0agl1": ["Aqara", "Relay T1 EU (no N)", "SSM-U02"],
    # "support": 5,
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),
        Converter("chip_temperature", "sensor", mi="2.p.6", enabled=False),
    ],
}, {
    # https://www.aqara.com/en/single_switch_T1_with-neutral.html
    "lumi.switch.n0agl1": ["Aqara", "Relay T1 EU (with N)", "SSM-U01"],
    "lumi.switch.n0acn2": ["Aqara", "Relay T1 CN (with N)", "DLKZMK11LM"],
    # "support": 5,
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),
        MathConv("energy", "sensor", mi="3.p.1", multiply=0.001, round=2),
        MathConv("power", "sensor", mi="3.p.2", round=2),
        BoolConv("led", "switch", mi="4.p.1", enabled=False),  # uint8
        MapConv("power_on_state", "select", mi="5.p.1", map=POWEROFF_MEMORY,
                enabled=False),
    ],
}, {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:outlet:0000A002:lumi-maeu01:1
    "lumi.plug.maeu01": ["Aqara", "Plug EU", "SP-EUC01"],  # no spec
    # "support": 5,
    "spec": [
        Converter("plug", "switch", mi="2.p.1"),
        MathConv("energy", "sensor", mi="3.p.1", multiply=0.001, round=2),
        MathConv("power", "sensor", mi="3.p.2", round=2),
        BoolConv("led", "switch", mi="4.p.1", enabled=False),  # uint8
        MapConv("power_on_state", "select", mi="5.p.1", map=POWEROFF_MEMORY,
                enabled=False),
    ],
}, {
    "lumi.switch.b1lc04": [
        "Aqara", "Single Wall Switch E1 (no N)", "QBKG38LM"
    ],
    # "support": 5,
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),
        ButtonMIConv("button", mi="6.e.1", value=1),
        ButtonMIConv("button", mi="6.e.2", value=2),
        Action,
        BoolConv("led", "switch", mi="3.p.1", enabled=False),  # uint8
        MapConv("power_on_state", "select", mi="4.p.1", map=POWEROFF_MEMORY,
                enabled=False),
        BoolConv("wireless", "switch", mi="6.p.1", enabled=False),
        MapConv("mode", "select", mi="10.p.1", map=SWITCH_MODE, enabled=False)
    ],
}, {
    "lumi.switch.b2lc04": [
        "Aqara", "Double Wall Switch E1 (no N)", "QBKG39LM"
    ],
    # "support": 5,
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        ButtonMIConv("button_1", mi="7.e.1", value=1),
        ButtonMIConv("button_1", mi="7.e.2", value=2),
        ButtonMIConv("button_2", mi="8.e.1", value=1),
        ButtonMIConv("button_2", mi="8.e.2", value=2),
        ButtonMIConv("button_both", mi="9.e.1", value=4),
        Action,
        BoolConv("wireless_1", "switch", mi="7.p.1", enabled=False),
        BoolConv("wireless_2", "switch", mi="8.p.1", enabled=False),
        BoolConv("led", "switch", mi="4.p.1", enabled=False),  # uint8
        MapConv("power_on_state", "select", mi="5.p.1", map=POWEROFF_MEMORY,
                enabled=False),
        MapConv("mode", "select", mi="15.p.1", map=SWITCH_MODE, enabled=False)
    ],
}, {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:switch:0000A003:lumi-b1nc01:1
    "lumi.switch.b1nc01": [
        "Aqara", "Single Wall Switch E1 (with N)", "QBKG40LM"
    ],
    # "support": 5,
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),
        ButtonMIConv("button", mi="7.e.1", value=1),
        ButtonMIConv("button", mi="7.e.2", value=2),
        Action,
        BoolConv("led", "switch", mi="4.p.1", enabled=False),  # uint8
        BoolConv("led_reverse", "switch", mi="4.p.2", enabled=False),  # uint8
        MapConv("power_on_state", "select", mi="5.p.1", map=POWEROFF_MEMORY,
                enabled=False),
        BoolConv("wireless", "switch", mi="7.p.1", enabled=False),
    ],
}, {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:switch:0000A003:lumi-b2nc01:1
    "lumi.switch.b2nc01": [
        "Aqara", "Double Wall Switch E1 (with N)", "QBKG41LM"
    ],
    # "support": 5,
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        ButtonMIConv("button_1", mi="8.e.1", value=1),
        ButtonMIConv("button_1", mi="8.e.2", value=2),
        ButtonMIConv("button_2", mi="9.e.1", value=1),
        ButtonMIConv("button_2", mi="9.e.2", value=2),
        ButtonMIConv("button_both", mi="10.e.1", value=4),
        Action,
        BoolConv("led", "switch", mi="5.p.1", enabled=False),  # uint8
        BoolConv("led_reverse", "switch", mi="5.p.2", enabled=False),  # uint8
        MapConv("power_on_state", "select", mi="6.p.1", map=POWEROFF_MEMORY,
                enabled=False),
        BoolConv("wireless_1", "switch", mi="8.p.1", enabled=False),
        BoolConv("wireless_2", "switch", mi="9.p.1", enabled=False),
    ],
}, {
    # required switch firmware 0.0.0_0030
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:switch:0000A003:lumi-b2naus01:1
    "lumi.switch.b2naus01": [
        "Aqara", "Double Wall Switch US (with N)", "WS-USC04"
    ],
    # "support": 5,
    "spec": [
        Channel1_MI21, Channel2_MI31, Action,
        MathConv("energy", "sensor", mi="4.p.1", multiply=0.001, round=2),
        MathConv("power", "sensor", mi="4.p.2", round=2),
        ButtonMIConv("button_1", mi="8.e.1", value=1),
        ButtonMIConv("button_1", mi="8.e.2", value=2),
        ButtonMIConv("button_2", mi="9.e.1", value=1),
        ButtonMIConv("button_2", mi="9.e.2", value=2),
        ButtonMIConv("button_both", mi="10.e.1", value=4),
        BoolConv("led", "switch", mi="5.p.1", enabled=False),  # uint8
        MapConv("power_on_state", "select", mi="6.p.1", map=POWEROFF_MEMORY,
                enabled=False),
        BoolConv("wireless_1", "switch", mi="8.p.1", enabled=False),  # uint8
        BoolConv("wireless_2", "switch", mi="9.p.1", enabled=False),  # uint8
    ],
}, {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:switch:0000A003:lumi-l1acn1:1
    "lumi.switch.l1acn1": [
        "Aqara", "Single Wall Switch H1 CN (no N)", "QBKG27LM"
    ],
    "lumi.switch.l1aeu1": [
        "Aqara", "Single Wall Switch H1 EU (no N)", "WS-EUK01"
    ],
    # "support": 5,
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),
        ButtonMIConv("button", mi="6.e.1", value=1),  # single
        ButtonMIConv("button", mi="6.e.2", value=2),  # double
        Action,
        BoolConv("led", "switch", mi="3.p.1", enabled=False),  # uint8
        MapConv("power_on_state", "select", mi="4.p.1", map=POWEROFF_MEMORY,
                enabled=False),
        BoolConv("wireless", "switch", mi="6.p.1", enabled=False),  # uint8
    ],
}, {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:switch:0000A003:lumi-l2acn1:1
    "lumi.switch.l2acn1": [
        "Aqara", "Double Wall Switch H1 CN (no N)", "QBKG28LM"
    ],
    "lumi.switch.l2aeu1": [
        "Aqara", "Double Wall Switch H1 EU (no N)", "WS-EUK02"
    ],
    # "support": 5,
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        ButtonMIConv("button_1", mi="7.e.1", value=1),  # single
        ButtonMIConv("button_1", mi="7.e.2", value=2),  # double
        ButtonMIConv("button_2", mi="8.e.1", value=1),  # single
        ButtonMIConv("button_2", mi="8.e.2", value=2),  # double
        ButtonMIConv("button_both", mi="9.e.1", value=4),
        Action,
        BoolConv("led", "switch", mi="4.p.1", enabled=False),  # uint8
        MapConv("power_on_state", "select", mi="5.p.1", map=POWEROFF_MEMORY,
                enabled=False),
        BoolConv("wireless_1", "switch", mi="7.p.1", enabled=False),  # uint8
        BoolConv("wireless_2", "switch", mi="8.p.1", enabled=False),  # uint8
    ],
}, {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:switch:0000A003:lumi-n1acn1:1
    "lumi.switch.n1acn1": [
        "Aqara", "Single Wall Switch H1 CN (with N)", "QBKG30LM"
    ],
    "lumi.switch.n1aeu1": [
        "Aqara", "Single Wall Switch H1 EU (with N)", "WS-EUK03"
    ],
    # "support": 5,
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),
        MathConv("energy", "sensor", mi="3.p.1", multiply=0.001, round=2),
        MathConv("power", "sensor", mi="3.p.2", round=2),
        ButtonMIConv("button", mi="7.e.1", value=1),  # single
        ButtonMIConv("button", mi="7.e.2", value=2),  # double
        Action,
        BoolConv("led", "switch", mi="4.p.1", enabled=False),  # uint8
        BoolConv("led_reverse", "switch", mi="4.p.2", enabled=False),  # uint8
        MapConv("power_on_state", "select", mi="5.p.1", map=POWEROFF_MEMORY,
                enabled=False),
        BoolConv("wireless", "switch", mi="7.p.1", enabled=False),  # uint8
    ],
}, {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:switch:0000A003:lumi-n2acn1:1
    "lumi.switch.n2acn1": [
        "Aqara", "Double Wall Switch H1 CN (with N)", "QBKG31LM"
    ],
    "lumi.switch.n2aeu1": [
        "Aqara", "Double Wall Switch H1 EU (with N)", "WS-EUK04"
    ],
    # "support": 5,
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        MathConv("energy", "sensor", mi="4.p.1", multiply=0.001, round=2),
        MathConv("power", "sensor", mi="4.p.2", round=2),
        ButtonMIConv("button_1", mi="8.e.1", value=1),  # single
        ButtonMIConv("button_1", mi="8.e.2", value=2),  # double
        ButtonMIConv("button_2", mi="9.e.1", value=1),  # single
        ButtonMIConv("button_2", mi="9.e.2", value=2),  # double
        ButtonMIConv("button_both", mi="10.e.1", value=4),
        Action,
        BoolConv("led", "switch", mi="5.p.1", enabled=False),  # uint8
        BoolConv("led_reverse", "switch", mi="5.p.2", enabled=False),  # uint8
        MapConv("power_on_state", "select", mi="6.p.1", map=POWEROFF_MEMORY,
                enabled=False),
        BoolConv("wireless_1", "switch", mi="8.p.1", enabled=False),  # uint8
        BoolConv("wireless_2", "switch", mi="9.p.1", enabled=False),  # uint8
    ],
}, {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:switch:0000A003:lumi-l3acn1:1
    "lumi.switch.l3acn1": [
        "Aqara", "Triple Wall Switch H1 CN (no N)", "QBKG29LM"
    ],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        Converter("channel_3", "switch", mi="4.p.1"),
        ButtonMIConv("button_1", mi="8.e.1", value=1),  # single
        ButtonMIConv("button_1", mi="8.e.2", value=2),  # double
        ButtonMIConv("button_2", mi="9.e.1", value=1),  # single
        ButtonMIConv("button_2", mi="9.e.2", value=2),  # double
        ButtonMIConv("button_3", mi="10.e.1", value=1),  # single
        ButtonMIConv("button_3", mi="10.e.2", value=2),  # double
        ButtonMIConv("button_both_12", mi="11.e.1", value=4),
        ButtonMIConv("button_both_13", mi="12.e.1", value=4),
        ButtonMIConv("button_both_23", mi="13.e.1", value=4),
        Action,
        BoolConv("led", "switch", mi="5.p.1", enabled=False),  # uint8
        MapConv("power_on_state", "select", mi="6.p.1", map=POWEROFF_MEMORY,
                enabled=False),
        BoolConv("wireless_1", "switch", mi="8.p.1", enabled=False),  # uint8
        BoolConv("wireless_2", "switch", mi="9.p.1", enabled=False),  # uint8
        BoolConv("wireless_3", "switch", mi="10.p.1", enabled=False),  # uint8
    ]
}, {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:switch:0000A003:lumi-n3acn1:1
    "lumi.switch.n3acn1": [
        "Aqara", "Triple Wall Switch H1 CN (with N)", "QBKG32LM"
    ],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        Converter("channel_3", "switch", mi="4.p.1"),
        MathConv("energy", "sensor", mi="5.p.1", multiply=0.001, round=2),
        MathConv("power", "sensor", mi="5.p.2", round=2),
        ButtonMIConv("button_1", mi="9.e.1", value=1),  # single
        ButtonMIConv("button_1", mi="9.e.2", value=2),  # double
        ButtonMIConv("button_2", mi="10.e.1", value=1),  # single
        ButtonMIConv("button_2", mi="10.e.2", value=2),  # double
        ButtonMIConv("button_3", mi="11.e.1", value=1),  # single
        ButtonMIConv("button_3", mi="11.e.2", value=2),  # double
        ButtonMIConv("button_both_12", mi="12.e.1", value=4),
        ButtonMIConv("button_both_13", mi="13.e.1", value=4),
        ButtonMIConv("button_both_23", mi="14.e.1", value=4),
        Action,
        BoolConv("led", "switch", mi="6.p.1", enabled=False),  # uint8
        BoolConv("led_reverse", "switch", mi="6.p.2", enabled=False),  # uint8
        MapConv("power_on_state", "select", mi="7.p.1", map=POWEROFF_MEMORY,
                enabled=False),
        MapConv("wireless_1", "switch", mi="9.p.1", map=INVERSE),
        MapConv("wireless_2", "switch", mi="10.p.1", map=INVERSE),
        MapConv("wireless_3", "switch", mi="11.p.1", map=INVERSE),
    ]
}, {
    "lumi.remote.b28ac1": ["Aqara", "Double Wall Button H1", "WRS-R02"],
    "spec": [
        Action,
        ButtonMIConv("button_1", mi="3.e.1", value=1),  # single
        ButtonMIConv("button_1", mi="3.e.2", value=2),  # double
        ButtonMIConv("button_1", mi="3.e.3", value=16),  # long
        ButtonMIConv("button_2", mi="4.e.1", value=1),  # single
        ButtonMIConv("button_2", mi="4.e.2", value=2),  # double
        ButtonMIConv("button_2", mi="4.e.3", value=16),  # long
        BatteryConv("battery", "sensor", mi="6.p.2"),  # voltage
        MapConv("battery_low", "binary_sensor", mi="6.p.1", map=BATTERY_LOW,
                enabled=False),
        MapConv("mode", "select", mi="8.p.1", map={
            1: "single_click", 2: "multi_click"
        }, enabled=False)
    ]
}]

################################################################################
# 3rd party zigbee
################################################################################

DEVICES += [{
    # only one attribute with should_poll
    "TS0121": ["BlitzWolf", "Plug", "BW-SHP13"],
    "support": 5,  # @AlexxIT
    "spec": [
        ZOnOffConv("plug", "switch"),
        ZVoltageConv("voltage", "sensor", poll=True),  # once per 60 seconds
        ZCurrentConv("current", "sensor", multiply=0.001),
        ZPowerConv("power", "sensor"),
        ZEnergyConv("energy", "sensor", multiply=0.01),  # once per 5 minutes
        ZTuyaPowerOn,
    ],
}, {
    "TS0115": ["UseeLink", "Power Strip", "SM-SO306E"],
    "support": 5,  # @AlexxIT
    "spec": [
        ZOnOffConv("channel_1", "switch", ep=1),
        ZOnOffConv("channel_2", "switch", ep=2),
        ZOnOffConv("channel_3", "switch", ep=3),
        ZOnOffConv("channel_4", "switch", ep=4),
        ZOnOffConv("usb", "switch", ep=7),
        ZTuyaPowerOn,
    ],
}, {
    # Neo Power Plug NAS-WR01B
    "TS011F": ["Neo", "Power Plug", "NAS-WR01B"],
    "support": 5,
    "spec": [
        ZOnOffConv("plug", "switch"),
        # default gateway software binds electrical_measurement and
        # smartenergy_metering clusters, no need to repeat it
        ZVoltageConv("voltage", "sensor", report="5s 1h 1"),
        ZCurrentConv("current", "sensor", report="5s 1h 1", multiply=0.001),
        ZPowerConv("power", "sensor", report="5s 1h 1"),
        ZEnergyConv("energy", "sensor", report="5s 1h 1", multiply=0.01),
        ZTuyaPowerOnConv("power_on_state", "select", enabled=False),
        ZTuyaLEDModeConv("led", "select", enabled=False),
        ZTuyaChildModeConv("child_mode", "switch", enabled=False),
        ZTuyaPlugModeConv("mode", "select", enabled=False)
    ],
}, {
    # tuya relay with neutral, 1 gang
    "TS0001": ["Tuya", "Relay", "TS0001"],
    "support": 4,
    "spec": [
        ZOnOffConv("switch", "switch", bind=True),
        ZTuyaPowerOn,
    ],
}, {
    # tuya relay with neutral, 2 gang
    "TS0002": ["Tuya", "Relay", "TS0002"],
    "support": 3,  # @zvldz
    "spec": [
        ZOnOffConv("channel_1", "switch", ep=1, bind=True),
        ZOnOffConv("channel_2", "switch", ep=2, bind=True),
        ZTuyaPowerOn,
        ZTuyaPlugModeConv("mode", "select", enabled=False),
    ],
}, {
    # tuya relay with neutral, 3 gang
    "TS0003": ["Tuya", "Relay", "TS0003"],
    "support": 3,
    "spec": [
        ZOnOffConv("channel_1", "switch", ep=1, bind=True),
        ZOnOffConv("channel_2", "switch", ep=2, bind=True),
        ZOnOffConv("channel_3", "switch", ep=3, bind=True),
        ZTuyaPowerOn,
        ZTuyaPlugModeConv("mode", "select", enabled=False),
    ],
}, {
    # tuya relay with neutral, 4 gang
    "TS0004": ["Tuya", "Relay", "TS0004"],
    "support": 3,
    "spec": [
        ZOnOffConv("channel_1", "switch", ep=1, bind=True),
        ZOnOffConv("channel_2", "switch", ep=2, bind=True),
        ZOnOffConv("channel_3", "switch", ep=3, bind=True),
        ZOnOffConv("channel_4", "switch", ep=4, bind=True),
        ZTuyaPowerOn,
        ZTuyaPlugModeConv("mode", "select", enabled=False),
    ],
}, {
    "TS004F": ["Tuya", "Wireless Four Button", "RSH-Zigbee-SC04"],
    "spec": [
        ZTuyaButtonConfig("action", "sensor"),
        ZTuyaButtonConv("button_1", ep=1, bind=True),
        ZTuyaButtonConv("button_2", ep=2, bind=True),
        ZTuyaButtonConv("button_3", ep=3, bind=True),
        ZTuyaButtonConv("button_4", ep=4, bind=True),
        ZBatteryConv("battery", "sensor", bind=True),
        ZTuyaButtonModeConv("mode", "select", enabled=False),
    ],
}, {
    # very simple relays with binding
    "TS0011": ["Tuya", "Single Switch (no N)", "TS0011"],
    "support": 5,
    "spec": [ZOnOffConv("switch", "switch", bind=True)],
}, {
    # very simple 2 gang relays with binding
    "TS0012": ["Tuya", "Double Switch", "TS0012"],
    "support": 5,
    "spec": [
        ZOnOffConv("channel_1", "light", ep=1, bind=True),
        ZOnOffConv("channel_2", "light", ep=2, bind=True),
        ZTuyaPowerOn,
        ZTuyaPlugModeConv("mode", "select", enabled=False),
    ],
}, {
    # very simple relays
    "01MINIZB": ["Sonoff", "Mini", "ZBMINI"],
    "SA-003-Zigbee": ["eWeLink", "Zigbee OnOff Controller", "SA-003-Zigbee"],
    "support": 5,  # @AlexxIT
    "spec": [ZSwitch]
}, {
    "Lamp_01": ["Ksentry Electronics", "OnOff Controller", "KS-SM001"],
    "spec": [
        ZOnOffConv("switch", "switch", ep=11, bind=True, report="0s 1h 0"),
    ]
}, {
    "WB01": ["Sonoff", "Button", "SNZB-01"],
    "support": 5,  # @AlexxIT
    "spec": [
        ZSonoffButtonConv("action", "sensor", bind=True),
        ZBatteryConv("battery", "sensor"),
    ],
}, {
    "MS01": ["Sonoff", "Motion Sensor", "SNZB-03"],
    "support": 5,  # @AlexxIT
    "spec": [
        ZIASZoneConv("occupancy", "binary_sensor"),
        ZBatteryConv("battery", "sensor"),
    ],
}, {
    "TH01": ["Sonoff", "TH Sensor", "SNZB-02"],
    "spec": [
        # temperature, humidity and battery binds by default
        # report config for battery_voltage also by default
        ZTemperatureConv("temperature", "sensor", report="10s 1h 100"),
        ZHumidityConv("humidity", "sensor", report="10s 1h 100"),
        ZBatteryConv("battery", "sensor", report="1h 12h 0"),
    ],
}, {
    # wrong zigbee model, some devices have model TH01 (ewelink bug)
    "DS01": ["Sonoff", "Door/Window Sensor", "SNZB-04"],
    "support": 5,
    "spec": [
        ZIASZoneConv("contact", "binary_sensor"),
        ZBatteryConv("battery", "sensor"),
    ],
}, {
    "SML001": ["Philips", "Hue motion sensor", "9290012607"],
    "support": 4,  # @AlexxIT TODO: sensitivity, led
    "spec": [
        ZOccupancyConv(
            "occupancy", "binary_sensor", ep=2, bind=True, report="0s 1h 0"
        ),
        ZIlluminanceConv(
            "illuminance", "sensor", ep=2, bind=True, report="10s 1h 5"
        ),
        ZTemperatureConv(
            "temperature", "sensor", ep=2, bind=True, report="10s 1h 100"
        ),
        ZBatteryConv("battery", "sensor", ep=2, bind=True, report="1h 12h 0"),
        ZOccupancyTimeoutConv(
            "occupancy_timeout", "number", ep=2, enabled=False
        ),
    ],
}, {
    "LWB010": ["Philips", "Hue white 806 lm", "9290011370B"],
    "support": 2,  # TODO: state change, effect?
    "spec": [
        ZOnOffConv("light", "light", ep=11),
        ZBrightnessConv("brightness", parent="light", ep=11),
    ],
}, {
    "LCT001": ["Philips", "Hue Color 600 lm", "9290012573A"],
    "support": 2,  # TODO: state change, effect?
    "spec": [
        ZOnOffConv("light", "light", ep=11),
        ZBrightnessConv("brightness", parent="light", ep=11),
        ZColorTempConv("color_temp", parent="light", ep=11),
    ],
}, {
    "RWL021": ["Philips", "Hue dimmer switch", "324131137411"],
    "support": 2,  # TODO: multiple clicks, tests
    "spec": [
        ZHueDimmerOnConv("action", "sensor", bind=True),
        ZHueDimmerLevelConv("action", bind=True),
        # ZBindConf("power", 64512, ep=2),
    ],
}, {
    "FNB56-ZSC01LX1.2": ["Unknown", "Dimmer", "LXZ8-02A"],
    "TRADFRI bulb E27 W opal 1000lm": [
        "IKEA", "Bulb E27 1000 lm", "LED1623G12"
    ],
    "TRADFRI bulb E27 WW 806lm": ["IKEA", "Bulb E27 806 lm", "LED1836G9"],
    "support": 3,  # @AlexxIT TODO: tests, effect?
    "spec": [
        ZOnOffConv("light", "light"),
        ZBrightnessConv("brightness", parent="light"),
    ],
}, {
    "TRADFRI bulb E14 WS opal 600lm": [
        "IKEA", "Bulb E14 WS opal 600lm", "LED1738G7"
    ],
    "spec": [
        ZOnOffConv("light", "light"),
        ZXiaomiBrightnessConv("brightness", parent="light"),
        ZXiaomiColorTempConv("color_temp", parent="light")
    ],
}, {
    "TRADFRI remote control": [
        "IKEA", "TRADFRI remote control", "E1524/E1810"
    ],
    "support": 1,
    "spec": [
        IKEARemoteConv1("action", "sensor", bind=True),
        IKEARemoteConv2("action"),
    ],
}, {
    "default": "zigbee",  # default zigbee device
    "spec": [
        ZOnOffConv("switch", "switch", ep=1, enabled=None, bind=True),
        ZOnOffConv("channel_2", "switch", ep=2, enabled=None),
        ZOnOffConv("channel_3", "switch", ep=3, enabled=None),
        ZOnOffConv("channel_4", "switch", ep=4, enabled=None),
    ],
}]

################################################################################
# BLE
################################################################################

# https://custom-components.github.io/ble_monitor/by_brand
DEVICES += [{
    152: ["Xiaomi", "Flower Care", "HHCCJCY01"],
    "spec": [
        MiBeacon, BLETemperature, BLEMoisture, BLEConductivity, BLEIlluminance,
        Converter("battery", "sensor", enabled=None),  # no in new firmwares
    ],
    "ttl": "1m",  # new data every 10 seconds
}, {
    349: ["Xiaomi", "Flower Pot", "HHCCPOT002"],
    "spec": [
        MiBeacon, BLEMoisture, BLEConductivity,
        Converter("battery", "sensor", enabled=None),  # no in new firmwares
    ],
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
    4611: ["Xiaomi", "TH Sensor", "XMWSDJ04MMC"],
    "spec": [
        MiBeacon, BLETemperature, BLEHumidity,
        Converter("battery", "sensor", enabled=None),  # no in new firmwares
    ],
}, {
    2038: ["Xiaomi", "Night Light 2", "MJYD02YL-A"],  # 15,4103,4106,4119,4120
    "spec": [
        MiBeacon, BLEBattery, BLELight, BLEMotion,
        Converter("idle_time", "sensor", enabled=False)
    ],
}, {
    131: ["Xiaomi", "Kettle", "YM-K1501"],  # CH, HK, RU version
    275: ["Xiaomi", "Kettle", "YM-K1501"],  # international
    1116: ["Xiaomi", "Viomi Kettle", "V-SK152"],  # international
    "spec": [MiBeacon, BLEPower, BLETemperature],
    "ttl": "12h",
}, {
    1249: ["Xiaomi", "Magic Cube", "XMMF01JQD"],
    "spec": [MiBeacon, Action],
    "ttl": "7d",  # don't send any data
}, {
    # logs: https://github.com/AlexxIT/XiaomiGateway3/issues/180
    2701: ["Xiaomi", "Motion Sensor 2", "RTCGQ02LM"],  # 15,4119,4120
    "spec": [
        MiBeacon, BLEMotion, BLELight, BLEBattery,
        Converter("action", "sensor", enabled=False),
        Converter("idle_time", "sensor", enabled=False),
    ],
}, {
    2691: ["Xiaomi", "Qingping Motion Sensor", "CGPR1"],
    "spec": [
        MiBeacon, BLEMotion, BLELight, BLEIlluminance, BLEBattery,
        Converter("idle_time", "sensor", enabled=False),
    ],
    "ttl": "34m",  # battery every 11 min
}, {
    1983: ["Yeelight", "Button S1", "YLAI003"],
    "spec": [MiBeacon, BLEAction, BLEBattery],
    "ttl": "16m",  # battery every 5 min
}, {
    2443: ["Xiaomi", "Door/Window Sensor 2", "MCCGQ02HL"],
    "spec": [
        MiBeacon, BLEContact, BLELight, BLEBattery,
    ],
    "ttl": "3d",  # battery every 1 day
}, {
    2455: ["Honeywell", "Smoke Alarm", "JTYJ-GD-03MI"],
    "spec": [MiBeacon, BLEAction, BLESmoke, BLEBattery],
    "ttl": "15m",  # battery every 4:30 min
}, {
    2147: ["Xiaomi", "Water Leak Sensor", "SJWS01LM"],
    "spec": [
        MiBeacon, BLEWaterLeak, BLEBattery,
        Converter("action", "sensor", enabled=False),
    ],
    "ttl": "725m"  # battery every 4 hour
}, {
    # BLE devices can be supported witout spec. New spec will be added
    # "on the fly" when device sends them. But better to rewrite right spec for
    # each device
    "default": "ble",  # default BLE device
    794: ["Xiaomi", "Door Lock", "MJZNMS02LM"],
    955: ["Unknown", "Lock M2", "ydhome.lock.m2silver"],
    982: ["Xiaomi", "Qingping Door Sensor", "CGH1"],
    1034: ["Xiaomi", "Mosquito Repellent", "WX08ZM"],
    1161: ["Xiaomi", "Toothbrush T500", "MES601"],
    1433: ["Xiaomi", "Door Lock", "MJZNMS03LM"],
    1694: ["Aqara", "Door Lock N100 (Bluetooth)", "ZNMS16LM"],
    1695: ["Aqara", "Door Lock N200", "ZNMS17LM"],
    2444: ["Xiaomi", "Door Lock", "XMZNMST02YD"],
    2480: ["Xiaomi", "Safe Box", "BGX-5/X1-3001"],
    3051: ["Aqara", "Door Lock D100", "ZNMS20LM"],
    3343: ["Loock", "Door Lock Classic 2X Pro", "loock.lock.cc2xpro"],
    "spec": [
        MiBeacon,
        # sensors:
        Converter("action", "sensor", enabled=None),
        Converter("battery", "sensor", enabled=None),
        Converter("conductivity", "sensor", enabled=None),
        Converter("formaldehyde", "sensor", enabled=None),
        Converter("humidity", "sensor", enabled=None),
        Converter("idle_time", "sensor", enabled=None),
        Converter("illuminance", "sensor", enabled=None),
        Converter("moisture", "sensor", enabled=None),
        Converter("rssi", "sensor", enabled=None),
        Converter("supply", "sensor", enabled=None),
        Converter("temperature", "sensor", enabled=None),
        # binary_sensors:
        Converter("contact", "binary_sensor", enabled=None),
        Converter("gas", "binary_sensor", enabled=None),
        Converter("light", "binary_sensor", enabled=None),
        Converter("lock", "binary_sensor", enabled=None),
        Converter("motion", "binary_sensor", enabled=None),
        Converter("opening", "binary_sensor", enabled=None),
        Converter("sleep", "binary_sensor", enabled=None),
        Converter("smoke", "binary_sensor", enabled=None),
        Converter("water_leak", "binary_sensor", enabled=None),
    ],
}]

################################################################################
# Mesh
################################################################################

DEVICES += [{
    # brightness 1..65535, color_temp 2700..6500
    948: ["Yeelight", "Mesh Downlight", "YLSD01YL"],  # flex
    995: ["Yeelight", "Mesh Bulb E14", "YLDP09YL"],  # flex
    996: ["Yeelight", "Mesh Bulb E27", "YLDP10YL"],  # flex
    997: ["Yeelight", "Mesh Spotlight", "YLSD04YL"],  # flex
    1771: ["Xiaomi", "Mesh Bulb", "MJDP09YL"],  # flex
    1772: ["Xiaomi", "Mesh Downlight", "MJTS01YL/MJTS003"],  # flex
    3291: ["Yeelight", "Mesh Downlight M1", "YLSD001"],  # flex
    2076: ["Yeelight", "Mesh Downlight M2", "YLTS02YL/YLTS04YL"],  # flex
    2342: ["Yeelight", "Mesh Bulb M2", "YLDP25YL/YLDP26YL"],  # flex
    "support": 4,  # @AlexxIT TODO: power_on_state values
    "spec": [
        Converter("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", parent="light", max=65535),
        ColorTempKelvin("color_temp", mi="2.p.3", parent="light"),
        BoolConv("flex_switch", "switch", mi="3.p.5", enabled=False),  # uint8
        BoolConv("power_on_state", "switch", mi="3.p.11", enabled=False),
    ],
}, {
    # brightness 1..65535, color_temp 2700..6500
    1054: ["Xiaomi", "Mesh Group", "yeelink.light.mb1grp"],
    "support": 4,  # @AlexxIT TODO: check if support flex and power on
    "spec": [
        Converter("group", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", parent="light", max=65535),
        ColorTempKelvin("color_temp", mi="2.p.3", parent="light"),
    ]
}, {
    # brightness 1..100, color_temp 2700..6500
    3416: ["PTX", "Mesh Downlight", "090615.light.mlig01"],
    "spec": [
        Converter("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", parent="light", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", parent="light"),
    ]
}, {
    # brightness 1..100, color_temp 3000..6400
    1910: ["LeMesh", "Mesh Light (RF ready)", "lemesh.light.wy0c02"],
    2293: ["Unknown", "Mesh Lightstrip (RF ready)", "crzm.light.wy0a01"],
    2351: ["LeMesh", "Mesh Downlight", "lemesh.light.wy0c05"],
    2584: ["XinGuang", "Smart Light", "LIBMDA09X"],
    3164: ["LeMesh", "Mesh Light (RF ready)", "lemesh.light.wy0c07"],
    3531: ["LeMesh", "Mesh Light", "lemesh.light.wy0c08"],
    "spec": [
        Converter("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", parent="light", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", parent="light",
                        mink=3000, maxk=6400),
    ]
}, {
    1945: ["Xiaomi", "Mesh Wall Switch", "DHKG01ZM"],
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),
        Converter("led", "switch", mi="10.p.1", enabled=False),
    ],
}, {
    2007: ["Unknown", "Mesh Switch Controller", "lemesh.switch.sw0a01"],
    3150: ["XinGuang", "Mesh Switch", "wainft.switch.sw0a01"],
    3169: ["Unknown", "Mesh Switch Controller", "lemesh.switch.sw0a02"],
    4252: ["Unknown", "Mesh Switch", "dwdz.switch.sw0a01"],
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),
    ],
}, {
    2258: ["PTX", "Mesh Single Wall Switch", "PTX-SK1M"],
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),
        BoolConv("led", "switch", mi="8.p.1", enabled=False),
        BoolConv("wireless", "switch", mi="8.p.2", enabled=False),
    ],
}, {
    # Mesh Switches
    1946: ["Xiaomi", "Mesh Double Wall Switch", "DHKG02ZM"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        Converter("led", "switch", mi="10.p.1", enabled=False),
        BoolConv("wireless_1", "switch", mi="2.p.2", enabled=False),
        BoolConv("wireless_2", "switch", mi="3.p.2", enabled=False),
        Converter("action", "sensor", enabled=False),
        ButtonMIConv("button_1", mi="8.e.1", value=1),  # single
        ButtonMIConv("button_2", mi="9.e.1", value=1),  # single
    ],
}, {
    2257: ["PTX", "Mesh Double Wall Switch", "PTX-SK2M"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        BoolConv("led", "switch", mi="8.p.1", enabled=False),
        BoolConv("wireless_1", "switch", mi="8.p.2", enabled=False),
        BoolConv("wireless_2", "switch", mi="8.p.3", enabled=False),
    ],
}, {
    # https://www.ixbt.com/live/chome/umnaya-rozetka-xiaomi-zncz01zm-s-energomonitoringom-i-bluetooth-mesh-integraciya-v-home-assistant.html
    3083: ["Xiaomi", "Electrical Outlet", "ZNCZ01ZM"],
    "spec": [
        Converter("outlet", "switch", mi="2.p.1"),
        MathConv("power", "sensor", mi="3.p.1", multiply=0.01),
        Converter("led", "switch", mi="4.p.1", enabled=False),
        Converter("power_protect", "switch", mi="7.p.1", enabled=False),
        MathConv("power_value", "number", mi="7.p.2", multiply=0.01,
                 min=0, max=1638400, enabled=False),
    ],
}, {
    2093: ["PTX", "Mesh Triple Wall Switch", "PTX-TK3/M"],
    3878: ["PTX", "Mesh Triple Wall Switch", "PTX-SK3M"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        Converter("channel_3", "switch", mi="4.p.1"),
        BoolConv("led", "switch", mi="8.p.1", enabled=False),
        BoolConv("wireless_1", "switch", mi="8.p.2", enabled=False),
        BoolConv("wireless_2", "switch", mi="8.p.3", enabled=False),
        BoolConv("wireless_3", "switch", mi="8.p.4", enabled=False),
    ],
}, {
    2715: ["Xiaomi", "Mesh Single Wall Switch", "ZNKG01HL"],
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),
        MathConv("humidity", "sensor", mi="6.p.1", round=2),
        MathConv("temperature", "sensor", mi="6.p.7", round=2),
        BoolConv("wireless", "switch", mi="2.p.2", enabled=False),
        Converter("baby_mode", "switch", mi="11.p.1", enabled=False),
    ]
}, {
    2716: ["Xiaomi", "Mesh Double Wall Switch", "ZNKG02HL"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        MathConv("humidity", "sensor", mi="6.p.1", round=2),
        MathConv("temperature", "sensor", mi="6.p.7", round=2),
        BoolConv("wireless_1", "switch", mi="2.p.2", enabled=False),
        BoolConv("wireless_2", "switch", mi="3.p.2", enabled=False),
        Converter("baby_mode", "switch", mi="11.p.1", enabled=False),
    ]
}, {
    2717: ["Xiaomi", "Mesh Triple Wall Switch", "ZNKG03HL/ISA-KG03HL"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        Converter("channel_3", "switch", mi="4.p.1"),
        MathConv("humidity", "sensor", mi="6.p.1", round=2),
        MathConv("temperature", "sensor", mi="6.p.7", round=2),
        BoolConv("wireless_1", "switch", mi="2.p.2", enabled=False),
        BoolConv("wireless_2", "switch", mi="3.p.2", enabled=False),
        BoolConv("wireless_3", "switch", mi="4.p.2", enabled=False),
        Converter("baby_mode", "switch", mi="11.p.1", enabled=False),
    ],
}, {
    4160: ["Xiaomi", "Mosquito Repeller 2", "WX10ZM"],
    # "support": 5,  # @AlexxIT need some tests
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),  # bool
        Converter("battery", "sensor", mi="3.p.1"),  # percentage 0-100
        Converter("supply", "sensor", mi="4.p.1"),  # percentage 0-100
        Converter("led", "switch", mi="9.p.1", enabled=False),  # bool
        MapConv("power_mode", "select", mi="2.p.2", map={
            0: "auto", 1: "battery", 2: "usb"
        }, enabled=False)
    ],
}, {
    # urn:miot-spec-v2:device:light:0000A001:yeelink-nl2:1:0000C81D 米家智能光感夜灯
    4736: ["Xiaomi", "Mesh Night Light", "MJYD05YL"],
    "spec": [
        Converter("switch", "light", mi="2.p.1"),  # bool
        BoolConv("light", "binary_sensor", mi="3.p.1")  # uint8 0-Dark 1-Bright
    ],
}, {
    3129: ["Xiaomi", "Smart Curtain Motor", "MJSGCLBL01LM"],
    "spec": [
        MapConv("motor", "cover", mi="2.p.1", map={
            0: "stop", 1: "open", 2: "close"
        }),
        Converter("target_position", mi="2.p.2"),
        CurtainPosConv("position", mi="2.p.6", parent="motor"),
        MapConv("run_state", mi="2.p.3", parent="motor", map={
            0: "stop", 1: "opening", 2: "closing"
        }),
        Converter("battery", "sensor", mi="5.p.1"),  # percent
        Converter("motor_reverse", "switch", mi="2.p.5", enabled=False),
        MapConv("battery_charging", "binary_sensor", mi="5.p.2", map={
            1: True, 2: False, 3: False,
        }, enabled=False),
        BoolConv("light", "binary_sensor", mi="3.p.11")
    ],
}, {
    "default": "mesh",  # default Mesh device
    "spec": [
        Converter("switch", "switch", mi="2.p.1", enabled=None),  # bool
    ],
}]
