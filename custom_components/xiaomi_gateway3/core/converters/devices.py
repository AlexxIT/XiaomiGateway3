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
- domain - optional, hass entity type (`sensor`, `switch`, `binary_sensor`...)
- mi - optional, item name in Lumi spec (`8.0.2012`) or MIoT spec (`2.p.1`)
- enabled - optional, default True:
   - True - entity will be enabled on first setup
   - False - entity and converter! will be disabled on first setup
   - None - converter will be enabled, but entity will be setup with first data

Old Zigbee devices uses Lumi format, new Zigbee 3 and Mesh devices uses MIoT format.
MIoT can be `siid.property.piid` or `siid.event.piid`.

Converter may have different types:

- Converter - default, don't change/convert value
- BoolConv - converts int to bool on decode and bool to int on encode
- MapConv - translate value using mapping: `{0: "disarmed", 1: "armed_home"}`
- MathConv - support multiply, round value and min/max borders
- BrightnessConv - converts `0..<max>` to `0..255`, support set `max` value
- and many others...

For MIoT bool properties you should use `Converter`. For MIoT uint8 properties you
should use `BoolConv`.

By default, the entity is updated only if the decoded payload has its attribute. But one
entity can process multiple attributes, example bulb: `light`, `brightness`,
`color_temp`. In this case you should set `parent` attribute name:

    BoolConv("light", "light", "4.1.85")
    BrightnessConv("brightness", mi="14.1.85", parent="light")
    Converter("color_temp", mi="14.2.85", parent="light")

Another case: one converter may generate multiple attributes, so you should set `childs`
for it. By default, `sensor` and `binary_sensor` with childs will adds its values to its
attributes.

If converter has `enabled=None` - it will work, but entity will setup only with first
data from device. Useful if we don't know exact spec of device. Example, battery not
exist on some firmwares of some devices.

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

Support level should be set only for confirmed devices. For theoretically supported it
should be empty. For unsupported it should be less than 3.

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

# Black formatter (https://black.readthedocs.io/) max-line-length = 88
# fmt: off

########################################################################################
# Gateways
########################################################################################

DEVICES = [{
    "lumi.gateway.mgl03": ["Xiaomi", "Multimode Gateway", "ZNDMWG03LM"],
    "support": 4,  # @AlexxIT TODO: cloud link
    "spec": [
        # write pair=60 => report discovered_mac => report 8.0.2166? =>
        # write pair_command => report added_device => write pair=0
        MapConv("pair", mi="8.0.2109", map={60: True, 0: False}, parent="data"),
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

        Converter("command", "select", parent="data"),
        Converter("data", "select"),

        BoolConv("led", "switch", mi="6.p.6", enabled=False),

        GatewayStats,

        # Converter("device_model", mi="8.0.2103"),  # very rare
        # ConstConv("pair", mi="8.0.2081", value=False),  # legacy pairing_stop
    ],
}, {
    "lumi.gateway.aqcn02": ["Aqara", "Hub E1 CN", "ZHWG16LM"],
    "lumi.gateway.aqcn03": ["Aqara", "Hub E1 EU", "HE1-G01"],
    "lumi.gateway.mcn001": ["Xiaomi", "Multimode Gateway 2 CN", "DMWG03LM"],
    "lumi.gateway.mgl001": ["Xiaomi", "Multimode Gateway 2 EU", "ZNDMWG04LM"],
    "support": 3,  # @AlexxIT
    "spec": [
        MapConv("pair", mi="8.0.2109", map={60: True, 0: False}, parent="data"),

        Converter("discovered_mac", mi="8.0.2110", parent="data"),
        Converter("pair_command", mi="8.0.2111", parent="data"),
        Converter("added_device", mi="8.0.2084", parent="data"),
        RemoveDIDConv("remove_did", mi="8.0.2082", parent="data"),

        # also updated from child devices OTAConv
        Converter("ota_progress", parent="data"),

        # support change with remote.send_command
        Converter("power_tx", mi="8.0.2012"),
        Converter("channel", mi="8.0.2024"),

        Converter("command", "select", parent="data"),
        Converter("data", "select"),

        GatewayStats
    ],
}]

########################################################################################
# Zigbee
########################################################################################

DEVICES += [{
    # don"t work: protect 8.0.2014, power 8.0.2015, plug_detection 8.0.2044
    "lumi.plug": ["Xiaomi", "Plug CN", "ZNCZ02LM"],  # tested
    "lumi.plug.mitw01": ["Xiaomi", "Plug TW", "ZNCZ03LM"],
    "lumi.plug.maus01": ["Xiaomi", "Plug US", "ZNCZ12LM"],
    "support": 5,  # @AlexxIT
    "spec": [
        Plug, Power, Energy, ChipTemp, PowerOffMemory, ChargeProtect, Led,
        # Converter("max_power", "sensor", mi="8.0.2042", enabled=False),
    ],
}, {
    "lumi.plug.mmeu01": ["Xiaomi", "Plug EU", "ZNCZ04LM"],
    "spec": [
        Plug, Power, Voltage, Energy, ChipTemp,
        BoolConv("plug_detection", "binary_sensor", mi="8.0.2044"),
        MapConv("power_on_state", "select", mi="8.0.2030", map=POWEROFF_MEMORY, enabled=False),
    ],
}, {
    "lumi.ctrl_86plug.aq1": ["Aqara", "Wall Outlet", "QBCZ11LM"],
    "lumi.ctrl_86plug": ["Aqara", "Wall Outlet", "QBCZ11LM"],
    "spec": [
        Outlet, Power, Energy, ChipTemp, PowerOffMemory, ChargeProtect, Led, Wireless,
    ],
}, {
    "lumi.ctrl_ln1.aq1": ["Aqara", "Single Wall Switch", "QBKG11LM"],
    "lumi.ctrl_ln1": ["Aqara", "Single Wall Switch", "QBKG11LM"],
    "lumi.switch.b1nacn02": ["Aqara", "Single Wall Switch D1 CN (with N)", "QBKG23LM"],
    "spec": [Switch, Power, Energy, Action, Button, Wireless, Led],
}, {
    "lumi.ctrl_neutral1": ["Aqara", "Single Wall Switch", "QBKG04LM"],
    "lumi.switch.b1lacn02": ["Aqara", "Single Wall Switch D1 CN (no N)", "QBKG21LM"],
    "spec": [Switch, Action, Button, Wireless, Led],
}, {
    # dual channel on/off, power measurement
    "lumi.ctrl_ln2.aq1": ["Aqara", "Double Wall Switch", "QBKG12LM"],
    "lumi.ctrl_ln2": ["Aqara", "Double Wall Switch", "QBKG12LM"],
    "lumi.switch.b2nacn02": ["Aqara", "Double Wall Switch D1 CN (with N)", "QBKG24LM"],
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
    "lumi.switch.b2lacn02": ["Aqara", "Double Wall Switch D1 CN (no N)", "QBKG22LM"],
    "spec": [
        Channel1, Channel2, Action, Button1, Button2, ButtonBoth,
        Wireless1, Wireless2, Led,
    ]
}, {
    # triple channel on/off, no neutral wire
    "lumi.switch.l3acn3": ["Aqara", "Triple Wall Switch D1 CN (no N)", "QBKG25LM"],
    "spec": [
        Channel1, Channel2, Channel3,
        Action, Button1, Button2, Button3, Button12, Button13, Button23,
        Wireless1, Wireless2, Wireless3, PowerOffMemory, Led,
    ],
}, {
    # with neutral wire, thanks @Mantoui
    "lumi.switch.n3acn3": ["Aqara", "Triple Wall Switch D1 CN (with N)", "QBKG26LM"],
    "spec": [
        Channel1, Channel2, Channel3, Power, Voltage, Energy,
        Action, Button1, Button2, Button3, Button12, Button13, Button23,
        Wireless1, Wireless2, Wireless3, PowerOffMemory, Led,
    ],
}, {
    # we are using lumi+zigbee converters for support heartbeats and transition
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
        Action, Button1, Button2, ButtonBoth, Battery, BatteryLow, BatteryOrig, ChipTemp
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
    # motion sensor E1 with illuminance
    "lumi.motion.acn001": ["Aqara", "Motion Sensor E1", "RTCGQ15LM"],
    "spec": [
        EventConv("motion", "binary_sensor", mi="2.e.1", value=True),
        Converter("illuminance", "sensor", mi="2.p.1"),
        BatteryConv("battery", "sensor", mi="3.p.2"),  # voltage, mV
        MapConv("battery_low", "binary_sensor", mi="3.p.1", map=BATTERY_LOW,
                enabled=False)
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
        LockActionConv("method", mi="13.15.85", map={1: "fingerprint", 2: "password"}),
        LockActionConv("error", mi="13.4.85", map={
            1: "Wrong password", 2: "Wrong fingerprint"
        }),
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
        MapConv("hvac_mode", mi="14.8.85", map={0: "heat", 1: "cool", 15: "off"}),
        MapConv("fan_mode", mi="14.10.85", map={
            0: "low", 1: "medium", 2: "high", 3: "auto"
        }),
        ClimateTempConv("target_temp", mi="14.9.85"),
    ],
}, {
    "lumi.airrtc.agl001": ["Aqara", "Thermostat E1", "SRTS-A01"],
    "spec": [
        # https://home.miot-spec.com/spec/lumi.airrtc.agl001
        # The following code is very different to the spec defined in home.miot-spec.com
        # thus leave unmodified
        BoolConv("climate", "climate", mi="4.21.85"),
        # 0: Manual module 1: Smart schedule mode 2: Antifreeze mode 3: Installation mode
        MapConv("mode", mi="14.51.85", parent="climate", map={0: "heat", 2: "auto"}),
        MathConv("current_temp", mi="0.1.85", multiply=0.01, parent="climate"),
        MathConv("target_temp", mi="1.8.85", multiply=0.01, parent="climate"),
        MathConv("antifreeze_temp", "number", mi="1.10.85", multiply=0.01, min=5,
                 max=15),
        BoolConv("window_detection", "switch", mi="4.24.85", enabled=False),
        BoolConv("valve_calibration", "switch", mi="4.22.85", enabled=False),
        BoolConv("valve_notification", "switch", mi="4.25.85", enabled=False),
        BoolConv("child_lock", "switch", mi="4.26.85", enabled=False),
        MapConv("find_device", "switch", mi="8.0.2096", map={2: True, 1: False},
                enabled=False),
        Converter("battery", "sensor", mi="8.0.2001"),
        ChipTemp,
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
    "lumi.sen_ill.agl01": ["Aqara", "Light Sensor CN", "GZCGQ11LM"],
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
    "lumi.flood.acn001": ["Aqara", "Water Leak Sensor E1", "SJCGQ13LM"],
    "spec": [
        Converter("moisture", "binary_sensor", mi="2.p.1"),  # bool
        BatteryConv("battery", "sensor", mi="3.p.2"),  # voltage, mV
        MapConv("battery_low", "binary_sensor", mi="3.p.1", map=BATTERY_LOW,
                enabled=False)
    ]
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
        EventConv("motion", "binary_sensor", mi="4.e.1", value=True),
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
    "lumi.airmonitor.acn01": ["Aqara", "Air Quality Monitor CN", "VOCKQJK11LM"],
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
        MapConv("motor", "cover", mi="2.p.2", map={0: "stop", 1: "close", 2: "open"}),
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
    # https://github.com/niceboygithub/AqaraGateway/pull/118/files
    "lumi.remote.acn007": ["Aqara", "Single Wall Button E1", "WXKG20LM"],
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
        MapConv("mode", "select", mi="5.p.1", map={1: "speed", 2: "multi"},
                enabled=False),
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
        MapConv("power_on_state", "select", mi="4.p.1", map=POWEROFF_MEMORY,
                enabled=False),
        MapConv("mode", "select", mi="6.p.2", map={1: "toggle", 2: "momentary"},
                enabled=False),
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
        MapConv("mode", "select", mi="7.p.2", map={1: "toggle", 2: "momentary"},
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
        MapConv("power_on_state", "select", mi="5.p.1", map=POWEROFF_MEMORY, enabled=False),
    ],
}, {
    "lumi.switch.b1lc04": ["Aqara", "Single Wall Switch E1 (no N)", "QBKG38LM"],
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
    "lumi.switch.b2lc04": ["Aqara", "Double Wall Switch E1 (no N)", "QBKG39LM"],
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
    "lumi.switch.b1nc01": ["Aqara", "Single Wall Switch E1 (with N)", "QBKG40LM"],
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
    "lumi.switch.b2nc01": ["Aqara", "Double Wall Switch E1 (with N)", "QBKG41LM"],
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
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:switch:0000A003:lumi-acn040:1
    "lumi.switch.acn040": ["Aqara", "Triple Wall Switch E1 (with N)", "ZNQBKG31LM"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        Converter("channel_3", "switch", mi="4.p.1"),

        # Button press actions
        Action,
        ButtonMIConv("button_1", mi="9.e.1", value=1),  # single
        ButtonMIConv("button_1", mi="9.e.2", value=2),  # double
        ButtonMIConv("button_2", mi="10.e.1", value=1),  # single
        ButtonMIConv("button_2", mi="10.e.2", value=2),  # double
        ButtonMIConv("button_3", mi="11.e.1", value=1),  # single
        ButtonMIConv("button_3", mi="11.e.2", value=2),  # double
        ButtonMIConv("button_both_12", mi="12.e.1", value=4),
        ButtonMIConv("button_both_13", mi="13.e.1", value=4),
        ButtonMIConv("button_both_23", mi="14.e.1", value=4),

        # Wireless switch
        # Native false = Wireless, Native true = Relay
        MapConv("wireless_1", "switch", mi="9.p.1", map={0: True, 1: False},
                enabled=False),
        MapConv("wireless_2", "switch", mi="10.p.1", map={0: True, 1: False},
                enabled=False),
        MapConv("wireless_3", "switch", mi="11.p.1", map={0: True, 1: False},
                enabled=False),

        # Others
        MapConv("power_on_state", "select", mi="7.p.1", map=POWEROFF_MEMORY,
                enabled=False),
        MapConv("temperature_alarm", "sensor", mi="8.p.1",
                map={0: "normal", 1: "protected", 2: "abnormal"}),

        # LED control
        BoolConv("led_inverted", "switch", mi="6.p.2", enabled=False),
        BoolConv("led_dnd", "switch", mi="6.p.1", enabled=False),
        AqaraTimePatternConv("led_dnd_time", "text", mi="6.p.3", enabled=False)
    ]
}, {
    # required switch firmware 0.0.0_0030
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:switch:0000A003:lumi-b2naus01:1
    "lumi.switch.b2naus01": ["Aqara", "Double Wall Switch US (with N)", "WS-USC04"],
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
    "lumi.switch.l1acn1": ["Aqara", "Single Wall Switch H1 CN (no N)", "QBKG27LM"],
    "lumi.switch.l1aeu1": ["Aqara", "Single Wall Switch H1 EU (no N)", "WS-EUK01"],
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
    "lumi.switch.l2acn1": ["Aqara", "Double Wall Switch H1 CN (no N)", "QBKG28LM"],
    "lumi.switch.l2aeu1": ["Aqara", "Double Wall Switch H1 EU (no N)", "WS-EUK02"],
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
    "lumi.switch.n1acn1": ["Aqara", "Single Wall Switch H1 CN (with N)", "QBKG30LM"],
    "lumi.switch.n1aeu1": ["Aqara", "Single Wall Switch H1 EU (with N)", "WS-EUK03"],
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
    "lumi.switch.n2acn1": ["Aqara", "Double Wall Switch H1 CN (with N)", "QBKG31LM"],
    "lumi.switch.n2aeu1": ["Aqara", "Double Wall Switch H1 EU (with N)", "WS-EUK04"],
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
    "lumi.switch.l3acn1": ["Aqara", "Triple Wall Switch H1 CN (no N)", "QBKG29LM"],
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
    "lumi.switch.n3acn1": ["Aqara", "Triple Wall Switch H1 CN (with N)", "QBKG32LM"],
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
}, {
    "lumi.sensor_smoke.acn03": ["Aqara", "Smoke Sensor", "JY-GZ-01AQ"],
    "spec": [
        BoolConv("smoke", "binary_sensor", mi="2.p.1"),
        BoolConv("problem", "binary_sensor", mi="2.p.2", enabled=False),
        Converter("smoke_density", "sensor", mi="2.p.3"),
        MapConv("battery_low", "binary_sensor", mi="3.p.1", map=BATTERY_LOW,
                enabled=False),
        Converter("battery_voltage", "sensor", mi="3.p.2", enabled=False),
        BoolConv("led", "switch", mi="5.p.1", enabled=False),  # uint8
    ]
}, {
    # https://github.com/AlexxIT/XiaomiGateway3/issues/865
    "lumi.sensor_gas.acn02": ["Aqara", "Gas Sensor", "JT-BZ-01AQ/A"],
    "spec": [
        MapConv("status", "sensor", mi="2.p.1", map={
            0: "Normal Monitoring", 1: "Alarm", 2: "Fault", 3: "Warm Up",
            4: "End Of Life"
        }),
        BoolConv("fault", "binary_sensor", mi="2.p.2"),
        Converter("gas_density", "sensor", mi="2.p.3"),  # percentage
        MapConv("sensitivity", "select", mi="5.p.1", map={
            1: "LEL15", 2: "LEL10"
        }, enabled=False),
        Converter("remain_days", "sensor", mi="9.p.1"),
    ],
}, {
    "lumi.light.acn014": ["Aqara", "Bulb T1", "ZNLDP14LM"],
    "spec": [
        Converter("light", "light", mi="2.p.1"),
        # BrightnessConv("brightness", mi="2.p.2", parent="light"),
        # ColorTempKelvin("color_temp", mi="2.p.3", parent="light"),
        ZXiaomiBrightnessConv("brightness", mi="2.p.2", parent="light"),
        ZXiaomiColorTempConv("color_temp", mi="2.p.3", parent="light"),
    ],
}, {
    "lumi.remote.b1acn02": ["Aqara", "Button", "WXKG13LM"],
    "spec": [
        Action,
        ButtonMIConv("button", mi="3.e.1", value=1),  # single
        ButtonMIConv("button", mi="3.e.2", value=2),  # double
        ButtonMIConv("button", mi="3.e.3", value=16),  # long
        BatteryConv("battery", "sensor", mi="2.p.1"),  # voltage
        MapConv("battery_low", "binary_sensor", mi="4.p.1", map=BATTERY_LOW, enabled=False)
    ]
}, {
    # https://home.miot-spec.com/spec/lumi.light.acn003
    "lumi.light.acn003": ["Aqara", "L1-350 Ceiling Light", "ZNXDD01LM"],
    "spec": [
        Converter("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", parent="light"),
        ColorTempKelvin("color_temp", mi="2.p.3", parent="light"),
        MapConv("mode", "select", mi="2.p.4", map={
            0: "day", 1: "reading", 2: "warm", 3: "tv", 4: "night"
        }),
        Converter("power_on_state", "switch", mi="3.p.2", enabled=False),  # bool
    ],
}]

########################################################################################
# 3rd party zigbee
########################################################################################

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
    "spec": [
        ZOnOffConv("switch", "switch", bind=True),
        ZTuyaPowerOn,
        ZTuyaPlugModeConv("mode", "select", enabled=False),
    ],
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
    "RH3052": ["Tuya", "TH sensor", "TT001ZAV20"],
    "TS0201": ["Tuya", "TH sensor", "IH-K009"],
    "support": 3,
    "spec": [
        ZTemperatureConv("temperature", "sensor"),
        ZHumidityConv("humidity", "sensor"),
        # value always 100%
        # ZBatteryConv("battery", "sensor"),
    ],
}, {
    "RH3040": ["Tuya", "Motion Sensor", "TYZPIR-02"],
    "support": 5,
    "ttl": 6 * 60 * 60,
    "spec": [
        ZIASZoneConv("occupancy", "binary_sensor"),
        ZBatteryConv("battery", "sensor", report="1h 12h 0"),
    ],
}, {
    "TS0202": ["Tuya", "Motion Sensor", "IH012-RT01"],
    "spec": [
        ZIASZoneConv("occupancy", "binary_sensor"),
    ],
}, {
    # very simple relays
    "01MINIZB": ["Sonoff", "Mini", "ZBMINI"],
    "SA-003-Zigbee": ["eWeLink", "Zigbee OnOff Controller", "SA-003-Zigbee"],
    "support": 5,  # @AlexxIT
    "spec": [ZSwitch]
}, {
    "ZBMINIL2": ["Sonoff", "Mini L2 (no N)", "ZBMINIL2"],
    "spec": [
        ZSwitch, ZPowerOn
    ]
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
        ZOccupancyConv("occupancy", "binary_sensor", ep=2, bind=True, report="0s 1h 0"),
        ZIlluminanceConv("illuminance", "sensor", ep=2, bind=True, report="10s 1h 5"),
        ZTemperatureConv("temperature", "sensor", ep=2, bind=True, report="10s 1h 100"),
        ZBatteryConv("battery", "sensor", ep=2, bind=True, report="1h 12h 0"),
        ZOccupancyTimeoutConv("occupancy_timeout", "number", ep=2, enabled=False),
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
    "TRADFRI bulb E27 W opal 1000lm": ["IKEA", "Bulb E27 1000 lm", "LED1623G12"],
    "TRADFRI bulb E27 WW 806lm": ["IKEA", "Bulb E27 806 lm", "LED1836G9"],
    "support": 3,  # @AlexxIT TODO: tests, effect?
    "spec": [
        ZOnOffConv("light", "light"),
        ZBrightnessConv("brightness", parent="light"),
    ],
}, {
    "TRADFRI bulb E14 WS opal 600lm": ["IKEA", "Bulb E14 WS opal 600lm", "LED1738G7"],
    "TRADFRI bulb E12 WS 450lm": ["IKEA", "Bulb E12 WS 450lm", "LED1903C5"],
    "TRADFRI bulb E14 WS 470lm": ["IKEA", "Bulb E14 WS 470lm", "LED1903C5"],
    "TRADFRI bulb E17 WS 440lm": ["IKEA", "Bulb E17 WS 440lm", "LED1903C5"],
    "spec": [
        ZOnOffConv("light", "light"),
        ZXiaomiBrightnessConv("brightness", parent="light"),
        ZXiaomiColorTempConv("color_temp", parent="light")
    ],
}, {
    "TRADFRI remote control": ["IKEA", "TRADFRI remote control", "E1524/E1810"],
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

########################################################################################
# BLE
########################################################################################

# Xiaomi BLE MiBeacon + MIoT spec
DEVICES += [{
    4611: ["Xiaomi", "TH Sensor", "XMWSDJ04MMC"],
    "spec": [
        MiBeacon, BLETemperature, BLEHumidity,
        # https://github.com/AlexxIT/XiaomiGateway3/issues/929
        MathConv("temperature", mi="3.p.1001", min=-30, max=100, round=1),
        MathConv("humidity", mi="3.p.1008", min=0, max=100, round=1),
        Converter("battery", mi="2.p.1003"),
        Converter("battery", "sensor", enabled=None),  # no in new firmwares
    ],
}, {
    6473: ["Xiaomi", "Double Button", "XMWXKG01YL"],
    "spec": [
        MiBeacon, BLEAction, Button1, Button2, ButtonBoth, BLEBattery,
        Converter("battery", mi="2.p.1003"),
        BLEEvent("action", mi="3.e.1012", map={
            1: "button_1_single", 2: "button_2_single", 3: "button_both_single"
        }),
        BLEEvent("action", mi="3.e.1013", map={
            1: "button_1_double", 2: "button_2_double"
        }),
        BLEEvent("action", mi="3.e.1014", map={
            1: "button_1_hold", 2: "button_2_hold"
        }),
    ],
    "ttl": "60m",  # battery every 5 min
}, {
    # https://github.com/AlexxIT/XiaomiGateway3/issues/826
    7184: ["Linptech", "Wireless Button", "K11"],
    "spec": [
        MiBeacon, BLEAction, Button, BLEBattery,
        Converter("battery", mi="2.p.1003"),
        BLEEvent("action", mi="3.e.1012", map={1: SINGLE, 8: HOLD, 15: DOUBLE}),
    ],
    "ttl": "6h"  # battery every 6 hours
}, {
    # https://home.miot-spec.com/spec?type=urn:miot-spec-v2:device:temperature-humidity-sensor:0000A00A:linp-ks1bp:1
    15895: ["Linptech", "Wireless Button KS1Pro", "KS1PBB"],
    "spec": [
        MiBeacon, BLEAction, BLEHumidity, BLETemperature, BLEBattery,
        MathConv("temperature", mi="2.p.1001", min=-30, max=100, round=1),
        MathConv("humidity", mi="2.p.1008", min=0, max=100, round=1),
        Converter("battery", mi="4.p.1003"),
        BLEEvent("action", mi="5.e.1012", map={
            1: "button_1_single", 2: "button_2_single", 3: "button_3_single", 4: "button_4_single"
        }),
        BLEEvent("action", mi="5.e.1013", map={
            1: "button_1_double", 2: "button_2_double", 3: "button_3_double", 4: "button_4_double"
        }),
        BLEEvent("action", mi="5.e.1014", map={
            1: "button_1_hold", 2: "button_2_hold", 3: "button_3_hold", 4: "button_4_hold"
        }),
    ],
    "ttl": "6h"  # battery every 6 hours
}, {
    # lumi.remote.mcn001
    9095: ["Xiaomi", "Wireless Button", "XMWXKG01LM"],
    "spec": [
        MiBeacon, BLEAction, Button, BLEBattery,
        Converter("battery", mi="2.p.1003"),
        ButtonMIConv("button", mi="3.e.1012", value=1),  # single
        ButtonMIConv("button", mi="3.e.1013", value=2),  # double
        ButtonMIConv("button", mi="3.e.1014", value=16),  # hold
    ],
    "ttl": "6h"  # battery every 6 hours
}, {
    # https://home.miot-spec.com/spec/miaomiaoce.sensor_ht.o2
    5860: ["Xiaomi", "TH Clock", "LYWSD02MMC"],
    # https://home.miot-spec.com/spec/miaomiaoce.sensor_ht.t8
    9538: ["Xiaomi", "TH Clock Pro", "LYWSD02MMC"],
    # https://home.miot-spec.com/spec/miaomiaoce.sensor_ht.t9
    10290: ["Xiaomi", "TH Sensor 3", "MJWSD05MMC"],
    "spec": [
        MiBeacon, BLETemperature, BLEHumidity,
        MathConv("temperature", mi="3.p.1001", min=-30, max=100, round=1),
        MathConv("humidity", mi="3.p.1002", min=0, max=100, round=0),
        Converter("battery", mi="2.p.1003"),
        Converter("battery", "sensor", enabled=None),  # no in new firmwares
    ]
}, {
    10987: ["Linptech", "Motion Sensor 2", "HS1BB"],
    "spec": [
        MiBeacon, BLEMotion, BLEIlluminance, BLEBattery,
        Converter("idle_time", "sensor", enabled=False),
        Converter("illuminance", mi="2.p.1005"),
        EventConv("motion", mi="2.e.1008", value=True),
        Converter("battery", mi="3.p.1003"),
    ],
}, {
    13617: ["xiaomi", "Motion Sensor 2s", "XMPIRO25XS"],
    "spec": [
        MiBeacon, BLEMotion, BLEIlluminance, BLEBattery,
        Converter("idle_time", "sensor", enabled=False),
        Converter("illuminance", mi="2.p.1005"),
        EventConv("motion", mi="2.e.1008", value=True),
        Converter("battery", mi="3.p.1003"),
    ],
}, {
    # https://home.miot-spec.com/spec?type=urn:miot-spec-v2:device:remote-control:0000A021:huca-wx8:1
    12382: ["H+", "Wireless Button", "huca-wx8"],
    "spec": [
        MiBeacon, BLEAction, Button, BLEBattery,
        Converter("battery", mi="13.p.1003"),
        BLEEvent("action", mi="12.e.1012", map={
            1: "button_1_single", 2: "button_2_single", 3: "button_3_single",
            4: "button_4_single", 5: "button_5_single", 6: "button_6_single",
            7: "button_7_single", 8: "button_8_single"
        }),
        BLEEvent("action", mi="12.e.1013", map={
            1: "button_1_double", 2: "button_2_double", 3: "button_3_double",
            4: "button_4_double", 5: "button_5_double", 6: "button_6_double",
            7: "button_7_double", 8: "button_8_double"
        }),
    ],
    "ttl": "6h"  # battery every 6 hours
}, {
    6742: ["Le", "Wireless Button", "lemesh.remote.ts1"],
    "spec": [
        MiBeacon, BLEAction, Button,
        BLEEvent("action", mi="2.e.1012", map={
            1: "button_1_single", 2: "button_2_single", 3: "button_3_single",
            4: "button_4_single", 5: "button_5_single", 6: "button_6_single",
            7: "button_7_single", 8: "button_8_single"
        }),
        BLEEvent("action", mi="2.e.1013", map={
            1: "button_1_double", 2: "button_2_double", 3: "button_3_double",
            4: "button_4_double", 5: "button_5_double", 6: "button_6_double",
            7: "button_7_double", 8: "button_8_double"
        }),
        BLEEvent("action", mi="2.e.1014", map={
            1: "button_1_hold", 2: "button_2_hold", 3: "button_3_hold",
            4: "button_4_hold", 5: "button_5_hold", 6: "button_6_hold",
            7: "button_7_hold", 8: "button_8_hold"
        }),
    ]
}, {
    # https://home.miot-spec.com/spec?type=urn:miot-spec-v2:device:timer:0000A0BD:hoto-kt:1
    9385: ["Mijia", "Smart Timer", "hoto.timer.kt"],
    "spec": [
        BLEAction,
        EventConv("action", mi="2.e.1025", value="timer1"),
        EventConv("action", mi="3.e.1025", value="timer2"),
    ],
}, {
    16143: ["Linptech", "Submersion Sensor", "RS1BB"],
    "spec": [
        MiBeacon, BLEWaterLeak, BLEBattery,
        Converter("water_leak", mi="2.p.1006"),
        Converter("battery", mi="3.p.1003"),
    ],
}, {
    # https://home.miot-spec.com/spec/linp.senpres.ps1bb
    16204: ["Linptech", "Pressure Sensor", "PS1BB"],
    "spec": [
        BoolConv("pressure_state", "binary_sensor", mi="2.p.1060"),  # bool
        Converter("battery", "sensor", mi="3.p.1003"),
    ],
}]

# Xiaomi BLE MiBeacon only spec
# https://custom-components.github.io/ble_monitor/by_brand
DEVICES += [{
    152: ["Xiaomi", "Flower Care", "HHCCJCY01"],
    "spec": [
        MiBeacon, BLETemperature, BLEMoisture, BLEConductivity, BLEIlluminance,
        Converter("battery", "sensor", enabled=None),  # no in new firmwares
    ],
    "ttl": "60m"  # TODO: check right value
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
    13617: ["Xiaomi", "Motion Sensor 2S", "XMPIR02SXS"],
    "spec": [
        MiBeacon, BLEMotion, BLEIlluminance, BLEBattery,
        EventConv("motion", mi="2.e.1008", value=True),
        Converter("illuminance", mi="2.p.1005"),
        Converter("idle_time", "sensor", mi="2.p.1024", enabled=False),
        Converter("battery", mi="3.p.1003", enabled=None),
    ],
    "ttl": "12h",  # battery every 12 hours
}, {
    2691: ["Xiaomi", "Qingping Motion Sensor", "CGPR1"],
    "spec": [
        MiBeacon, BLEMotion, BLELight, BLEIlluminance, BLEBattery,
        Converter("idle_time", "sensor", enabled=False),
    ],
    "ttl": "60m",  # battery every 11 min
}, {
    1983: ["Yeelight", "Button S1", "YLAI003"],
    "spec": [MiBeacon, BLEAction, BLEBattery],
    "ttl": "60m",  # battery every 5 min
}, {
    2443: ["Xiaomi", "Door/Window Sensor 2", "MCCGQ02HL"],
    "spec": [
        MiBeacon, BLEContact, BLELight, BLEBattery,
    ],
    "ttl": "3d",  # battery every 1 day
}, {
    6281: ["Linptech", "Door/Window Sensor", "MS1BB"],
    "spec": [
        MiBeacon, BLEContact, BLEBattery,
        MapConv("contact", mi="2.p.1004", map={1: True, 2: False}),
        Converter("battery", mi="3.p.1003"),
    ],
    "ttl": "60m",
}, {
    2455: ["Honeywell", "Smoke Alarm", "JTYJ-GD-03MI"],
    "spec": [MiBeacon, BLEAction, BLESmoke, BLEBattery],
    "ttl": "60m",  # battery every 4:30 min
}, {
    2147: ["Xiaomi", "Water Leak Sensor", "SJWS01LM"],
    "spec": [
        MiBeacon, BLEWaterLeak, BLEBattery,
        Converter("action", "sensor", enabled=False),
    ],
    "ttl": "60m"  # battery every 4? hour
}, {
    # https://github.com/AlexxIT/XiaomiGateway3/issues/776
    3685: ["Xiaomi", "Face Recognition Smart Door Lock X", "XMZNMS06LM"],
    "spec": [
        MiBeacon,
        Converter("action", "sensor"),
        Converter("battery", "sensor"),
        Converter("contact", "binary_sensor"),
        Converter("lock", "binary_sensor"),
    ],
}, {
    6017: ["Xiaomi", "Face Recognition Smart Door Lock", "XMZNMS09LM"],
    "spec": [
        MiBeacon,  # backward support old firmwares

        # sensor action
        EventConv("action", "sensor", mi="2.e.1020"),
        Converter("key_id", mi="2.p.1"),
        Converter("method_id", mi="2.p.5"),
        MapConv("method", mi="2.p.5", map={
            1: "mobile", 2: "fingerprint", 3: "password", 4: "nfc", 5: "face", 8: "key",
            9: "one_time_password", 10: "periodic_password", 12: "coerce", 15: "manual",
            16: "auto"
        }),
        Converter("action_id", mi="2.p.3"),
        MapConv("action", mi="2.p.3", map={
            1: "lock", 2: "unlock", 3: "lock_outside", 4: "lock_inside",
            5: "unlock_inside", 6: "enable_child_lock", 7: "disable_child_lock",
            8: "enable_away", 9: "disable_away"
        }),
        MapConv("position", mi="2.p.6", map={
            1: "indoor", 2: "outdoor", 3: "not tell indoor or outdoor"
        }),
        Converter("timestamp", mi="2.p.2"),  # lock timestamp

        # doorbell
        EventConv("action", mi="5.e.1006", value="doorbell"),
        Converter("timestamp", mi="5.p.1"),  # doorbell timestamp

        # doorbell sensor
        Converter("doorbell", "sensor", mi="5.p.1"),
        # contact binary_sensor
        MapConv("contact", "binary_sensor", mi="2.p.3", map={1: False, 2: True}),
        # lock binary_sensor
        MapConv("lock", "binary_sensor", mi="2.p.3", map={1: False, 2: True}),
        # battery sensor
        Converter("battery", "sensor", mi="4.p.1003"),
    ],
    "ttl": "25h"
}, {
    # https://github.com/AlexxIT/XiaomiGateway3/issues/657
    2444: ["Xiaomi", "Door Lock", "XMZNMST02YD"],
    "spec": [
        MiBeacon,
        Converter("action", "sensor"),
        Converter("battery", "sensor"),
        Converter("lock", "binary_sensor"),
        Converter("opening", "binary_sensor"),
    ],
    "ttl": "6h"
}, {
    3641: ["Xiaomi", "Door Lock 1S", "XMZNMS08LM"],
    "spec": [
        MiBeacon,
        Converter("action", "sensor"),
        Converter("battery", "sensor"),
        Converter("doorbell", "sensor"),
        Converter("contact", "binary_sensor"),
    ],
    "ttl": "3d"  # battery every 1? day
}, {
    # https://home.miot-spec.com/spec/oms.lock.dl01
    # https://github.com/AlexxIT/XiaomiGateway3/issues/973
    10249: ["Xiaomi", "Door Lock E10", "XMZNMS01OD"],
    "spec": [
        MapConv("door", "sensor", mi="4.p.1021", map={
            1: "locked", 2: "unlocked", 3: "timeout", 4: "ajar"
        }),

        EventConv("action", "sensor", mi="3.e.1020"),
        Converter("key_id", mi="3.p.1"),
        Converter("method_id", mi="3.p.2"),
        MapConv("method", mi="3.p.2", map={
            1: "mobile", 2: "fingerprint", 3: "password", 4: "nfc", 8: "key",
            9: "one_time_password", 10: "periodic_password", 12: "coerce", 15: "manual"
        }),
        Converter("action_id", mi="3.p.3"),
        MapConv("action", mi="3.p.3", map={
            1: "lock", 2: "unlock", 3: "lock_outside", 4: "lock_inside",
            5: "unlock_inside", 8: "enable_away", 9: "disable_away"
        }),
        MapConv("position", mi="3.p.4", map={1: "indoor", 2: "outdoor"}),

        Converter("timestamp", mi="3.p.6"),  # lock timestamp

        # doorbell
        EventConv("action", mi="6.e.1006", value="doorbell"),
        Converter("timestamp", mi="6.p.1"),  # doorbell timestamp

        Converter("battery", "sensor", mi="5.p.1003"),
    ],
    "ttl": "25h"
}, {
    # https://home.miot-spec.com/spec/lcrmcr.safe.ms30b
    1393: ["Xiaomi", "Smart Safe Cayo Anno 30Z", "lcrmcr.safe.ms30b"],
    "spec": [
        MiBeacon, BLEAction,

        MapConv("method", mi="2.p.1", map={
            0: "mobile", 2: "fingerprint", 4: "key",
        }),
        Converter("action_id", mi="2.p.2"),
        MapConv("abnormal_condition", mi="2.p.3", map={
            1: "wrong_fingerprint", 2: "lockpicking", 4: "timeout_not_locked",
        }),
        Converter("battery", "sensor"),
    ],
    "ttl": "25h"
}, {
    # https://github.com/AlexxIT/XiaomiGateway3/issues/1063
    10371: ["PTX", "Mesh Multifunction Wireless Switch", "PTX-AK3-QMIMB"],
    "spec": [
        MiBeacon, BLEAction, Button,  # don't know is it BLE or Mesh
        EventConv("action", mi="2.e.1", value="button_1_single"),
        EventConv("action", mi="2.e.2", value="button_2_single"),
        EventConv("action", mi="2.e.3", value="button_3_single"),
        EventConv("action", mi="2.e.4", value="button_4_single"),
        EventConv("action", mi="2.e.5", value="button_5_single"),
        EventConv("action", mi="3.e.1", value="button_6_single"),
        EventConv("action", mi="3.e.2", value="button_1_hold"),
        EventConv("action", mi="3.e.3", value="button_2_hold"),
        EventConv("action", mi="3.e.4", value="button_3_hold"),
        EventConv("action", mi="3.e.5", value="button_4_hold"),
        EventConv("action", mi="3.e.6", value="button_5_hold"),
        EventConv("action", mi="3.e.7", value="button_6_hold"),
        Converter("battery", "sensor", mi="4.p.1"),
    ],
    "ttl": "25h"
}, {
    # https://home.miot-spec.com/spec/giot.switch.v52ksm
    13139: ["GranwinIoT", "Smart Two-Button Switch (Mesh) V5", "giot.switch.v52ksm"],
    "spec": [
        Converter("left_switch", "switch", mi="2.p.1"),
        Converter("right_switch", "switch", mi="3.p.1"),
        MapConv("left_switch_mode", "select", mi="2.p.2", map={
            0: "normal_switch", 1: "wireless_switch", 2: "smart_switch", 3: "button_switch"
        }),
        MapConv("right_switch_mode", "select", mi="3.p.2", map={
            0: "normal_switch", 1: "wireless_switch", 2: "smart_switch", 3: "button_switch"
        }),
    ]
}, {
    11273: ["PTX", "BLE Wireless situation knob switch", "PTX-X6-QMIMB"],
    "spec": [
        Action,
        ButtonMIConv("button_1", mi="2.e.1012", value=1),  # single
        ButtonMIConv("button_2", mi="2.e.1013", value=1),
        ButtonMIConv("button_3", mi="2.e.1014", value=1),
        ButtonMIConv("button_4", mi="2.e.1028", value=1),
        EventConv("action", mi="3.e.1012", value="knob_increasing"),
        EventConv("action", mi="3.e.1013", value="knob_reduced"),
        EventConv("action", mi="3.e.1014", value="knob_press"),
    ],
    "ttl": "7d"
}, {
    # https://home.miot-spec.com/spec/090615.remote.btsw1
    14523: ["PTX", "BLE Wireless Switch", "090615.remote.btsw1"],
    "spec": [
        MiBeacon, BLEAction, Button,
        EventConv("action", mi="2.e.1012", value="single"),
        EventConv("action", mi="2.e.1013", value="double"),
        EventConv("action", mi="2.e.1014", value="hold"),
    ]
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
    # https://github.com/AlexxIT/XiaomiGateway3/issues/1001
    1203: ["Dessmann ", "Q3", "dsm.lock.q3"],
    1433: ["Xiaomi", "Door Lock", "MJZNMS03LM"],
    1694: ["Aqara", "Door Lock N100 (Bluetooth)", "ZNMS16LM"],
    1695: ["Aqara", "Door Lock N200", "ZNMS17LM"],
    2054: ["Xiaomi", "Toothbrush T700", "MES604"],
    6032: ["Xiaomi", "Toothbrush T700i", "MES604"],
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

########################################################################################
# Mesh
########################################################################################

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
    # https://home.miot-spec.com/spec/crzm.light.w00a01
    2292: ["crzm", "Mesh Light", "crzm.light.w00a01"],
    "spec": [
        Converter("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", parent="light", max=100),
    ]
}, {
    # brightness 1..100, color_temp 2700..6500
    3416: ["PTX", "Mesh Downlight", "090615.light.mlig01"],
    4924: ["PTX", "Mesh Downlight", "090615.light.mlig02"],
    4945: ["PTX", "Mesh Lightstrip", "090615.light.mdd02"],
    7057: ["PTX", "Mesh Light", "090615.light.cxlg01"],
    15169: ["PTX", "Mesh Downlight", "090615.light.mylg04"],
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
    7136: ["LeMesh", "Mesh Light v2", "lemesh.light.wy0c09"],
    9439: ["GDDS", "Mesh Light", "gdds.light.wy0a01"],
    "spec": [
        Converter("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", parent="light", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", parent="light", mink=3000, maxk=6400),
    ]
}, {
    # https://home.miot-spec.com/spec/lemesh.light.wy0c08
    3531: ["LeMesh", "Mesh Light", "lemesh.light.wy0c08"],
    "spec": [
        Converter("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", parent="light", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", parent="light", mink=3000, maxk=6400),
        MapConv("mode", "select", mi="2.p.5", map={
            0: "WY", 4: "day", 5: "night", 8: "TV", 9: "reading", 10: "computer",
            11: "hospitality", 12: "entertainment", 13: "wakeup", 14: "dusk",
            15: "sleep"
        }),
        MapConv("power_on_state", "select", mi="4.p.1", map={0: "default", 1: "on"}),
        BoolConv("save_state", "switch", mi="4.p.2"),
        MapConv("dimming", "select", mi="4.p.3", map={0: "Gradient", 1: "Immediately"}),
        BoolConv("night_light", "switch", mi="4.p.5"),
    ]
}, {
    # https://home.miot-spec.com/spec/yeelink.light.stripf
    11901: ["Yeelight", "Mesh Light Strip C1", "yeelink.light.stripf"],
    # https://home.miot-spec.com/spec/yeelink.light.ml9
    11667: ["Yeelight", "Mesh Downlight C1", "YCCBC1019/YCCBC1020"],  # flex
    "spec": [
        Converter("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", parent="light", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", parent="light", mink=3000, maxk=6400),
        MapConv("mode", "select", mi="2.p.5", map={
            0: "WY", 4: "day", 5: "night", 8: "TV", 9: "reading", 10: "computer",
            11: "hospitality", 12: "entertainment", 13: "wakeup", 14: "dusk",
            15: "sleep"
        }),

        Converter("flex_switch", "switch", mi="2.p.6", enabled=False),  # uint8
        MapConv("power_on_state", "select", mi="2.p.7", map={0: "default", 1: "on"}, enabled=False),

        BoolConv("save_state", "switch", mi="4.p.2"),
        MapConv("dimming", "select", mi="4.p.3", map={0: "Gradient", 1: "Immediately"}),
        BoolConv("night_light", "switch", mi="4.p.5"),
    ]
}, {
    # https://home.miot-spec.com/spec/symi.light.wy0a01
    10055: ["Symi", "Mesh Light", "symi.light.wy0a01"],
    "spec": [
        Converter("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", parent="light", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", parent="light", mink=3000, maxk=6400),
        MapConv("mode", "select", mi="2.p.5", map={
            0: "WY", 4: "day", 5: "night", 7: "Warmth", 8: "TV", 9: "reading", 10: "computer",
            11: "hospitality", 12: "entertainment", 13: "wakeup", 14: "dusk",
            15: "sleep", 16: "Respiration", 17: "Loop Jump"
        }),

        Converter("flex_switch", "switch", mi="2.p.6", enabled=False),  # uint8
        MapConv("power_on_state", "select", mi="2.p.7", map={0: "default", 1: "on"}),

        BoolConv("save_state", "switch", mi="4.p.2"),
        MapConv("dimming", "select", mi="4.p.3", map={0: "Gradient", 1: "Immediately"}),
        BoolConv("night_light", "switch", mi="4.p.5"),
    ]
}, {
    # https://home.miot-spec.com/spec/lemesh.light.wy0c14
    13471: ["LeMesh", "Mesh Light", "lemesh.light.wy0c14"],
    # https://home.miot-spec.com/spec/lemesh.light.wy0c15
    13525: ["LeMesh", "Mesh Light", "lemesh.light.wy0c15"],
    # https://home.miot-spec.com/spec/yeelink.light.wy0a03
    14335: ["Yeelight", "Yeelight Smart Light", "yeelink.light.wy0a03"],
    "spec": [
        Converter("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", parent="light", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", parent="light", mink=2700, maxk=6500),
        MapConv("mode", "select", mi="2.p.5", map={
            0: "WY", 4: "day", 5: "night", 8: "TV", 9: "reading", 10: "computer",
            11: "hospitality", 12: "entertainment", 13: "wakeup", 14: "dusk",
            15: "sleep"
        }),

        Converter("flex_switch", "switch", mi="2.p.6", enabled=False),  # uint8
        MapConv("power_on_state", "select", mi="2.p.7", map={0: "default", 1: "on"}),

        BoolConv("save_state", "switch", mi="4.p.2"),
        MapConv("dimming", "select", mi="4.p.3", map={0: "Gradient", 1: "Immediately"}),
        BoolConv("night_light", "switch", mi="4.p.5"),
    ]
}, {
    # https://home.miot-spec.com/spec/jymc.light.falmp
    10729: ["Unknown", "Mesh Light", "jymc.light.falmp"],
    "spec": [
        Converter("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", parent="light", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", parent="light", mink=3000, maxk=6500),
        BoolConv("flex_switch", "switch", mi="2.p.4", enabled=False),
        MapConv("mode", "select", mi="2.p.5", map={
            0: "Warmth", 1: "TV", 2: "Reading", 3: "Night",
            4: "Hospitality", 5: "Leisure", 6: "Office", 255: "Normal"
        }),
    ],
}, {
    15745: ["Yeelight", "Mesh Downlight Z1", "YCCSLI001"],
    "spec": [
        Converter("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", parent="light", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", parent="light", mink=2700, maxk=6000),
        MapConv("mode", "select", mi="2.p.7", map={
            0: "WY", 4: "Lighting", 5: "Night Light", 7: "Warmth", 8: "TV", 9: "Reading", 10: "Computer",
            11: "Hospitality", 12: "Entertainment", 13: "Wake Up", 14: "Dusk",
            15: "Sleep", 16: "Mode-1", 17: "Mode-2", 18: "Mode-3", 19: "Mode-4"
        })
    ]
}, {
    12455: ["Yeelight", "K Series Single Wall Switch", "YLYKG-0025/0020"],
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),
        MapConv("power_on_state", "select", mi="2.p.2", map={
            1: "On", 2: "Off", 3: "Default"
        }, enabled=False),
        MapConv("wireless", "select", mi="2.p.3", map={
            0: "default", 1: "Wireless", 2: "Wireless", 3: "Wireless"
        }, enabled=False),
        Converter("led", "switch", mi="5.p.1", enabled=False),
        MapConv("operatingmode", "select", mi="8.p.1", map={
            1: "Top Speed Mode", 2: "Standard Mode"
        }, enabled=False),
        Converter("action", "sensor", enabled=False),
        ButtonMIConv("button", mi="14.e.1", value=1),
        ButtonMIConv("button", mi="14.e.2", value=2),
        ButtonMIConv("button", mi="14.e.3", value=16),
    ],
}, {
    12456: ["Yeelight", "K Series Double Wall Switch", "YLYKG-0026/0021"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        MapConv("power_on_state_1", "select", mi="2.p.2", map={
            1: "On", 2: "Off", 3: "Default"
        }, enabled=False),
        MapConv("wireless_1", "select", mi="2.p.3", map={
            0: "default", 1: "Wireless", 2: "Wireless", 3: "Wireless"
        }, enabled=False),
        Converter("channel_2", "switch", mi="3.p.1"),
        MapConv("power_on_state_2", "select", mi="3.p.2", map={
            1: "On", 2: "Off", 3: "Default"
        }, enabled=False),
        MapConv("wireless_2", "select", mi="3.p.3", map={
            0: "default", 1: "Wireless", 2: "Wireless", 3: "Wireless"
        }, enabled=False),
        Converter("led", "switch", mi="5.p.1", enabled=False),
        MapConv("operatingmode", "select", mi="8.p.1", map={
            1: "Top Speed Mode", 2: "Standard Mode"
        }, enabled=False),
        Converter("action", "sensor", enabled=False),
        ButtonMIConv("button_1", mi="14.e.1", value=1),
        ButtonMIConv("button_1", mi="14.e.2", value=2),
        ButtonMIConv("button_1", mi="14.e.3", value=16),
        ButtonMIConv("button_2", mi="15.e.1", value=1),
        ButtonMIConv("button_2", mi="15.e.2", value=2),
        ButtonMIConv("button_2", mi="15.e.3", value=16),
    ],
}, {
    12457: ["Yeelight", "K Series Triple Wall Switch", "YLYKG-0026/0021"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        MapConv("power_on_state_1", "select", mi="2.p.2", map={
            1: "On", 2: "Off", 3: "Default"
        }, enabled=False),
        MapConv("wireless_1", "select", mi="2.p.3", map={
            0: "default", 1: "Wireless", 2: "Wireless", 3: "Wireless"
        }, enabled=False),
        Converter("channel_2", "switch", mi="3.p.1"),
        MapConv("power_on_state_2", "select", mi="3.p.2", map={
            1: "On", 2: "Off", 3: "Default"
        }, enabled=False),
        MapConv("wireless_2", "select", mi="3.p.3", map={
            0: "default", 1: "Wireless", 2: "Wireless", 3: "Wireless"
        }, enabled=False),
        Converter("channel_3", "switch", mi="4.p.1"),
        MapConv("power_on_state_3", "select", mi="4.p.2", map={
            1: "On", 2: "Off", 3: "Default"
        }, enabled=False),
        MapConv("wireless_3", "select", mi="4.p.3", map={
            0: "default", 1: "Wireless", 2: "Wireless", 3: "Wireless"
        }, enabled=False),
        Converter("led", "switch", mi="5.p.1", enabled=False),
        MapConv("operatingmode", "select", mi="8.p.1", map={
            1: "Top Speed Mode", 2: "Standard Mode"
        }, enabled=False),
        Converter("action", "sensor", enabled=False),
        ButtonMIConv("button_1", mi="14.e.1", value=1),
        ButtonMIConv("button_1", mi="14.e.2", value=2),
        ButtonMIConv("button_1", mi="14.e.3", value=16),
        ButtonMIConv("button_2", mi="15.e.1", value=1),
        ButtonMIConv("button_2", mi="15.e.2", value=2),
        ButtonMIConv("button_2", mi="15.e.3", value=16),
        ButtonMIConv("button_3", mi="16.e.1", value=1),
        ButtonMIConv("button_3", mi="16.e.2", value=2),
        ButtonMIConv("button_3", mi="16.e.3", value=16),
    ],
}, {
    12458: ["Yeelight", "K Series 4-Key Wall Switch", "YLYKG-0028/0023"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        MapConv("power_on_state_1", "select", mi="2.p.2", map={
            1: "On", 2: "Off", 3: "Default"
        }, enabled=False),
        MapConv("wireless_1", "select", mi="2.p.3", map={
            0: "default", 1: "Wireless", 2: "Wireless", 3: "Wireless"
        }, enabled=False),
        Converter("channel_2", "switch", mi="3.p.1"),
        MapConv("power_on_state_2", "select", mi="3.p.2", map={
            1: "On", 2: "Off", 3: "Default"
        }, enabled=False),
        MapConv("wireless_2", "select", mi="3.p.3", map={
            0: "default", 1: "Wireless", 2: "Wireless", 3: "Wireless"
        }, enabled=False),
        Converter("channel_3", "switch", mi="4.p.1"),
        MapConv("power_on_state_3", "select", mi="4.p.2", map={
            1: "On", 2: "Off", 3: "Default"
        }, enabled=False),
        MapConv("wireless_3", "select", mi="4.p.3", map={
            0: "default", 1: "Wireless", 2: "Wireless", 3: "Wireless"
        }, enabled=False),
        Converter("channel_4", "switch", mi="12.p.1"),
        MapConv("power_on_state_4", "select", mi="12.p.2", map={
            1: "On", 2: "Off", 3: "Default"
        }, enabled=False),
        MapConv("wireless_4", "select", mi="12.p.3", map={
            0: "default", 1: "Wireless", 2: "Wireless", 3: "Wireless"
        }, enabled=False),
        Converter("led", "switch", mi="5.p.1", enabled=False),
        MapConv("operatingmode", "select", mi="8.p.1", map={
            1: "Top Speed Mode", 2: "Standard Mode"
        }, enabled=False),
        Converter("action", "sensor", enabled=False),
        ButtonMIConv("button_1", mi="14.e.1", value=1),
        ButtonMIConv("button_1", mi="14.e.2", value=2),
        ButtonMIConv("button_1", mi="14.e.3", value=16),
        ButtonMIConv("button_2", mi="15.e.1", value=1),
        ButtonMIConv("button_2", mi="15.e.2", value=2),
        ButtonMIConv("button_2", mi="15.e.3", value=16),
        ButtonMIConv("button_3", mi="16.e.1", value=1),
        ButtonMIConv("button_3", mi="16.e.2", value=2),
        ButtonMIConv("button_3", mi="16.e.3", value=16),
        ButtonMIConv("button_4", mi="17.e.1", value=1),
        ButtonMIConv("button_4", mi="17.e.2", value=2),
        ButtonMIConv("button_4", mi="17.e.3", value=16),
    ],
}, {
    1945: ["Xiaomi", "Mesh Wall Switch", "DHKG01ZM"],
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),
        Converter("led", "switch", mi="10.p.1", enabled=False),
        BoolConv("wireless", "switch", mi="2.p.2", enabled=False),
        Converter("action", "sensor", enabled=False),
        ButtonMIConv("button_1", mi="8.e.1", value=1),  # single
    ],
}, {
    2007: ["Unknown", "Mesh Switch Controller", "lemesh.switch.sw0a01"],
    3150: ["XinGuang", "Mesh Switch", "wainft.switch.sw0a01"],
    3169: ["Unknown", "Mesh Switch Controller", "lemesh.switch.sw0a02"],
    3170: ["Unknown", "Mesh Switch Controller", "lemesh.switch.sw0a04"],
    4252: ["Unknown", "Mesh Switch", "dwdz.switch.sw0a01"],
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),
    ],
}, {
    # https://home.miot-spec.com/spec/lemesh.switch.sw4a02
    8194: ["LeMesh", "Mesh Switch", "lemesh.switch.sw4a02"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        Converter("channel_3", "switch", mi="4.p.1"),
        Converter("channel_4", "switch", mi="12.p.1"),
    ],
}, {
    # https://home.miot-spec.com/spec/bean.switch.bl01
    9609: ["Bean", "Mesh Switch", "bean.switch.bl01"],
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),
        Converter("action", "sensor", enabled=False),
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
    # https://home.miot-spec.com/spec/zimi.plug.zncz01
    3083: ["Xiaomi", "Electrical Outlet", "ZNCZ01ZM"],
    "spec": [
        Converter("outlet", "switch", mi="2.p.1"),
        MathConv("power", "sensor", mi="3.p.1", multiply=0.01),
        Converter("led", "switch", mi="4.p.1", enabled=False),
        Converter("power_protect", "switch", mi="7.p.1", enabled=False),
        MathConv("power_value", "number", mi="7.p.2", multiply=0.01,
                 min=0, max=163840000, enabled=False),
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
    5937: ["Xiaomi", "Mesh Triple Wall Switch", "DHKG05"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        Converter("channel_3", "switch", mi="4.p.1"),
        Converter("led", "switch", mi="10.p.1", enabled=False),
        BoolConv("wireless_1", "switch", mi="2.p.2", enabled=False),
        BoolConv("wireless_2", "switch", mi="3.p.2", enabled=False),
        BoolConv("wireless_3", "switch", mi="4.p.2", enabled=False),
        Converter("action", "sensor", enabled=False),
        ButtonMIConv("button_1", mi="5.e.1", value=1),  # single
        ButtonMIConv("button_2", mi="6.e.1", value=1),  # single
        ButtonMIConv("button_3", mi="7.e.1", value=1),  # single
        Converter("anti_flick", "switch", mi="9.p.1"),
    ],
}, {
    8255: ["ZNSN", "Mesh Wall Switch ML3", "zm3d"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        Converter("channel_3", "switch", mi="4.p.1"),
    ],
}, {
    12054: ["ZNSN", "Mesh Single Wall Switch", "zg1m"],
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),
        MapConv("wireless", "select", mi="2.p.2", map={
            0: "Normal", 1: "Wireless", 2: "Atom", 3: "Scene"
        }, enabled=False),
        MapConv("power_on_state", "select", mi="2.p.3", map={
            0: "Default", 1: "Off", 2: "On"
        }, enabled=False),
        Converter("action", "sensor", enabled=False),
        ButtonMIConv("button", mi="6.e.2", value=1),
    ],
}, {
    12055: ["ZNSN", "Mesh Double Wall Switch", "zg2m"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        MapConv("wireless_1", "select", mi="2.p.2", map={
            0: "Normal", 1: "Wireless", 2: "Atom", 3: "Scene"
        }, enabled=False),
        MapConv("power_on_state_1", "select", mi="2.p.3", map={
            0: "Default", 1: "Off", 2: "On"
        }, enabled=False),
        Converter("channel_2", "switch", mi="3.p.1"),
        MapConv("wireless_2", "select", mi="3.p.2", map={
            0: "Normal", 1: "Wireless", 2: "Atom", 3: "Scene"
        }, enabled=False),
        MapConv("power_on_state_2", "select", mi="3.p.3", map={
            0: "Default", 1: "Off", 2: "On"
        }, enabled=False),
        Converter("action", "sensor", enabled=None),
        ButtonMIConv("button_1", mi="6.e.1", value=1),
        ButtonMIConv("button_2", mi="6.e.3", value=1),
    ],
}, {
    12058: ["ZNSN", "Mesh Triple Wall Switch", "zg3m"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        MapConv("wireless_1", "select", mi="2.p.2", map={
            0: "Normal", 1: "Wireless", 2: "Atom", 3: "Scene"
        }, enabled=False),
        MapConv("power_on_state_1", "select", mi="2.p.3", map={
            0: "Default", 1: "Off", 2: "On"
        }, enabled=False),
        Converter("channel_2", "switch", mi="3.p.1"),
        MapConv("wireless_2", "select", mi="3.p.2", map={
            0: "Normal", 1: "Wireless", 2: "Atom", 3: "Scene"
        }, enabled=False),
        MapConv("power_on_state_2", "select", mi="3.p.3", map={
            0: "Default", 1: "Off", 2: "On"
        }, enabled=False),
        Converter("channel_3", "switch", mi="4.p.1"),
        MapConv("wireless_3", "select", mi="4.p.2", map={
            0: "Normal", 1: "Wireless", 2: "Atom", 3: "Scene"
        }, enabled=False),
        MapConv("power_on_state_3", "select", mi="4.p.3", map={
            0: "Default", 1: "Off", 2: "On"
        }, enabled=False),
        Converter("action", "sensor", enabled=None),
        ButtonMIConv("button_1", mi="6.e.1", value=1),
        ButtonMIConv("button_2", mi="6.e.2", value=1),
        ButtonMIConv("button_3", mi="6.e.3", value=1),
    ],
}, {
    12059: ["ZNSN", "Mesh Four-Key Wall Switch", "zg4m"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        MapConv("wireless_1", "select", mi="2.p.2", map={
            0: "Normal", 1: "Wireless", 2: "Atom", 3: "Scene"
        }, enabled=False),
        MapConv("power_on_state_1", "select", mi="2.p.3", map={
            0: "Default", 1: "Off", 2: "On"
        }, enabled=False),
        Converter("channel_2", "switch", mi="3.p.1"),
        MapConv("wireless_2", "select", mi="3.p.2", map={
            0: "Normal", 1: "Wireless", 2: "Atom", 3: "Scene"
        }, enabled=False),
        MapConv("power_on_state_2", "select", mi="3.p.3", map={
            0: "Default", 1: "Off", 2: "On"
        }, enabled=False),
        Converter("channel_3", "switch", mi="4.p.1"),
        MapConv("wireless_3", "select", mi="4.p.2", map={
            0: "Normal", 1: "Wireless", 2: "Atom", 3: "Scene"
        }, enabled=False),
        MapConv("power_on_state_3", "select", mi="4.p.3", map={
            0: "Default", 1: "Off", 2: "On"
        }, enabled=False),
        Converter("channel_4", "switch", mi="5.p.1"),
        MapConv("wireless_4", "select", mi="5.p.2", map={
            0: "Normal", 1: "Wireless", 2: "Atom", 3: "Scene"
        }, enabled=False),
        MapConv("power_on_state_4", "select", mi="5.p.3", map={
            0: "Default", 1: "Off", 2: "On"
        }, enabled=False),
        Converter("action", "sensor", enabled=None),
        ButtonMIConv("button_1", mi="6.e.1", value=1),
        ButtonMIConv("button_2", mi="6.e.2", value=1),
        ButtonMIConv("button_3", mi="6.e.3", value=1),
        ButtonMIConv("button_4", mi="6.e.4", value=1),
    ],
}, {
    2715: ["Xiaomi", "Mesh Single Wall Switch", "ZNKG01HL"],
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),
        MathConv("humidity", "sensor", mi="6.p.1", round=2),
        MathConv("temperature", "sensor", mi="6.p.7", round=2),
        BoolConv("wireless", "switch", mi="2.p.2", enabled=False),
        Converter("baby_mode", "switch", mi="11.p.1", enabled=False),
        Converter("action", "sensor", enabled=False),
        ButtonMIConv("button_1", mi="16.e.1", value=1),
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
        Converter("action", "sensor", enabled=False),
        ButtonMIConv("button_1", mi="16.e.1", value=1),
        ButtonMIConv("button_2", mi="18.e.1", value=1),
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
        Converter("action", "sensor", enabled=False),
        ButtonMIConv("button_1", mi="16.e.1", value=1),
        ButtonMIConv("button_2", mi="17.e.1", value=1),
        ButtonMIConv("button_3", mi="18.e.1", value=1),
    ],
}, {
    6266: ["Gosund", "Mesh Triple Wall Switch S6AM", "cuco.switch.s6amts"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        Converter("channel_3", "switch", mi="4.p.1"),
        MapConv("wireless_1", "select", mi="6.p.1", map={
            0: "close", 1: "open-close", 2: "open-open"
        }, enabled=False),
        MapConv("wireless_2", "select", mi="6.p.2", map={
            0: "close", 1: "open-close", 2: "open-open"
        }, enabled=False),
        MapConv("wireless_3", "select", mi="6.p.3", map={
            0: "close", 1: "open-close", 2: "open-open"
        }, enabled=False),
        Converter("led", "switch", mi="8.p.1", enabled=False),  # bool
        Converter("mode", "switch", mi="8.p.2", enabled=False),  # bool
        Converter("action", "sensor", enabled=False),
        ButtonMIConv("button_1", mi="9.e.2", value=1),
        ButtonMIConv("button_1", mi="9.e.3", value=2),
        ButtonMIConv("button_2", mi="9.e.5", value=1),
        ButtonMIConv("button_2", mi="9.e.6", value=2),
        ButtonMIConv("button_3", mi="9.e.8", value=1),
        ButtonMIConv("button_3", mi="9.e.9", value=2),
    ]
}, {
    6267: ["Gosund", "Mesh double Wall Switch S5AM", "cuco.switch.s5amts"],
    "spec": [
        Converter("left_switch", "switch", mi="2.p.1"),
        Converter("right_switch", "switch", mi="3.p.1"),
        MapConv("wireless_1", "select", mi="6.p.1", map={
            0: "close", 1: "open-close", 2: "open-open"
        }, enabled=False),
        MapConv("wireless_2", "select", mi="6.p.2", map={
            0: "close", 1: "open-close", 2: "open-open"
        }, enabled=False),
        Converter("led", "switch", mi="8.p.1", enabled=False),  # bool
        Converter("mode", "switch", mi="8.p.2", enabled=False),  # bool
    ]
}, {
    4160: ["Xiaomi", "Mosquito Repeller 2", "WX10ZM"],
    # "support": 5,  # @AlexxIT need some tests
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),  # bool
        Converter("battery", "sensor", mi="3.p.1"),  # percentage 0-100
        Converter("supply", "sensor", mi="4.p.1"),  # percentage 0-100
        MapConv("led", "switch", mi="9.p.1", map=INVERSE_BOOL, enabled=False),  # bool
        MapConv("power_mode", "select", mi="2.p.2", map={
            0: "auto", 1: "battery", 2: "usb"
        }, enabled=False)
    ],
    "ttl": "1440m"  # https://github.com/AlexxIT/XiaomiGateway3/issues/804
}, {
    4737: ["Xiaomi", "Smart Charging Table Lamp", "MJTD04YL"],
    "spec": [
        Converter("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", parent="light", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", parent="light"),
        Converter("battery", "sensor", mi="4.p.1"),
        MapConv("battery_charging", "binary_sensor", mi="4.p.2", map={
            1: True, 2: False, 3: False,
        }, enabled=False),
    ],
    "ttl": "7d",
}, {
    # urn:miot-spec-v2:device:light:0000A001:yeelink-nl2:1:0000C81D 米家智能光感夜灯
    4736: ["Xiaomi", "Mesh Night Light", "MJYD05YL"],
    "spec": [
        Converter("switch", "light", mi="2.p.1"),  # bool
        BoolConv("light", "binary_sensor", mi="3.p.1")  # uint8 0-Dark 1-Bright
    ],
}, {
    # urn:miot-spec-v2:device:outlet:0000A002:qmi-psv3:1:0000C816小米智能插线板2 5位插孔
    4896: ["Xiaomi", "Mesh Power Strip 2", "XMZNCXB01QM"],
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),  # bool
        Converter("mode", "switch", mi="2.p.2"),  # int8
        MathConv("chip_temperature", "sensor", mi="2.p.3", round=2,
                 enabled=False),  # float
        MathConv("energy", "sensor", mi="3.p.1", multiply=0.1, round=2),
        MathConv("power", "sensor", mi="3.p.2", round=2),  # float
        MathConv("voltage", "sensor", mi="3.p.3", multiply=0.001, round=2),  # float
        MathConv("current", "sensor", mi="3.p.4", multiply=0.001, round=2),  # float
    ]
}, {
    3129: ["Xiaomi", "Smart Curtain Motor", "MJSGCLBL01LM"],
    "spec": [
        MapConv("motor", "cover", mi="2.p.1", map={0: "stop", 1: "open", 2: "close"}),
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
    3789: ["PTX", "Mesh Double Wall Switch", "090615.switch.meshk2"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
    ],
}, {
    3788: ["PTX", "Mesh Triple Wall Switch", "090615.switch.meshk3"],
    # https://github.com/AlexxIT/XiaomiGateway3/issues/993
    11356: ["PTX", "Mesh Triple Wall Switch", "090615.switch.aksk3"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        Converter("channel_3", "switch", mi="4.p.1"),
    ],
}, {
    11333: ["PTX", "Mesh Single Wall Switch", "090615.switch.aksk1"],
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),
        BoolConv("wireless", "switch", mi="2.p.2", enabled=False),
        Converter("action", "sensor", enabled=False),
        ButtonMIConv("button", mi="8.e.1", value=1),  # single
    ],
}, {
    11332: ["PTX", "Mesh Double Wall Switch", "090615.switch.aksk2"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        BoolConv("wireless", "switch", mi="2.p.2", enabled=False),
        Converter("channel_2", "switch", mi="3.p.1"),
        BoolConv("wireless", "switch", mi="3.p.2", enabled=False),
        Converter("action", "sensor", enabled=False),
        ButtonMIConv("button_1", mi="8.e.1", value=1),
        ButtonMIConv("button_1", mi="8.e.2", value=2),
    ],
}, {
    12471: ["PTX", "Mesh Double Wall Switch (No N)", "aidh2"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        BoolConv("wireless", "switch", mi="2.p.2", enabled=False),
        Converter("channel_2", "switch", mi="3.p.1"),
        BoolConv("wireless", "switch", mi="3.p.2", enabled=False),
        Converter("action", "sensor", enabled=False),
        ButtonMIConv("button_1", mi="6.e.1", value=1),  # single
        ButtonMIConv("button_2", mi="7.e.1", value=1),  # single 
        BoolConv("led", "switch", mi="9.p.1", enabled=False),
    ],
}, {
    12470: ["PTX", "Mesh Single Wall Switch(No N)", "aidh1"],
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),
        BoolConv("wireless", "switch", mi="2.p.2", enabled=False),
        Converter("action", "sensor", enabled=False),
        ButtonMIConv("button", mi="6.e.1", value=1),  # single
        BoolConv("led", "switch", mi="9.p.1", enabled=False),
    ],
}, {
    6379: ["Xiaomi", "Mesh Wall Switch (Neutral Wire)", "XMQBKG01LM"],
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),
        Converter("led", "switch", mi="7.p.1", enabled=False),
        BoolConv("wireless", "switch", mi="2.p.2", enabled=False),
        Converter("action", "sensor", enabled=False),
        ButtonMIConv("button", mi="6.e.1", value=1),
        MapConv("device_fault", mi="2.p.3", map={
            0: "nofaults", 1: "overtemperature", 2: "overload",
            3: "overtemperature-overload"
        }),
        MathConv("power", "sensor", mi="5.p.6", round=1),
    ],
}, {
    6380: ["Xiaomi", "Mesh Double Wall Switch (Neutral Wire)", "XMQBKG02LM"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        Converter("led", "switch", mi="5.p.1", enabled=False),
        BoolConv("wireless_1", "switch", mi="2.p.2", enabled=False),
        BoolConv("wireless_2", "switch", mi="3.p.2", enabled=False),
        Converter("action", "sensor", enabled=False),
        ButtonMIConv("button_1", mi="6.e.1", value=1),
        ButtonMIConv("button_2", mi="7.e.1", value=1),
        MapConv("device_fault_1", mi="2.p.3", map={
            0: "nofaults", 1: "overtemperature", 2: "overload",
            3: "overtemperature-overload"
        }),
        MapConv("device_fault_2", mi="3.p.3", map={
            0: "nofaults", 1: "overtemperature", 2: "overload",
            3: "overtemperature-overload"
        }),
        MathConv("power", "sensor", mi="4.p.6", round=1),
    ],
}, {
    6381: ["Xiaomi", "Mesh Triple Wall Switch (Neutral Wire)", "XMQBKG03LM"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        Converter("channel_3", "switch", mi="4.p.1"),
        Converter("led", "switch", mi="9.p.1", enabled=False),
        BoolConv("wireless_1", "switch", mi="2.p.2", enabled=False),
        BoolConv("wireless_2", "switch", mi="3.p.2", enabled=False),
        BoolConv("wireless_3", "switch", mi="4.p.2", enabled=False),
        Converter("action", "sensor", enabled=False),
        ButtonMIConv("button_1", mi="6.e.1", value=1),
        ButtonMIConv("button_2", mi="7.e.1", value=1),
        ButtonMIConv("button_3", mi="8.e.1", value=1),
        MapConv("device_fault_1", mi="2.p.3", map={
            0: "nofaults", 1: "overtemperature", 2: "overload",
            3: "overtemperature-overload"
        }),
        MapConv("device_fault_2", mi="3.p.3", map={
            0: "nofaults", 1: "overtemperature", 2: "overload",
            3: "overtemperature-overload"
        }),
        MapConv("device_fault_3", mi="4.p.3", map={
            0: "nofaults", 1: "overtemperature", 2: "overload",
            3: "overtemperature-overload"
        }),
        MathConv("power", "sensor", mi="5.p.6", round=1),
    ],
}, {
    5195: ["YKGC", "LS Smart Curtain Motor", "LSCL"],
    "spec": [
        MapConv("motor", "cover", mi="2.p.1", map={0: "stop", 1: "open", 2: "close"}),
        Converter("target_position", mi="2.p.6"),
        CurtainPosConv("position", mi="2.p.2", parent="motor"),
        Converter("motor_reverse", "switch", mi="2.p.5", enabled=False),
        BoolConv("on", "switch", mi="2.p.9"),
    ],
}, {
    10356: ["ZiQing", "IZQ Presence Sensor Lite", "IZQ-24"],
    "spec": [
        BoolConv("occupancy", "binary_sensor", mi="2.p.1"),
        MathConv("no_one_determine_time", "number", mi="2.p.2", min=0, max=10000),
        MathConv("has_someone_duration", "sensor", mi="2.p.3"),
        MathConv("idle_time", "sensor", mi="2.p.4", multiply=60),
        MathConv("illuminance", "sensor", mi="2.p.5"),
        MathConv("distance", "sensor", mi="2.p.6", multiply=0.01),

        Converter("led", "switch", mi="3.p.1", enabled=True),
        MathConv("detect_range", "number", mi="3.p.2", min=0, max=8, step=0.1),
        Converter("pir", "switch", mi="3.p.3", enabled=True),
        MathConv("enterin_confirm_time", "number", mi="3.p.5", min=0, max=60),

        MapConv("occupancy_status", "sensor", mi="2.p.1", map={
            0: "NoOne", 1: "EnterIn", 2: "SmallMove", 3: "MicroMove", 4: "Approaching",
            5: "MoveAway"
        }),
    ],
}, {
    10441: ["Linptech", "Presence Sensor ES1", "ES1ZB"],  # linp.sensor_occupy.hb01
    "spec": [
        # occupancy sensors
        BoolConv("occupancy", "binary_sensor", mi="2.p.1"),
        MathConv("occupancy_duration", "sensor", mi="2.p.3", multiply=60),  # minutes
        MathConv("occupancy_distance", "sensor", mi="3.p.3"),
        MathConv("idle_time", "sensor", mi="2.p.4", multiply=60),  # minutes

        # occupancy settings
        MathConv("occupancy_timeout", "number", mi="2.p.2", min=0, max=10000),

        MaskConv("distance_00_08", "switch", mi="3.p.2", mask=1),
        MaskConv("distance_08_15", "switch", mi="3.p.2", mask=2),
        MaskConv("distance_15_23", "switch", mi="3.p.2", mask=4),
        MaskConv("distance_23_30", "switch", mi="3.p.2", mask=8),
        MaskConv("distance_30_38", "switch", mi="3.p.2", mask=16),
        MaskConv("distance_38_45", "switch", mi="3.p.2", mask=32),
        MaskConv("distance_45_53", "switch", mi="3.p.2", mask=64),
        MaskConv("distance_53_60", "switch", mi="3.p.2", mask=128),

        # other sensors
        Converter("illuminance", "sensor", mi="2.p.5"),

        # approach/away event
        EventConv("approach_away", mi="3.e.1", value=True),
        MapConv("action", "sensor", mi="3.p.1", map={0: "", 1: "approach", 2: "away"}),
        MathConv("approach_distance", "number", mi="3.p.4", min=1, max=5),

        Converter("led", "switch", mi="4.p.1"),
    ],
}, {
    # https://home.miot-spec.com/s/ainice.sensor_occupy.rd
    13156: ["AInice", "AInice Dual Presence Sensor", "ainice-dual-presence-sensor"],
    "spec": [
        BoolConv("radar_group_occupancy", "binary_sensor", mi="3.p.2"),
        BoolConv("radar_occupancy", "binary_sensor", mi="3.p.4"),
        BoolConv("radar_enter_edge", "binary_sensor", mi="3.p.6"),
        BoolConv("bluetooth_group_online_status", "binary_sensor", mi="4.p.2"),
        BoolConv("bluetooth_group_enter_area", "binary_sensor", mi="4.p.5"),
        MathConv("illuminance", "sensor", mi="5.p.2"),
    ]
}, {
    # https://github.com/AlexxIT/XiaomiGateway3/issues/835
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:switch:0000A003:lemesh-sw1a02:1:0000C808
    3001: ["LeMesh", "Switch Sensor", "lemesh.switch.sw1a02"],
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),  # bool
        BoolConv("led", "switch", mi="5.p.1", enabled=False),  # uint8
    ],
}, {
    # https://home.miot-spec.com/s/10789
    10789: ["Zxgs", "Mesh Two Color Scene Light", "zxgs.light.bdcl01"],
    "spec": [
        Converter("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", parent="light", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", parent="light", mink=2700, maxk=6500),
    ],
}, {
    6084: ["Leishi", "NVC Smart Light Source Module Switch", "wy0a09"],
    "spec": [
        Converter("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", parent="light", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", parent="light"),
    ],
}, {
    # https://home.miot-spec.com/s/giot.plug.v3shsm
    10920: ["Unknown", "Mesh Smart Plug V3", "giot.plug.v3shsm"],
    "spec": [
        Converter("plug", "switch", mi="2.p.1"),
        MapConv("power_on_state", "select", mi="2.p.3", map={
            0: "off", 1: "on", 2: "previous"
        }),

        # Inching mode
        BoolConv("inching_mode", "switch", mi="2.p.2"),
        MapConv("inching_state", "select", mi="3.p.1", map={False: "off", True: "on"}),
        MathConv("inching_time", "number", mi="3.p.2", multiply=0.5, min=1, max=7200,
                 step=1, round=1),

        # LED
        MapConv("led", "select", mi="4.p.1", map={
            0: "follow_switch", 1: "opposite_to_switch", 2: "off", 3: "on"
        })
    ]
}, {
    # A third party module widely used in small brand wall switches
    # https://home.miot-spec.com/s/6514
    6514: ["Unknown", "Mesh Single Wall Switch (with N)", "babai.switch.201m"],
    # A third party module widely used in small brand wall switches
    # https://home.miot-spec.com/s/7219
    7219: ["Unknown", "Mesh Single Wall Switch (no N)", "babai.switch.201ml"],
    "spec": [
        Converter("channel", "switch", mi="2.p.1"),

        # Either Default/Wireless or Default/Atom, depending on hardware
        BoolConv("wireless", "switch", mi="2.p.2", enabled=False),
    ]
}, {
    # A third party module widely used in small brand wall switches
    # https://home.miot-spec.com/s/6528
    6528: ["Unknown", "Mesh Double Wall Switch (with N)", "babai.switch.202m"],
    # A third party module widely used in small brand wall switches
    # https://home.miot-spec.com/s/7220
    7220: ["Unknown", "Mesh Double Wall Switch (no N)", "babai.switch.202ml"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),

        # Either Default/Wireless or Default/Atom, depending on hard    ware
        BoolConv("wireless_1", "switch", mi="2.p.2", enabled=False),
        BoolConv("wireless_2", "switch", mi="3.p.2", enabled=False),
    ]
}, {
    # A third party module widely used in small brand wall switches
    # https://home.miot-spec.com/s/6529
    6529: ["Unknown", "Mesh Triple Wall Switch (with N)", "babai.switch.203m"],
    # A third party module widely used in small brand wall switches
    # https://home.miot-spec.com/s/7221
    7221: ["Unknown", "Mesh Triple Wall Switch (no N)", "babai.switch.203ml"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        Converter("channel_3", "switch", mi="4.p.1"),

        # Either Default/Wireless or Default/Atom, depending on hardware
        BoolConv("wireless_1", "switch", mi="2.p.2", enabled=False),
        BoolConv("wireless_2", "switch", mi="3.p.2", enabled=False),
        BoolConv("wireless_3", "switch", mi="4.p.2", enabled=False),
    ]
}, {
    # https://home.miot-spec.com/s/5045
    5045: ["Linptech", "Mesh Triple Wall Switch (no N)", "QE1SB-W3(MI)"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        Converter("channel_3", "switch", mi="4.p.1"),

        BoolConv("wireless_1", "switch", mi="2.p.3"),
        BoolConv("wireless_2", "switch", mi="3.p.3"),
        BoolConv("wireless_3", "switch", mi="4.p.3"),

        Converter("led", "switch", mi="5.p.1"),

        Converter("compatible_mode", "switch", mi="7.p.4"),

        Action,
        ButtonMIConv("button_1", mi="7.e.1", value=1),  # button_1_single
        ButtonMIConv("button_2", mi="7.e.2", value=1),  # button_2_single
        ButtonMIConv("button_3", mi="7.e.3", value=1),  # button_3_single
    ],
}, {
    # https://home.miot-spec.com/s/2428
    2428: ["Linptech", "Lingpu Single Wall Switch", "linp.switch.q3s1"],
    # https://home.miot-spec.com/spec/linp.switch.q4s1
    5043: ["Linptech", "Lingpu Single Wall Switch", "linp.switch.q4s1"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("action", "sensor", enabled=False),

        ButtonMIConv("button_1", mi="7.e.1", value=1),

        Converter("led", "switch", mi="5.p.1"),
    ],
}, {
    # https://home.miot-spec.com/spec/linp.switch.q3s2
    2429: ["Linptech", "Lingpu Double Wall Switch", "linp.switch.q3s2"],
    # https://home.miot-spec.com/spec/linp.switch.q4s2
    5044: ["Linptech", "Lingpu Double Wall Switch", "linp.switch.q4s2"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),

        BoolConv("wireless_1", "switch", mi="2.p.3"),
        BoolConv("wireless_2", "switch", mi="3.p.3"),

        Converter("led", "switch", mi="5.p.1"),

        Converter("compatible_mode", "switch", mi="7.p.4"),

        Action,
        ButtonMIConv("button_1", mi="7.e.1", value=1),
        ButtonMIConv("button_2", mi="7.e.2", value=1),
    ],
}, {
    2274: ["Linptech", "Lingpu Triple Wall Switch", "linp.switch.q3s3"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        Converter("channel_3", "switch", mi="4.p.1"),

        Converter("action", "sensor", enabled=False),

        ButtonMIConv("button_1", mi="7.e.1", value=1),
        ButtonMIConv("button_2", mi="7.e.2", value=1),
        ButtonMIConv("button_3", mi="7.e.3", value=1),

        Converter("led", "switch", mi="5.p.1"),
    ],
}, {
    # https://home.miot-spec.com/spec/chuangmi.switch.mesh
    1350: ["Chuangmi", "Single Wall Switch K1-A (with N)", "chuangmi.switch.mesh"],
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),
        MapConv("led", "switch", mi="3.p.3", map={1: False, 2: True}),
    ]
}, {
    # https://home.miot-spec.com/spec/chuangmi.switch.meshb01
    1490: ["Chuangmi", "Double Wall Switch K1-B (with N)", "chuangmi.switch.meshb01"],
    "spec": [
        Converter("left_switch", "switch", mi="2.p.1"),
        Converter("right_switch", "switch", mi="3.p.1"),
        MapConv("led", "switch", mi="4.p.3", map={1: False, 2: True}),
    ]
}, {
    # https://home.miot-spec.com/spec/chuangmi.switch.meshc01
    1489: ["Chuangmi", "Triple Wall Switch K1-C (with N)", "chuangmi.switch.meshc01"],
    "spec": [
        Converter("left_switch", "switch", mi="2.p.1"),
        Converter("middle_switch", "switch", mi="3.p.1"),
        Converter("right_switch", "switch", mi="4.p.1"),
        MapConv("led", "switch", mi="5.p.3", map={1: False, 2: True}),
    ]
}, {
    7855: ["Unknown", "Mesh Single Wall Switch (No N)", "frfox.switch.bl01"],
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),
        MapConv("mode", "select", mi="2.p.2", map={
            0: "off", 1: "wireless", 2: "flex", 3: "scene",
        }),
        Action,
        ButtonMIConv("button", mi="3.e.1", value=1),
        Converter("backlight", "switch", mi="4.p.1"),
        Converter("led", "switch", mi="4.p.2"),
    ]
}, {
    7856: ["Unknown", "Mesh Double Wall Switch (No N)", "frfox.switch.bl02"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        MapConv("mode_1", "select", mi="2.p.2", map={0: "default", 1: "wireless", 2: "flex", 3: "scene"}),
        MapConv("mode_2", "select", mi="3.p.2", map={0: "default", 1: "wireless", 2: "flex", 3: "scene"}),
        Action,
        ButtonMIConv("button_1", mi="4.e.1", value=1),
        ButtonMIConv("button_2", mi="5.e.1", value=1),
        Converter("backlight", "switch", mi="6.p.1"),
        Converter("led", "switch", mi="6.p.2"),
    ]
}, {
    11253: ["LianXun", "Smart Switch Four-key Mesh", "lxun.switch.lxswm4"],
    "spec": [
        Converter("switch_1", "switch", mi="2.p.1"),
        Converter("switch_2", "switch", mi="3.p.1"),
        Converter("switch_3", "switch", mi="4.p.1"),
        Converter("switch_4", "switch", mi="12.p.1"),
        MapConv("backlight", "select", mi="5.p.1", map={0: "off", 1: "on"}),
        MapConv("backlight_1", "select", mi="9.p.1", map={1: "reverse", 2: "open", 3: "close", 4: "flash"}),
        MapConv("backlight_2", "select", mi="9.p.2", map={1: "reverse", 2: "open", 3: "close", 4: "flash"}),
        MapConv("backlight_3", "select", mi="9.p.3", map={1: "reverse", 2: "open", 3: "close", 4: "flash"}),
        MapConv("backlight_4", "select", mi="9.p.4", map={1: "reverse", 2: "open", 3: "close", 4: "flash"}),
        MapConv("mode_1", "select", mi="10.p.1", map={1: "normal", 2: "scene", 3: "flex"}),
        MapConv("mode_2", "select", mi="10.p.2", map={1: "normal", 2: "scene", 3: "flex"}),
        MapConv("mode_3", "select", mi="10.p.3", map={1: "normal", 2: "scene", 3: "flex"}),
        MapConv("mode_4", "select", mi="10.p.4", map={1: "normal", 2: "scene", 3: "flex"}),
        Action,
        ButtonMIConv("button_1", mi="11.e.1", value=1),
        ButtonMIConv("button_2", mi="11.e.2", value=1),
        ButtonMIConv("button_3", mi="11.e.3", value=1),
        ButtonMIConv("button_4", mi="11.e.4", value=1),
        ButtonMIConv("button_1", mi="11.e.5", value=2),
        ButtonMIConv("button_2", mi="11.e.6", value=2),
        ButtonMIConv("button_3", mi="11.e.7", value=2),
        ButtonMIConv("button_4", mi="11.e.8", value=2),
        ButtonMIConv("button_1", mi="11.e.9", value=16),
        ButtonMIConv("button_2", mi="11.e.10", value=16),
        ButtonMIConv("button_3", mi="11.e.11", value=16),
        ButtonMIConv("button_4", mi="11.e.12", value=16),
    ]
}, {
    12987: ["LianXun", "Smart Switch 8-key Mesh", "lxun.switch.sw08"],
    "spec": [
        Converter("switch_1", "switch", mi="2.p.1"),
        Converter("switch_2", "switch", mi="3.p.1"),
        Converter("switch_3", "switch", mi="4.p.1"),
        Converter("switch_4", "switch", mi="12.p.1"),
        MapConv("backlight", "select", mi="5.p.1", map={0: "off", 1: "on"}),
        MapConv("backlight_1", "select", mi="9.p.1", map={1: "reverse", 2: "open", 3: "close", 4: "flash"}),
        MapConv("backlight_2", "select", mi="9.p.2", map={1: "reverse", 2: "open", 3: "close", 4: "flash"}),
        MapConv("backlight_3", "select", mi="9.p.3", map={1: "reverse", 2: "open", 3: "close", 4: "flash"}),
        MapConv("backlight_4", "select", mi="9.p.4", map={1: "reverse", 2: "open", 3: "close", 4: "flash"}),
        MapConv("backlight_5", "select", mi="9.p.5", map={1: "reverse", 2: "open", 3: "close", 4: "flash"}),
        MapConv("backlight_6", "select", mi="9.p.6", map={1: "reverse", 2: "open", 3: "close", 4: "flash"}),
        MapConv("backlight_7", "select", mi="9.p.7", map={1: "reverse", 2: "open", 3: "close", 4: "flash"}),
        MapConv("backlight_8", "select", mi="9.p.8", map={1: "reverse", 2: "open", 3: "close", 4: "flash"}),
        MapConv("mode_1", "select", mi="10.p.1", map={1: "normal", 2: "scene", 3: "flex"}),
        MapConv("mode_2", "select", mi="10.p.2", map={1: "normal", 2: "scene", 3: "flex"}),
        MapConv("mode_3", "select", mi="10.p.3", map={1: "normal", 2: "scene", 3: "flex"}),
        MapConv("mode_4", "select", mi="10.p.4", map={1: "normal", 2: "scene", 3: "flex"}),
        Action,
        ButtonMIConv("button_1", mi="11.e.1", value=1),
        ButtonMIConv("button_2", mi="11.e.2", value=1),
        ButtonMIConv("button_3", mi="11.e.3", value=1),
        ButtonMIConv("button_4", mi="11.e.4", value=1),
        ButtonMIConv("button_1", mi="11.e.5", value=2),
        ButtonMIConv("button_2", mi="11.e.6", value=2),
        ButtonMIConv("button_3", mi="11.e.7", value=2),
        ButtonMIConv("button_4", mi="11.e.8", value=2),
        ButtonMIConv("button_1", mi="11.e.9", value=16),
        ButtonMIConv("button_2", mi="11.e.10", value=16),
        ButtonMIConv("button_3", mi="11.e.11", value=16),
        ButtonMIConv("button_4", mi="11.e.12", value=16),
        ButtonMIConv("button_5", mi="11.e.13", value=1),
        ButtonMIConv("button_6", mi="11.e.14", value=1),
        ButtonMIConv("button_7", mi="11.e.15", value=1),
        ButtonMIConv("button_8", mi="11.e.16", value=1),
        ButtonMIConv("button_5", mi="11.e.17", value=2),
        ButtonMIConv("button_6", mi="11.e.18", value=2),
        ButtonMIConv("button_7", mi="11.e.19", value=2),
        ButtonMIConv("button_8", mi="11.e.20", value=2),
        ButtonMIConv("button_5", mi="11.e.21", value=16),
        ButtonMIConv("button_6", mi="11.e.22", value=16),
        ButtonMIConv("button_7", mi="11.e.23", value=16),
        ButtonMIConv("button_8", mi="11.e.24", value=16),
    ]
}, {
    7857: ["Unknown", "Mesh Triple Wall Switch (No N)", "frfox.switch.bl03"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        MapConv("mode_1", "select", mi="2.p.2", map={
            0: "default", 1: "wireless", 2: "flex", 3: "scene",
        }),
        Converter("channel_2", "switch", mi="3.p.1"),
        MapConv("mode_2", "select", mi="3.p.2", map={
            0: "default", 1: "wireless", 2: "flex", 3: "scene",
        }),
        Converter("channel_3", "switch", mi="4.p.1"),
        MapConv("mode_3", "select", mi="4.p.2", map={
            0: "default", 1: "wireless", 2: "flex", 3: "scene",
        }),
        Action,
        ButtonMIConv("button_1", mi="5.e.1", value=1),
        ButtonMIConv("button_2", mi="6.e.1", value=1),
        ButtonMIConv("button_3", mi="7.e.1", value=1),
        Converter("backlight", "switch", mi="8.p.1"),
        Converter("led", "switch", mi="8.p.2"),
    ]
}, {
    10939: ["Linptech", "Sliding Window Driver WD1", "WD1"],
    "spec": [
        MapConv("motor", "cover", mi="2.p.1", map={
            0: "stop", 1: "open", 2: "close"
        }),
        Converter("target_position", mi="2.p.3"),
        CurtainPosConv("position", mi="2.p.2", parent="motor"),
        Converter("battery", "sensor", mi="3.p.1"),
        Converter("security_mode", "switch", mi="4.p.6"),
        Converter("power_replenishment", "sensor", mi="7.p.1", enabled=None),
        Converter("realtime_current_in", "sensor", mi="7.p.2", enabled=None),
    ],
}, {
    # https://home.miot-spec.com/spec/yeelink.curtain.crc1
    10813: ["Yeelink", "Curtain Motor C1", "YCCBCI008"],
    "spec": [
        MapConv("motor", "cover", mi="2.p.1", map={0: "stop", 1: "open", 2: "close"}),
        Converter("target_position", mi="2.p.2"),
        CurtainPosConv("position", mi="2.p.3", parent="motor"),
        Converter("motor_reverse", "switch", mi="2.p.4", enabled=False),
        MapConv("mode", "select", mi="2.p.5", map={
            0: "default", 1: "doublmode", 2: "leftmode", 3: "rightmode"
        }, enabled=False),
    ],
    "ttl": "7d",
}, {
    # https://home.miot-spec.com/spec/090615.curtain.crus6
    15069: ["PTX", "Curtain Motor", "crus6"],
    "spec": [
        MapConv("motor", "cover", mi="2.p.1", map={0: "stop", 1: "open", 2: "close"}),
        Converter("target_position", mi="2.p.2"),
        CurtainPosConv("position", mi="2.p.3", parent="motor"),
        Converter("motor_reverse", "switch", mi="2.p.4", enabled=False),
        MapConv("mode", "select", mi="2.p.5", map={
            0: "default", 1: "doublmode", 2: "leftmode", 3: "rightmode"
        }, enabled=False),
        MapConv("run_state", mi="2.p.6", parent="motor", map={
            0: "stop", 1: "opening", 2: "closing"
        }),
        MapConv("fault", "sensor", mi="2.p.7", map={
            0: "No faults", 1: "Faults"}, enabled=False),
    ],
    "ttl": "7d",
}, {
    4722: ["Xiaomi", "Curtain Motor", "MJZNCL02LM"],
    "spec": [
        MapConv("motor", "cover", mi="2.p.1", map={
            0: "stop", 1: "open", 2: "close"
        }),
        Converter("target_position", mi="2.p.2"),
        CurtainPosConv("position", mi="2.p.6", parent="motor"),
        MapConv("run_state", mi="2.p.3", parent="motor", map={
            0: "stop", 1: "opening", 2: "closing", 3: "busy"
        }),
        Converter("battery", "sensor", mi="5.p.1"),  # percent
        Converter("motor_reverse", "switch", mi="2.p.5", enabled=False),
        MapConv("battery_charging", "binary_sensor", mi="5.p.2", map={
            1: True, 2: False, 3: False,
        }, enabled=False),
    ],
}, {
    # https://home.miot-spec.com/spec/giot.curtain.v5icm
    13804: ["giot", "Curtain Motor", "v5icm"],
    "spec": [
        MapConv("motor", "cover", mi="2.p.1", map={0: "stop", 1: "open", 2: "close"}),
        Converter("target_position", mi="2.p.7"),
        CurtainPosConv("position", mi="2.p.6", parent="motor"),
        Converter("motor_reverse", "switch", mi="2.p.8", enabled=False),
        Converter("battery", "sensor", mi="3.p.1"),
    ],
    "ttl": "7d",
}, {
    # https://home.miot-spec.com/spec/giot.light.v5ssm
    11724: ["GranwinIoT", "Mesh Light V5", "giot.light.v5ssm"],
    "spec": [
        Converter("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", parent="light", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", parent="light", mink=2700, maxk=6500),
        MapConv("mode", "select", mi="2.p.4", map={
            0: "Auto", 1: "Day", 2: "Night", 3: "Warmth", 4: "TV", 5: "Reading",
            6: "Computer", 7: "Sleeping Aid", 8: "Wakeup Aid",
        }),
        Converter("flex_switch", "switch", mi="2.p.5"),

        # Converter("ac_status", "sensor", mi="3.p.1"),

        MapConv("power_on_state", "select", mi="3.p.2", map={0: "off", 1: "on"}),
        MapConv("turn_on_state", "select", mi="3.p.3",
                map={0: "previous", 1: "default"}),

        MathConv("default_brightness", "number", mi="3.p.4", min=1, max=100),
        MathConv("default_temp", "number", mi="3.p.5", min=2700, max=6500),

        MathConv("sleep_aid_minutes", "number", mi="3.p.7", min=1, max=60),
        Converter("sleep_aid_use_custom", "switch", mi="3.p.8"),
        MathConv("sleep_aid_custom_init_brightness", "number", mi="3.p.9", min=1,
                 max=100),
        MathConv("sleep_aid_custom_init_temp", "number", mi="3.p.10", min=2700,
                 max=6500),

        MathConv("wakeup_minutes", "number", mi="3.p.11", min=1, max=60),
        Converter("wakeup_use_custom", "switch", mi="3.p.12"),
        MathConv("wakeup_custom_final_brightness", "number", mi="3.p.13", min=1,
                 max=100),
        MathConv("wakeup_custom_final_temp", "number", mi="3.p.14", min=2700, max=6500),

        Converter("night_light", "switch", mi="3.p.15"),
        MathConv("turn_on_transit_sec", "number", mi="3.p.17", multiply=0.001, min=100,
                 max=30000, step=100, round=1),
        MathConv("turn_off_transit_sec", "number", mi="3.p.18", multiply=0.001, min=100,
                 max=30000, step=100, round=1),
        MathConv("change_transit_sec", "number", mi="3.p.19", multiply=0.001, min=100,
                 max=30000, step=100, round=1),

        MathConv("min_brightness", "number", mi="3.p.23", multiply=0.1, min=1, max=500,
                 step=1, round=1),

        GiotTimePatternConv("night_light_time", "text", mi="3.p.16")

        # Converter("fill_light_detection", "sensor", mi="3.p.20"),
        # Converter("fill_light_switch", "switch", mi="3.p.21"),
        # MathConv("min_bri_factory", "number", mi="3.p.16", min=1, max=500),
    ]
}, {
    # https://home.miot-spec.com/spec/opple.light.barelp
    3661: ["Opple", "Bare Light Panel", "opple.light.barelp"],
    "spec": [
        Converter("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", parent="light", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", parent="light", mink=3000, maxk=5700),
        MapConv("mode", "select", mi="2.p.4", map={
            0: "Reception", 1: "Entertainment", 2: "Cinema", 3: "Night", 4: "Wakeup", 5: "Sleep",
            6: "Sunset", 7: "None", 8: "Invert"
        }),
    ],
}, {
    # https://home.miot-spec.com/spec/lemesh.switch.sw0a04
    13586: ["LeMesh", "Mesh Switch Controller V2S", "lemesh.switch.sw0a04"],
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),  # Tested
        MapConv("power_on_state", "select", mi="2.p.2", map={0: "previous", 1: "on", 2: "off"},
                enabled=False),  # Tested
        BoolConv("flex_switch", "switch", mi="3.p.4", enabled=False),  # uint8 # Tested
    ],
}, {
    # https://home.miot-spec.com/spec/090615.curtain.s2mesh
    # run_state attribute is not available according to the spec
    6461: ["PTX", "Smart Curtain Motor", "090615.curtain.s2mesh"],
    "spec": [
        MapConv("motor", "cover", mi="2.p.1", map={0: "stop", 1: "open", 2: "close"}),
        Converter("target_position", mi="2.p.2"),
        CurtainPosConv("position", mi="2.p.3", parent="motor"),
        Converter("motor_reverse", "switch", mi="2.p.4", enabled=False),
    ],
}, {
    # https://home.miot-spec.com/spec/giot.switch.v53ksm
    13140: ["GranwinIoT", "Smart three-Button Switch (Mesh) V5", "giot.switch.v53ksm"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        Converter("channel_3", "switch", mi="4.p.1"),
        Converter("switch_status_1", "switch", mi="11.p.1"),
        Converter("switch_status_2", "switch", mi="12.p.1"),
        Converter("switch_status_3", "switch", mi="13.p.1"),
        MapConv("mode_1", "select", mi="2.p.2", map={
            0: "normal_switch", 1: "wireless_switch", 2: "smart_switch", 3: "toggle_switch"
        }),
        MapConv("mode_2", "select", mi="3.p.2", map={
            0: "normal_switch", 1: "wireless_switch", 2: "smart_switch", 3: "toggle_switch"
        }),
        MapConv("mode_3", "select", mi="4.p.2", map={
            0: "normal_switch", 1: "wireless_switch", 2: "smart_switch", 3: "toggle_switch"
        }),
    ]
}, {
    # https://home.miot-spec.com/spec/giot.switch.v54ksm
    13141: ["GranwinIoT", "Smart four-Button Switch (Mesh) V5", "giot.switch.v54ksm"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        Converter("channel_3", "switch", mi="4.p.1"),
        Converter("channel_4", "switch", mi="5.p.1"),
        Converter("switch_status_1", "switch", mi="11.p.1"),
        Converter("switch_status_2", "switch", mi="12.p.1"),
        Converter("switch_status_3", "switch", mi="13.p.1"),
        Converter("switch_status_4", "switch", mi="14.p.1"),
        MapConv("mode_1", "select", mi="2.p.2", map={
            0: "normal_switch", 1: "wireless_switch", 2: "smart_switch", 3: "toggle_switch"
        }),
        MapConv("mode_2", "select", mi="3.p.2", map={
            0: "normal_switch", 1: "wireless_switch", 2: "smart_switch", 3: "toggle_switch"
        }),
        MapConv("mode_3", "select", mi="4.p.2", map={
            0: "normal_switch", 1: "wireless_switch", 2: "smart_switch", 3: "toggle_switch"
        }),
        MapConv("mode_4", "select", mi="5.p.2", map={
            0: "normal_switch", 1: "wireless_switch", 2: "smart_switch", 3: "toggle_switch"
        }),
    ]
}, {
    9612: ["Unkown", "Mesh Singel Wall Switch", "bean.switch.bl01"],
    "spec": [
        Converter("switch_1", "switch", mi="2.p.1"),
        MapConv("mode_1", "select", mi="2.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),
        Action,
        ButtonMIConv("button_1", mi="3.e.1", value=1),
    ]
}, {
    9613: ["Unkown", "Mesh Double Wall Switch", "bean.switch.bl02"],
    "spec": [
        Converter("switch_1", "switch", mi="2.p.1"),
        Converter("switch_2", "switch", mi="3.p.1"),
        MapConv("mode_1", "select", mi="2.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),
        MapConv("mode_2", "select", mi="3.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),
        Action,
        ButtonMIConv("button_1", mi="4.e.1", value=1),
        ButtonMIConv("button_2", mi="5.e.1", value=1),
    ]
}, {
    9614: ["Unkown", "Mesh Triple Wall Switch", "bean.switch.bl03"],
    "spec": [
        Converter("switch_1", "switch", mi="2.p.1"),
        Converter("switch_2", "switch", mi="3.p.1"),
        Converter("switch_3", "switch", mi="4.p.1"),
        MapConv("mode_1", "select", mi="2.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),
        MapConv("mode_2", "select", mi="3.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),
        MapConv("mode_3", "select", mi="4.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),
        Action,
        ButtonMIConv("button_1", mi="5.e.1", value=1),
        ButtonMIConv("button_2", mi="6.e.1", value=1),
        ButtonMIConv("button_3", mi="7.e.1", value=1),
    ]
}, {
    10147: ["Unkown", "Mesh Four-Key Wall Switch", "bean.switch.bln04"],
    "spec": [
        Converter("switch_1", "switch", mi="2.p.1"),
        Converter("switch_2", "switch", mi="3.p.1"),
        Converter("switch_3", "switch", mi="4.p.1"),
        Converter("switch_4", "switch", mi="5.p.1"),
        MapConv("mode_1", "select", mi="2.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),
        MapConv("mode_2", "select", mi="3.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),
        MapConv("mode_3", "select", mi="4.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),
        MapConv("mode_4", "select", mi="5.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),
        Action,
        ButtonMIConv("button_1", mi="6.e.1", value=1),
        ButtonMIConv("button_2", mi="7.e.1", value=1),
        ButtonMIConv("button_3", mi="8.e.1", value=1),
        ButtonMIConv("button_4", mi="9.e.1", value=1),
    ],
}, {
    14431: ["Xiaomi", "Xiaomi Smart Wall Switch Pro (1 Gang)", "XMQBKG04LM"],
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),
        Converter("action", "sensor", enabled=False),
        ButtonMIConv("button_1", mi="3.e.1", value=1),
        MapConv("fault", "sensor", mi="2.p.3",
                map={0: "No Faults", 1: "Over Temperature", 2: "Overload", 3: "Overload And Overheat"}),
        MathConv("power", "sensor", mi="4.p.2", round=1),
        Converter("led", "light", mi="5.p.1"),
    ],
}, {
    14432: ["Xiaomi", "Xiaomi Smart Wall Switch Pro (2 Gang)", "XMQBKG05LM"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        Converter("action", "sensor", enabled=False),
        ButtonMIConv("button_1", mi="4.e.1", value=1),
        ButtonMIConv("button_2", mi="5.e.1", value=1),
        MapConv("fault", "sensor", mi="2.p.3",
                map={0: "No Faults", 1: "Over Temperature", 2: "Overload", 3: "Overload And Overheat"}),
        MathConv("power", "sensor", mi="6.p.2", round=1),
        Converter("led", "light", mi="7.p.1"),
    ],
}, {
    14433: ["Xiaomi", "Xiaomi Smart Wall Switch Pro (3 Gang)", "XMQBKG06LM"],
    "spec": [
        Converter("channel_1", "switch", mi="2.p.1"),
        Converter("channel_2", "switch", mi="3.p.1"),
        Converter("channel_3", "switch", mi="4.p.1"),
        Converter("action", "sensor", enabled=False),
        ButtonMIConv("button_1", mi="5.e.1", value=1),
        ButtonMIConv("button_2", mi="6.e.1", value=1),
        ButtonMIConv("button_3", mi="7.e.1", value=1),
        MapConv("fault", "sensor", mi="2.p.3",
                map={0: "No Faults", 1: "Over Temperature", 2: "Overload", 3: "Overload And Overheat"}),
        MathConv("power", "sensor", mi="8.p.2", round=1),
        Converter("led", "light", mi="9.p.1"),
    ],
}, {
    13521: ["Xiaomi", "Xiaomi Smart Wall Outlet Pro", "XMZNCZ01LM"],
    "spec": [
        Converter("outlet", "switch", mi="2.p.1"),
        MapConv("power_on_state", "switch", mi="2.p.2", map={0: True, 1: False}),
        MapConv("fault", "sensor", mi="2.p.3",
                map={0: "No Faults", 1: "Over Temperature", 2: "Overload", 3: "Overload And Overheat"}),
        MathConv("power", "sensor", mi="3.p.6", round=1),
        Converter("led", "light", mi="4.p.1"),
    ],
}, {
    7082: ["pmfbj", "Panasonic Ceiling Light", "pmfbj.light.xsx340"],
    6857: ["pmfbj", "Panasonic Ceiling Light", "pmfbj.light.xsx341"],
    # https://home.miot-spec.com/s/pmfbj.light.xsx340
    # https://home.miot-spec.com/s/pmfbj.light.xsx341
    "spec": [
        Converter("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", parent="light", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", parent="light", mink=2700, maxk=6500),
        MapConv("effect", mi="2.p.4", parent="light", map={
            0: "Default", 1: "Daily", 2: "Leisure", 3: "Comfortable", 4: "Night", 5: "SY"
        })
    ]
}, {
    6435: ["PTX", "PTX Smart Quadruple Switch", "sk4k"],
    "spec": [
        Converter("switch_1", "switch", mi="2.p.1"),
        Converter("switch_2", "switch", mi="3.p.1"),
        Converter("switch_3", "switch", mi="4.p.1"),
        Converter("switch_4", "switch", mi="5.p.1"),
        MapConv("mode_1", "select", mi="2.p.2", map={0: "Wired And Wireless", 1: "Wireless"}),
        MapConv("mode_2", "select", mi="3.p.2", map={0: "Wired And Wireless", 1: "Wireless"}),
        MapConv("mode_3", "select", mi="4.p.2", map={0: "Wired And Wireless", 1: "Wireless"}),
        MapConv("mode_4", "select", mi="5.p.2", map={0: "Wired And Wireless", 1: "Wireless"}),
        Converter("backlight", "switch", mi="8.p.1"),
    ],
}, {
    # https://home.miot-spec.com/s/giot.plug.v3oodm
    10944: ["Unknown", "Mesh Smart Switch V3", "giot.switch.v3oodm"],
    "spec": [
        Converter("switch", "switch", mi="2.p.1"),
        MapConv("power_on_state", "select", mi="2.p.3", map={
            0: "off", 1: "on", 2: "previous"
        }),

        # Inching mode
        BoolConv("inching_mode", "switch", mi="2.p.2"),
        MapConv("inching_state", "select", mi="3.p.1", map={False: "off", True: "on"}),
        MathConv("inching_time", "number", mi="3.p.2", multiply=0.5, min=1, max=7200,
                 step=1, round=1),

        # LED
        MapConv("led", "select", mi="4.p.1", map={
            0: "follow_switch", 1: "opposite_to_switch", 2: "off", 3: "on"
        })
    ]
}, {
    "default": "mesh",  # default Mesh device
    "spec": [
        Converter("switch", "switch", mi="2.p.1", enabled=None),  # bool
    ],
}]
