"""
Each device has a specification:

    {
        "<model>": ["<brand>", "<name>", "<market model>", "<other model>"],
        "spec": [<list of converters>],
        "ttl": <time to live>
    }

- model - `lumi.xxx` for Zigbee devices, number (pdid) for BLE and Mesh devices
- spec - list of converters
- ttl - optional available timeout

Each converter has:

    Converter(<attribute name>, <hass domain>, <mi name>)

- attribute - required, entity or attribute name in Hass
- domain - optional, hass entity type (`sensor`, `switch`, `binary_sensor`...)
- mi - optional, item name in:
   - Lumi spec `mi="8.0.2012"`
   - MIoT spec `mi="2.p.1"` or `mi="2.e.1"` or `mi="3.e.1012.p.1"`
   - MiBeacon spec `mi=4100`

Old Zigbee devices uses Lumi format, new Zigbee 3 and Mesh devices uses MIoT format.

Converter may have different types:

- BaseConv - default, don't change/convert value
- BoolConv - converts int to bool on decode and bool to int on encode
- MapConv - translate value using mapping: `{0: "disarmed", 1: "armed_home"}`
- MathConv - support multiply, round value and min/max borders
- and many others...

For MIoT bool properties you should use `BaseConv`. For MIoT uint8 properties you
should use `BoolConv`.

If converter has `entity=ENTITY_LAZY` - it will work, but entity will setup only with
first data from device. Useful if we don't know exact spec of device. Example, battery
not exist on some firmwares of some devices.

The name of the attribute defines the device class, icon and unit of measure.
Recommended attributes names:

- `motion` - the sensor can only send motion detection (timeout in Hass)
- `occupancy` - the sensor can send motion start and motion stop
- `plug` - for sockets with male connector
- `outlet` - for sockets with only female connector (wall installation)
- `switch` - for relays and switches with buttons (wall installation, remotes)
- `led` - control device led light
- `wireless` - change mode from wired to wireless (decoupled)
- `power_on_state` - default state when electricity is supplied
- `contact` - for door/windor sensor (zigbee2mqtt - contact, hass - door or window)
- `water_leak` - for water leak sensor (zigbee2mqtt - water_leak, hass - moisture)

Nice project with MIoT spec description: https://home.miot-spec.com/
"""
from .converters.base import *
from .converters.const import *
from .converters.lumi import *
from .converters.mesh import *
from .converters.mibeacon import *
from .converters.zigbee import *

# Disable Black formatter and ignore line width
# fmt: off

# Gateways (lumi and miot specs)
DEVICES = [{
    "lumi.gateway.mgl03": ["Xiaomi", "Multimode Gateway", "ZNDMWG03LM", "ZNDMWG02LM", "YTC4044GL"],
    "spec": [
        # write pair=60 => report discovered_mac => report 8.0.2166? => write pair_command => report added_device => write pair=0
        MapConv("pair", mi="8.0.2109", map={60: True, 0: False}),

        BaseConv("discovered_mac", mi="8.0.2110"),
        BaseConv("pair_command", mi="8.0.2111"),
        BaseConv("added_device", mi="8.0.2084"),
        BaseConv("remove_did", mi="8.0.2082"),

        BaseConv("z3_version", mi="8.0.2080"),  # can be read
        BaseConv("z3_info", mi="8.0.2166"),
        BaseConv("ota", mi="8.0.2091"),  # percent

        # support change with remote.send_command
        BaseConv("power_tx", mi="8.0.2012"),
        BaseConv("channel", mi="8.0.2024"),

        BaseConv("command", "select"),
        BaseConv("data", "select"),

        MapConv("alarm", "alarm_control_panel", mi="3.p.1", map={0: "disarmed", 1: "armed_home", 2: "armed_away", 3: "armed_night"}),
        BoolConv("alarm_trigger", "switch", mi="3.p.22"),
        BoolConv("led", "switch", mi="6.p.6"),
    ],
}, {
    "lumi.gateway.aqcn02": ["Aqara", "Hub E1 CN", "ZHWG16LM"],
    "lumi.gateway.aqcn03": ["Aqara", "Hub E1 EU", "HE1-G01"],
    "lumi.gateway.mcn001": ["Xiaomi", "Multimode Gateway 2 CN", "DMWG03LM"],
    "lumi.gateway.mgl001": ["Xiaomi", "Multimode Gateway 2 EU", "ZNDMWG04LM", "BHR6765GL"],
    "spec": [
        MapConv("pair", mi="8.0.2109", map={60: True, 0: False}),

        BaseConv("discovered_mac", mi="8.0.2110"),
        BaseConv("pair_command", mi="8.0.2111"),
        BaseConv("added_device", mi="8.0.2084"),
        BaseConv("remove_did", mi="8.0.2082"),  # support change

        BaseConv("power_tx", mi="8.0.2012"),  # support change
        BaseConv("channel", mi="8.0.2024"),  # support change
        BaseConv("pan_id", mi="8.0.2157"),

        BaseConv("command", "select"),
        BaseConv("data", "select"),

        MapConv("led", "light", mi="6.p.1", map={0: True, 1: False}, entity=ENTITY_CONFIG),  # dnd mode for mgl001
        BrightnessConv("brightness", mi="6.p.3"),  # works only for Multimode 2

        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="4.e.1", value=BUTTON_SINGLE),
        ConstConv("action", mi="4.e.2", value=BUTTON_DOUBLE),
        ConstConv("action", mi="4.e.3", value=BUTTON_HOLD),
    ],
}]

# Zigbee (lumi spec)
DEVICES += [{
    # don't work: protect 8.0.2014, power 8.0.2015, plug_detection 8.0.2044
    "lumi.plug": ["Xiaomi", "Plug CN", "ZNCZ02LM"],  # tested
    "lumi.plug.mitw01": ["Xiaomi", "Plug TW", "ZNCZ03LM"],
    "lumi.plug.maus01": ["Xiaomi", "Plug US", "ZNCZ12LM"],
    "support": 5,  # @AlexxIT
    "spec": [
        BoolConv("plug", "switch", mi="4.1.85"),
        MathConv("power", "sensor", mi="0.12.85", round=2),
        MathConv("energy", "sensor", mi="0.13.85", multiply=0.001, round=2),
        BaseConv("chip_temperature", "sensor", mi="8.0.2006"),  # diagnostic
        MapConv("power_on_state", "select", mi="8.0.2030", map={0: "off", 1: "previous"}),  # config
        BoolConv("charge_protect", "switch", mi="8.0.2031"),  # config
        BoolConv("led", "switch", mi="8.0.2032"),  # config
        # Converter("max_power", "sensor", mi="8.0.2042", entity=ENTITY_DISABLED),
    ],
}, {
    "lumi.plug.mmeu01": ["Xiaomi", "Plug EU", "ZNCZ04LM"],
    "spec": [
        BoolConv("plug", "switch", mi="4.1.85"),
        MathConv("power", "sensor", mi="0.12.85", round=2),
        MathConv("voltage", "sensor", mi="0.11.85", multiply=0.001, round=2),
        MathConv("energy", "sensor", mi="0.13.85", multiply=0.001, round=2),
        BoolConv("plug_detection", "binary_sensor", mi="8.0.2044"),
        BaseConv("chip_temperature", "sensor", mi="8.0.2006"),  # diagnostic
        MapConv("power_on_state", "select", mi="8.0.2030", map={0: "off", 1: "previous"}),  # config
    ],
}, {
    "lumi.ctrl_86plug.aq1": ["Aqara", "Wall Outlet", "QBCZ11LM"],
    "lumi.ctrl_86plug": ["Aqara", "Wall Outlet", "QBCZ11LM"],
    "spec": [
        BoolConv("outlet", "switch", mi="4.1.85"),
        MathConv("power", "sensor", mi="0.12.85", round=2),
        MathConv("energy", "sensor", mi="0.13.85", multiply=0.001, round=2),
        BaseConv("chip_temperature", "sensor", mi="8.0.2006"),  # diagnostic
        MapConv("power_on_state", "select", mi="8.0.2030", map={0: "off", 1: "previous"}),  # config
        BoolConv("charge_protect", "switch", mi="8.0.2031"),  # config
        BoolConv("led", "switch", mi="8.0.2032"),  # config
        BoolConv("wireless", "switch", mi="4.10.85"),  # config
    ],
}, {
    "lumi.ctrl_ln1.aq1": ["Aqara", "Single Wall Switch", "QBKG11LM"],
    "lumi.ctrl_ln1": ["Aqara", "Single Wall Switch", "QBKG11LM"],
    "lumi.switch.b1nacn02": ["Aqara", "Single Wall Switch D1 (with N)", "QBKG23LM"],
    "spec": [
        BoolConv("switch", "switch", mi="4.1.85"),
        MathConv("power", "sensor", mi="0.12.85", round=2),
        MathConv("energy", "sensor", mi="0.13.85", multiply=0.001, round=2),
        BaseConv("action", "sensor"),
        ButtonConv("button", mi="13.1.85"),
        BoolConv("wireless", "switch", mi="4.10.85"),  # config
        BoolConv("led", "switch", mi="8.0.2032"),  # config
    ],
}, {
    "lumi.ctrl_neutral1": ["Aqara", "Single Wall Switch", "QBKG04LM"],
    "lumi.switch.b1lacn02": ["Aqara", "Single Wall Switch D1 (no N)", "QBKG21LM"],
    "spec": [
        BoolConv("switch", "switch", mi="4.1.85"),
        BaseConv("action", "sensor"),
        ButtonConv("button", mi="13.1.85"),
        BoolConv("wireless", "switch", mi="4.10.85"),  # config
        BoolConv("led", "switch", mi="8.0.2032"),  # config
    ],
}, {
    # dual channel on/off, power measurement
    "lumi.ctrl_ln2.aq1": ["Aqara", "Double Wall Switch", "QBKG12LM"],
    "lumi.ctrl_ln2": ["Aqara", "Double Wall Switch", "QBKG12LM"],
    "lumi.switch.b2nacn02": ["Aqara", "Double Wall Switch D1 (with N)", "QBKG24LM"],
    "spec": [
        BoolConv("channel_1", "switch", mi="4.1.85"),
        BoolConv("channel_2", "switch", mi="4.2.85"),
        MathConv("power", "sensor", mi="0.12.85", round=2),
        MathConv("energy", "sensor", mi="0.13.85", multiply=0.001, round=2),
        BaseConv("action", "sensor"),
        ButtonConv("button_1", mi="13.1.85"),
        ButtonConv("button_2", mi="13.2.85"),
        ButtonConv("button_both", mi="13.5.85"),
        BoolConv("wireless_1", "switch", mi="4.10.85"),  # config
        BoolConv("wireless_2", "switch", mi="4.11.85"),  # config
        MapConv("power_on_state", "select", mi="8.0.2030", map={0: "off", 1: "previous"}),  # config
        BoolConv("led", "switch", mi="8.0.2032"),  # config
    ],
}, {
    "lumi.relay.c2acn01": ["Aqara", "Relay CN", "LLKZMK11LM"],  # tested
    "support": 4,  # @AlexxIT
    "spec": [
        BoolConv("channel_1", "switch", mi="4.1.85"),
        BoolConv("channel_2", "switch", mi="4.2.85"),
        MathConv("current", "sensor", mi="0.14.85", multiply=0.001, round=2),
        MathConv("power", "sensor", mi="0.12.85", round=2),
        MathConv("voltage", "sensor", mi="0.11.85", multiply=0.001, round=2),
        MathConv("energy", "sensor", mi="0.13.85", multiply=0.001, round=2),
        BaseConv("action", "sensor"),
        ButtonConv("button_1", mi="13.1.85"),
        ButtonConv("button_2", mi="13.2.85"),
        ButtonConv("button_both", mi="13.5.85"),
        MapConv("power_on_state", "select", mi="8.0.2030", map={0: "off", 1: "previous"}),  # config
        BoolConv("interlock", "switch", mi="4.9.85", entity=ENTITY_CONFIG),
        BaseConv("chip_temperature", "sensor", mi="8.0.2006"),  # diagnostic
    ],
}, {
    "lumi.ctrl_neutral2": ["Aqara", "Double Wall Switch (no N)", "QBKG03LM"],
    "lumi.switch.b2lacn02": ["Aqara", "Double Wall Switch D1 (no N)", "QBKG22LM"],
    "spec": [
        BoolConv("channel_1", "switch", mi="4.1.85"),
        BoolConv("channel_2", "switch", mi="4.2.85"),
        BaseConv("action", "sensor"),
        ButtonConv("button_1", mi="13.1.85"),
        ButtonConv("button_2", mi="13.2.85"),
        ButtonConv("button_both", mi="13.5.85"),
        BoolConv("wireless_1", "switch", mi="4.10.85"),  # config
        BoolConv("wireless_2", "switch", mi="4.11.85"),  # config
        BoolConv("led", "switch", mi="8.0.2032"),  # config
    ],
}, {
    # triple channel on/off, no neutral wire
    "lumi.switch.l3acn3": ["Aqara", "Triple Wall Switch D1 (no N)", "QBKG25LM"],
    "spec": [
        BoolConv("channel_1", "switch", mi="4.1.85"),
        BoolConv("channel_2", "switch", mi="4.2.85"),
        BoolConv("channel_3", "switch", mi="4.3.85"),
        BaseConv("action", "sensor"),
        ButtonConv("button_1", mi="13.1.85"),
        ButtonConv("button_2", mi="13.2.85"),
        ButtonConv("button_3", mi="13.3.85"),
        ButtonConv("button_both_12", mi="13.5.85"),
        ButtonConv("button_both_13", mi="13.6.85"),
        ButtonConv("button_both_23", mi="13.7.85"),
        BoolConv("wireless_1", "switch", mi="4.10.85"),  # config
        BoolConv("wireless_2", "switch", mi="4.11.85"),  # config
        BoolConv("wireless_3", "switch", mi="4.12.85"),  # config
        MapConv("power_on_state", "select", mi="8.0.2030", map={0: "off", 1: "previous"}),  # config
        BoolConv("led", "switch", mi="8.0.2032"),  # config
    ],
}, {
    # with neutral wire, thanks @Mantoui
    "lumi.switch.n3acn3": ["Aqara", "Triple Wall Switch D1 (with N)", "QBKG26LM"],
    "spec": [
        BoolConv("channel_1", "switch", mi="4.1.85"),
        BoolConv("channel_2", "switch", mi="4.2.85"),
        BoolConv("channel_3", "switch", mi="4.3.85"),
        MathConv("power", "sensor", mi="0.12.85", round=2),
        MathConv("voltage", "sensor", mi="0.11.85", multiply=0.001, round=2),
        MathConv("energy", "sensor", mi="0.13.85", multiply=0.001, round=2),
        BaseConv("action", "sensor"),
        ButtonConv("button_1", mi="13.1.85"),
        ButtonConv("button_2", mi="13.2.85"),
        ButtonConv("button_3", mi="13.3.85"),
        ButtonConv("button_both_12", mi="13.5.85"),
        ButtonConv("button_both_13", mi="13.6.85"),
        ButtonConv("button_both_23", mi="13.7.85"),
        BoolConv("wireless_1", "switch", mi="4.10.85"),  # config
        BoolConv("wireless_2", "switch", mi="4.11.85"),  # config
        BoolConv("wireless_3", "switch", mi="4.12.85"),  # config
        MapConv("power_on_state", "select", mi="8.0.2030", map={0: "off", 1: "previous"}),  # config
        BoolConv("led", "switch", mi="8.0.2032"),  # config
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
        ZLumiBrightness("brightness", mi="14.1.85"),
        ZLumiColorTemp("color_temp", mi="14.2.85"),
        ZTransitionConv("transition"),
    ],
}, {
    "lumi.light.aqcn02": ["Aqara", "Bulb CN", "ZNLDP12LM"],
    "spec": [
        BoolConv("light", "light", mi="4.1.85"),
        ZLumiBrightness("brightness", mi="14.1.85"),
        ZLumiColorTemp("color_temp", mi="14.2.85"),
        ZTransitionConv("transition"),
        MapConv("power_on_state", "select", mi="8.0.2030", map={0: "on", 1: "previous"}),  # config
    ],
}, {
    # light with brightness
    "ikea.light.led1623g12": ["IKEA", "Bulb E27 1000 lm", "LED1623G12"],
    "ikea.light.led1650r5": ["IKEA", "Bulb GU10 400 lm", "LED1650R5"],
    "ikea.light.led1649c5": ["IKEA", "Bulb E14 400 lm", "LED1649C5"],  # tested
    "spec": [
        BoolConv("light", "light", mi="4.1.85"),
        ZLumiBrightness("brightness", mi="14.1.85"),
        ZTransitionConv("transition"),
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
    "spec": [
        BaseConv("action", "sensor"),
        ButtonConv("button", mi="13.1.85"),
        BatVoltConv("battery", "sensor", mi="8.0.2008"),
        BoolConv("battery_low", "binary_sensor", mi="8.0.9001"),  # diagnostic
        BaseConv("battery_original", mi="8.0.2001"),  # diagnostic
        BaseConv("chip_temperature", "sensor", mi="8.0.2006"),  # diagnostic
    ],
}, {
    # multi button action, no retain
    "lumi.sensor_86sw2.es1": ["Aqara", "Double Wall Button", "WXKG02LM"],
    "lumi.sensor_86sw2": ["Aqara", "Double Wall Button", "WXKG02LM"],
    "lumi.remote.b286acn01": ["Aqara", "Double Wall Button CN", "WXKG02LM"],
    "lumi.remote.b286acn02": ["Aqara", "Double Wall Button D1 CN", "WXKG07LM"],
    "spec": [
        BaseConv("action", "sensor"),
        ButtonConv("button_1", mi="13.1.85"),
        ButtonConv("button_2", mi="13.2.85"),
        ButtonConv("button_both", mi="13.5.85"),
        BatVoltConv("battery", "sensor", mi="8.0.2008"),
        BoolConv("battery_low", "binary_sensor", mi="8.0.9001"),  # diagnostic
        BaseConv("battery_original", mi="8.0.2001"),  # diagnostic
        BaseConv("chip_temperature", "sensor", mi="8.0.2006"),  # diagnostic
    ],
}, {
    "lumi.remote.b286opcn01": ["Aqara", "Opple Two Button CN", "WXCJKG11LM"],
    "lumi.remote.b486opcn01": ["Aqara", "Opple Four Button CN", "WXCJKG12LM"],
    "lumi.remote.b686opcn01": ["Aqara", "Opple Six Button CN", "WXCJKG13LM"],
    "spec": [
        BaseConv("action", "sensor"),
        ButtonConv("button_1", mi="13.1.85"),
        ButtonConv("button_2", mi="13.2.85"),
        ButtonConv("button_3", mi="13.3.85"),
        ButtonConv("button_4", mi="13.4.85"),
        ButtonConv("button_5", mi="13.6.85"),
        ButtonConv("button_6", mi="13.7.85"),
        ButtonConv("button_both", mi="13.5.85"),
        BatVoltConv("battery", "sensor", mi="8.0.2008"),
        ZLumiOppleMode("mode", "select"),  # config
        BoolConv("battery_low", "binary_sensor", mi="8.0.9001"),  # diagnostic
        BaseConv("battery_original", mi="8.0.2001"),  # diagnostic
        BaseConv("chip_temperature", "sensor", mi="8.0.2006"),  # diagnostic
    ],
}, {
    # temperature and humidity sensor
    "lumi.sensor_ht": ["Xiaomi", "TH Sensor", "WSDCGQ01LM"],
    "spec": [
        MathConv("temperature", "sensor", mi="0.1.85", multiply=0.01, min=-4000, max=12500),
        MathConv("humidity", "sensor", mi="0.2.85", multiply=0.01, min=0, max=10000),
        BatVoltConv("battery", "sensor", mi="8.0.2008"),
        BoolConv("battery_low", "binary_sensor", mi="8.0.9001"),  # diagnostic
        BaseConv("battery_original", mi="8.0.2001"),  # diagnostic
        BaseConv("chip_temperature", "sensor", mi="8.0.2006"),  # diagnostic
    ],
}, {
    # temperature, humidity and pressure sensor
    "lumi.weather": ["Aqara", "TH Sensor", "WSDCGQ11LM"],
    "spec": [
        MathConv("temperature", "sensor", mi="0.1.85", multiply=0.01, min=-4000, max=12500),
        MathConv("humidity", "sensor", mi="0.2.85", multiply=0.01, min=0, max=10000),
        MathConv("pressure", "sensor", mi="0.3.85", multiply=0.01),
        BatVoltConv("battery", "sensor", mi="8.0.2008"),
        BaseConv("battery_original", mi="8.0.2001"),  # diagnostic
        BaseConv("battery_voltage", "sensor"),  # diagnostic
    ],
}, {
    # door window sensor
    "lumi.sensor_magnet": ["Xiaomi", "Door/Window Sensor", "MCCGQ01LM"],
    "lumi.sensor_magnet.aq2": ["Aqara", "Door/Window Sensor", "MCCGQ11LM"],
    "spec": [
        # hass: On means open, Off means closed
        BoolConv("contact", "binary_sensor", mi="3.1.85"),
        BatVoltConv("battery", "sensor", mi="8.0.2008"),
        BoolConv("battery_low", "binary_sensor", mi="8.0.9001"),  # diagnostic
        BaseConv("battery_original", mi="8.0.2001"),  # diagnostic
        BaseConv("chip_temperature", "sensor", mi="8.0.2006"),  # diagnostic
    ],
}, {
    # motion sensor
    "lumi.sensor_motion": ["Xiaomi", "Motion Sensor", "RTCGQ01LM"],
    "spec": [
        BoolConv("motion", "binary_sensor", mi="3.1.85"),
        BatVoltConv("battery", "sensor", mi="8.0.2008"),
        BoolConv("battery_low", "binary_sensor", mi="8.0.9001"),  # diagnostic
        BaseConv("battery_original", mi="8.0.2001"),  # diagnostic
        BaseConv("chip_temperature", "sensor", mi="8.0.2006"),  # diagnostic
    ],
}, {
    # motion sensor with illuminance
    "lumi.sensor_motion.aq2": ["Aqara", "Motion Sensor", "RTCGQ11LM"],
    "spec": [
        BoolConv("motion", "binary_sensor", mi="3.1.85"),
        BaseConv("illuminance", "sensor", mi="0.3.85"),
        # Converter("illuminance", "sensor", mi="0.4.85"),
        BatVoltConv("battery", "sensor", mi="8.0.2008"),
        BaseConv("battery_original", mi="8.0.2001"),  # diagnostic
    ],
}, {
    # motion sensor E1 with illuminance
    "lumi.motion.acn001": ["Aqara", "Motion Sensor E1", "RTCGQ15LM"],
    "spec": [
        ConstConv("motion", "binary_sensor", mi="2.e.1", value=True),
        BaseConv("illuminance", "sensor", mi="2.e.1.p.1"),
        BaseConv("illuminance", mi="2.p.1"),
        BatVoltConv("battery", "sensor", mi="3.p.2"),  # voltage, mV
        MapConv("battery_low", "binary_sensor", mi="3.p.1", map={1: False, 2: True}),  # diagnostic
    ],
}, {
    # water leak sensor
    "lumi.sensor_wleak.aq1": ["Aqara", "Water Leak Sensor", "SJCGQ11LM"],
    "spec": [
        BoolConv("moisture", "binary_sensor", mi="3.1.85"),
        BatVoltConv("battery", "sensor", mi="8.0.2008"),
        BaseConv("battery_original", mi="8.0.2001"),  # diagnostic
        ZLumiBasicAlarm("moisture", basic_attr=100),  # read "no alarm" from heartbeats
    ],
}, {
    # vibration sensor
    "lumi.vibration.aq1": ["Aqara", "Vibration Sensor", "DJT11LM"],
    "support": 3,  # @AlexxIT
    "spec": [
        BaseConv("action", "sensor"),
        BatVoltConv("battery", "sensor", mi="8.0.2008"),
        BoolConv("battery_low", "binary_sensor", mi="8.0.9001"),  # diagnostic
        BaseConv("battery_original", mi="8.0.2001"),  # diagnostic
        BaseConv("bed_activity", mi="0.1.85"),
        TiltAngleConv("tilt_angle", mi="0.2.85"),
        BaseConv("vibrate_intensity", mi="0.3.85"),
        VibrationConv("vibration", mi="13.1.85"),
        BaseConv("vibration_level", mi="14.1.85"),  # read/write from 1 to 30
    ],
}, {
    # cube action, no retain
    "lumi.sensor_cube.aqgl01": ["Aqara", "Cube EU", "MFKZQ01LM"],  # tested
    "lumi.sensor_cube": ["Aqara", "Cube", "MFKZQ01LM"],
    "support": 5,  # @AlexxIT
    "spec": [
        ZLumiCubeMain("action", "sensor"),
        ZLumiCubeRotate("angle"),
        # Converter("action", mi="13.1.85"),
        # Converter("duration", mi="0.2.85", parent="action"),
        # MathConv("angle", mi="0.3.85", parent="action", multiply=0.001),
        BatVoltConv("battery", "sensor", mi="8.0.2008"),
        BaseConv("battery_original", mi="8.0.2001"),  # diagnostic
    ],
}, {
    "lumi.sensor_smoke": ["Honeywell", "Smoke Sensor", "JTYJ-GD-01LM/BW"],
    "spec": [
        BaseConv("smoke_density", "sensor", mi="0.1.85"),
        BoolConv("smoke", "binary_sensor", mi="13.1.85"),
        BatVoltConv("battery", "sensor", mi="8.0.2008"),
        BaseConv("battery_original", mi="8.0.2001"),  # diagnostic
        ZLumiSensConv("sensitivity", "select"),  # config
        ZLumiBasicAlarm("smoke", basic_attr=150),  # read "no alarm" from heartbeats
    ],
}, {
    "lumi.sensor_natgas": ["Honeywell", "Gas Sensor", "JTQJ-BF-01LM/BW"],
    "support": 4,  # @AlexxIT
    "spec": [
        BaseConv("gas_density", "sensor", mi="0.1.85"),
        BoolConv("gas", "binary_sensor", mi="13.1.85"),
        ZLumiSensConv("sensitivity", "select"),  # config
        ZLumiBasicAlarm("gas", basic_attr=150),  # read "no alarm" from heartbeats
    ],
}, {
    "lumi.curtain": ["Aqara", "Curtain", "ZNCLDJ11LM"],
    "lumi.curtain.aq2": ["Aqara", "Roller Shade", "ZNGZDJ11LM"],
    "spec": [
        MapConv("motor", "cover", mi="14.2.85", map={0: "close", 1: "open", 2: "stop"}),
        BaseConv("position", mi="1.1.85"),
        MapConv("run_state", mi="14.4.85", map={0: "closing", 1: "opening", 2: "stop"}),
    ],
}, {
    "lumi.curtain.hagl04": ["Aqara", "Curtain B1 EU", "ZNCLDJ12LM"],
    "spec": [
        MapConv("motor", "cover", mi="14.2.85", map={0: "close", 1: "open", 2: "stop"}),
        BaseConv("position", mi="1.1.85"),
        MapConv("run_state", mi="14.4.85", map={0: "closing", 1: "opening", 2: "stop"}),
        BaseConv("battery", "sensor", mi="8.0.2001"),
        MapConv("power_mode", mi="14.5.85", map={1: "adapter", 3: "battery", 4: "charging"}),
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
        BaseConv("battery", "sensor", mi="8.0.2001"),
        LockActionConv("key_id", "sensor", mi="13.1.85"),
        LockActionConv("method", mi="13.15.85", map={1: "fingerprint", 2: "password"}),
        LockActionConv("error", mi="13.4.85", map={1: "Wrong password", 2: "Wrong fingerprint"}),
        # BoolConv("lock", "binary_sensor", mi="13.20.85")
        BaseConv("action", "sensor"),
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
        BaseConv("battery", "sensor", mi="8.0.2001"),
        LockActionConv("key_id", mi="13.1.85"),
        LockActionConv("lock_control", mi="13.25.85", map={0: "in_unlocked", 1: "out_unlocked", 2: "in_locked", 3: "out_locked"}),
        LockActionConv("door_state", mi="13.26.85", map={0: "open", 1: "close", 2: "ajar"}),
        LockActionConv("lock_state", mi="13.28.85", map={0: "door_cannot_locked", 1: "door_opened", 2: "door_without_lift", 3: "door_locked", 4: "reverse_locked"}),
        LockActionConv("alarm", mi="13.5.85", map={0: "off", 1: "key_open", 4: "unlocked", 8: "hijack", 16: "pry", 32: "normally_open", 256: "less_storage", 500: "low_bat", 512: "doorbell"}),
        LockActionConv("card_wrong", mi="13.2.85"),
        LockActionConv("psw_wrong", mi="13.3.85"),
        LockActionConv("fing_wrong", mi="13.4.85"),
        LockActionConv("verified_wrong", mi="13.6.85"),
        BaseConv("action", "sensor"),
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
        ClimateConv("climate", "climate", mi="14.2.85"),
        BoolConv("power", mi="3.1.85"),
        BaseConv("current_temp", mi="3.2.85"),
        MapConv("hvac_mode", mi="14.8.85", map={0: "heat", 1: "cool", 15: "off"}),
        MapConv("fan_mode", mi="14.10.85", map={0: "low", 1: "medium", 2: "high", 3: "auto"}),
        ClimateTempConv("target_temp", mi="14.9.85"),
    ],
}, {
    "lumi.airrtc.agl001": ["Aqara", "Thermostat E1", "SRTS-A01"],
    "spec": [
        # The following code is very different to the spec defined in home.miot-spec.com thus leave unmodified
        BoolConv("climate", "climate", mi="4.21.85"),
        # 0: Manual module 1: Smart schedule mode # 2: Antifreeze mode 3: Installation mode
        MapConv("mode", mi="14.51.85", map={0: "heat", 2: "auto"}),
        MathConv("current_temp", mi="0.1.85", multiply=0.01),
        MathConv("target_temp", mi="1.8.85", multiply=0.01),
        MathConv("antifreeze_temp", "number", mi="1.10.85", multiply=0.01, min=5, max=15, entity={"category": "config", "enabled": False, "units": UNIT_CELSIUS}),
        BoolConv("window_detection", "switch", mi="4.24.85", entity=ENTITY_CONFIG),
        BoolConv("valve_calibration", "switch", mi="4.22.85", entity=ENTITY_CONFIG),
        BoolConv("valve_notification", "switch", mi="4.25.85", entity=ENTITY_CONFIG),
        BoolConv("child_lock", "switch", mi="4.26.85"),
        MapConv("find_device", "switch", mi="8.0.2096", map={2: True, 1: False}, entity=ENTITY_CONFIG),
        BaseConv("battery", "sensor", mi="8.0.2001"),
        BaseConv("chip_temperature", "sensor", mi="8.0.2006"),
    ],
}, {
    "lumi.airrtc.vrfegl01": ["Xiaomi", "VRF Air Conditioning EU"],
    "support": 1,
    "spec": [
        BaseConv("channels", "sensor", mi="13.1.85"),
    ],
}]

# Zigbee (miot)
DEVICES += [{
    "lumi.sen_ill.mgl01": ["Xiaomi", "Light Sensor EU", "GZCGQ01LM", "YTC4043GL"],
    "lumi.sen_ill.agl01": ["Aqara", "Light Sensor T1 CN", "GZCGQ11LM"],
    "spec": [
        BaseConv("illuminance", "sensor", mi="2.p.1"),
        BatVoltConv("battery", "sensor", mi="3.p.1"),  # voltage, mV
        # new gw firmwares has a bug - don't bind power cluster
        # ZBatteryVoltConv("battery", bind=True, report=True),
    ],
}, {
    "lumi.magnet.acn001": ["Aqara", "Door/Window Sensor E1 CN", "MCCGQ14LM"],
    "spec": [
        MapConv("contact", "binary_sensor", mi="2.p.1", map={0: True, 1: False}),
        BatVoltConv("battery", "sensor", mi="3.p.2"),  # voltage, mV
        MapConv("battery_low", "binary_sensor", mi="3.p.1", map={1: False, 2: True}),  # diagnostic
    ],
}, {
    "lumi.flood.acn001": ["Aqara", "Water Leak Sensor E1", "SJCGQ13LM"],
    "spec": [
        BaseConv("moisture", "binary_sensor", mi="2.p.1"),  # bool
        BatVoltConv("battery", "sensor", mi="3.p.2"),  # voltage, mV
        MapConv("battery_low", "binary_sensor", mi="3.p.1", map={1: False, 2: True}),  # diagnostic
    ]
}, {
    "lumi.sensor_ht.agl02": ["Aqara", "TH Sensor T1", "WSDCGQ12LM"],
    "spec": [
        BaseConv("temperature", "sensor", mi="2.p.1"),  # celsius
        BaseConv("humidity", "sensor", mi="2.p.2"),  # percentage
        BaseConv("pressure", "sensor", mi="2.p.3"),  # kilopascal
        BatVoltConv("battery", "sensor", mi="3.p.1"),  # voltage, mV
        MapConv("battery_low", "binary_sensor", mi="4.p.1", map={1: False, 2: True}),  # diagnostic
    ],
}, {
    # https://home.miot-spec.com/spec?type=urn:miot-spec-v2:device:motion-sensor:0000A014:lumi-agl04:1:0000C813
    # for spec names Fibaro has good example: https://manuals.fibaro.com/motion-sensor/
    "lumi.motion.agl04": ["Aqara", "Precision Motion Sensor EU", "RTCGQ13LM"],
    "spec": [
        ConstConv("motion", "binary_sensor", mi="4.e.1", value=True),
        BatVoltConv("battery", "sensor", mi="3.p.1"),  # voltage, mV
        MapConv("sensitivity", "select", mi="8.p.1", map={1: "low", 2: "medium", 3: "high"}),  # config
        MathConv("blind_time", "number", mi="10.p.1", min=2, max=180),  # config
        MapConv("battery_low", "binary_sensor", mi="5.p.1", map={1: False, 2: True}),  # diagnostic
        BaseConv("idle_time", "sensor", mi="6.p.1"),  # diagnostic
    ],
}, {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-monitor:0000A008:lumi-acn01:1
    "lumi.airmonitor.acn01": ["Aqara", "Air Quality Monitor CN", "VOCKQJK11LM"],
    "spec": [
        BaseConv("temperature", "sensor", mi="3.p.1"),  # celsius
        BaseConv("humidity", "sensor", mi="3.p.2"),  # percentage
        BaseConv("tvoc", "sensor", mi="3.p.3"),  # ppb
        BatVoltConv("battery", "sensor", mi="4.p.2"),  # voltage, mV
        MapConv("battery_low", "binary_sensor", mi="4.p.1", map={1: False, 2: True}),  # diagnostic
        MapConv("display_unit", "select", mi="6.p.1", map={0: "℃, mg/m³", 1: "℃, ppb", 16: "℉, mg/m³", 17: "℉, ppb"}),  # config
    ],
}, {
    "lumi.curtain.acn002": ["Aqara", "Roller Shade E1 CN", "ZNJLBL01LM"],
    "spec": [
        MapConv("motor", "cover", mi="2.p.2", map={0: "stop", 1: "close", 2: "open"}),
        BaseConv("target_position", mi="2.p.4"),
        CurtainPosConv("position", mi="2.p.5"),
        MapConv("run_state", mi="2.p.6", map={0: "closing", 1: "opening", 2: "stop"}),
        BaseConv("battery", "sensor", mi="3.p.4"),  # percent
        BaseConv("motor_reverse", "switch", mi="2.p.7"),  # config
        MapConv("motor_speed", "select", mi="5.p.5", map={0: "low", 1: "mid", 2: "high"}),  # config
        MapConv("battery_low", "binary_sensor", mi="3.p.1", map={1: False, 2: True}),  # diagnostic
        BaseConv("battery_voltage", "sensor", mi="3.p.2"),  # diagnostic
        MapConv("battery_charging", "binary_sensor", mi="3.p.3", map={0: False, 1: True, 2: False}),  # diagnostic
        # BoolConv("fault", "sensor", mi="2.p.1", entity=ENTITY_DISABLED),
        # Converter("mode", "sensor", mi="2.p.3"),  # only auto
    ],
}, {
    19363: ["Xijia", "Curtain Motor", "xijia1.curtain.x3"],
    "spec": [
        MapConv("motor", "cover", mi="2.p.1", map={0: "close", 1: "stop", 2: "open"}),
        BaseConv("target_position", mi="2.p.4"),
        CurtainPosConv("position", mi="2.p.3"),
        MapConv("run_state", mi="2.p.2", map={0: "closing", 1: "stop", 2: "opening"}),
        BaseConv("battery", "sensor", mi="3.p.1"),  # percent
        BoolConv("motor_reverse", "switch", mi="2.p.5"),  # uint8, config
        MapConv("battery_charging", "binary_sensor", mi="3.p.2", map={1: True, 2: False}),  # diagnostic
    ],
}, {
    "lumi.remote.acn003": ["Aqara", "Single Wall Button E1 CN", "WXKG16LM"],
    # https://github.com/niceboygithub/AqaraGateway/pull/118/files
    "lumi.remote.acn007": ["Aqara", "Single Wall Button E1", "WXKG20LM"],
    "spec": [
        BaseConv("action", "sensor"),
        ConstConv("action", mi="2.e.1", value=BUTTON_SINGLE),
        ConstConv("action", mi="2.e.2", value=BUTTON_DOUBLE),
        ConstConv("action", mi="2.e.3", value=BUTTON_HOLD),
        BatVoltConv("battery", "sensor", mi="3.p.2"),
    ],
}, {
    "lumi.remote.acn004": ["Aqara", "Double Wall Button E1 CN", "WXKG17LM"],
    "spec": [
        BaseConv("action", "sensor"),
        ConstConv("action", mi="2.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="2.e.2", value=BUTTON_1_DOUBLE),
        ConstConv("action", mi="2.e.3", value=BUTTON_1_HOLD),
        ConstConv("action", mi="7.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="7.e.2", value=BUTTON_2_DOUBLE),
        ConstConv("action", mi="7.e.3", value=BUTTON_2_HOLD),
        ConstConv("action", mi="8.e.1", value=BUTTON_BOTH_SINGLE),
        BatVoltConv("battery", "sensor", mi="3.p.2"),
        MapConv("mode", "select", mi="5.p.1", map={1: "speed", 2: "multi"}),  # config
    ],
}]

# relays and switches

DEVICES += [{
    # https://www.aqara.com/en/single_switch_T1_no-neutral.html
    "lumi.switch.l0agl1": ["Aqara", "Relay T1 EU (no N)", "SSM-U02"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),
        BaseConv("chip_temperature", "sensor", mi="2.p.6"),  # diagnostic
        MapConv("power_on_state", "select", mi="4.p.1", map={0: "off", 1: "previous"}),  # config
        MapConv("mode", "select", mi="6.p.2", map={1: "toggle", 2: "momentary"}),  # config
    ],
}, {
    # https://www.aqara.com/en/single_switch_T1_with-neutral.html
    "lumi.switch.n0agl1": ["Aqara", "Relay T1 EU (with N)", "SSM-U01"],
    "lumi.switch.n0acn2": ["Aqara", "Relay T1 CN (with N)", "DLKZMK11LM"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),
        MathConv("energy", "sensor", mi="3.p.1", multiply=0.001, round=2),
        MathConv("power", "sensor", mi="3.p.2", round=2),
        BoolConv("led", "switch", mi="4.p.1"),  # uint8, config
        MapConv("power_on_state", "select", mi="5.p.1", map={0: "off", 1: "previous"}),  # config
        MapConv("mode", "select", mi="7.p.2", map={1: "toggle", 2: "momentary"}),  # config
    ],
}, {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:outlet:0000A002:lumi-maeu01:1
    "lumi.plug.maeu01": ["Aqara", "Plug EU", "SP-EUC01"],  # no spec
    "spec": [
        BaseConv("plug", "switch", mi="2.p.1"),
        MathConv("energy", "sensor", mi="3.p.1", multiply=0.001, round=2),
        MathConv("power", "sensor", mi="3.p.2", round=2),
        BoolConv("led", "switch", mi="4.p.1"),  # uint8, config
        MapConv("power_on_state", "select", mi="5.p.1", map={0: "off", 1: "previous"}),  # config
    ],
}, {
    "lumi.switch.b1lc04": ["Aqara", "Single Wall Switch E1 (no N)", "QBKG38LM"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),
        ConstConv("action", mi="6.e.1", value=BUTTON_SINGLE),
        ConstConv("action", mi="6.e.2", value=BUTTON_DOUBLE),
        BaseConv("action", "sensor"),
        BoolConv("led", "switch", mi="3.p.1"),  # uint8, config
        MapConv("power_on_state", "select", mi="4.p.1", map={0: "off", 1: "previous"}),  # config
        BoolConv("wireless", "switch", mi="6.p.1"),  # config
        MapConv("mode", "select", mi="10.p.1", map={1: "250 ms", 2: "500 ms", 3: "750 ms", 4: "1 sec"}),  # config
    ],
}, {
    "lumi.switch.b2lc04": ["Aqara", "Double Wall Switch E1 (no N)", "QBKG39LM"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        ConstConv("action", mi="7.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="7.e.2", value=BUTTON_1_DOUBLE),
        ConstConv("action", mi="8.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="8.e.2", value=BUTTON_2_DOUBLE),
        ConstConv("action", mi="9.e.1", value=BUTTON_BOTH_SINGLE),
        BaseConv("action", "sensor"),
        BoolConv("wireless_1", "switch", mi="7.p.1"),  # config
        BoolConv("wireless_2", "switch", mi="8.p.1"),  # config
        BoolConv("led", "switch", mi="4.p.1"),  # uint8, config
        MapConv("power_on_state", "select", mi="5.p.1", map={0: "off", 1: "previous"}),  # config
        MapConv("mode", "select", mi="15.p.1", map={1: "250 ms", 2: "500 ms", 3: "750 ms", 4: "1 sec"})  # config
    ],
}, {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:switch:0000A003:lumi-b1nc01:1
    "lumi.switch.b1nc01": ["Aqara", "Single Wall Switch E1 (with N)", "QBKG40LM"],
    # "support": 5,
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),
        BaseConv("action", "sensor"),
        ConstConv("action", mi="7.e.1", value=BUTTON_SINGLE),
        ConstConv("action", mi="7.e.2", value=BUTTON_DOUBLE),
        BoolConv("led", "switch", mi="4.p.1"),  # uint8, config
        BoolConv("led_reverse", "switch", mi="4.p.2"),  # uint8, config
        MapConv("power_on_state", "select", mi="5.p.1", map={0: "off", 1: "previous"}),  # config
        BoolConv("wireless", "switch", mi="7.p.1"),  # config
    ],
}, {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:switch:0000A003:lumi-b2nc01:1
    "lumi.switch.b2nc01": ["Aqara", "Double Wall Switch E1 (with N)", "QBKG41LM"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        ConstConv("action", mi="8.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="8.e.2", value=BUTTON_1_DOUBLE),
        ConstConv("action", mi="9.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="9.e.2", value=BUTTON_2_DOUBLE),
        ConstConv("action", mi="10.e.1", value=BUTTON_BOTH_SINGLE),
        BaseConv("action", "sensor"),
        BoolConv("led", "switch", mi="5.p.1"),  # uint8, config
        BoolConv("led_reverse", "switch", mi="5.p.2"),  # uint8, config
        MapConv("power_on_state", "select", mi="6.p.1", map={0: "off", 1: "previous"}),  # config
        BoolConv("wireless_1", "switch", mi="8.p.1"),  # config
        BoolConv("wireless_2", "switch", mi="9.p.1"),  # config
    ],
}, {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:switch:0000A003:lumi-acn040:1
    "lumi.switch.acn040": ["Aqara", "Triple Wall Switch E1 (with N)", "ZNQBKG31LM"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),

        # Button press actions
        BaseConv("action", "sensor"),
        ConstConv("action", mi="9.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="9.e.2", value=BUTTON_1_DOUBLE),
        ConstConv("action", mi="10.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="10.e.2", value=BUTTON_2_DOUBLE),
        ConstConv("action", mi="11.e.1", value=BUTTON_3_SINGLE),
        ConstConv("action", mi="11.e.2", value=BUTTON_3_DOUBLE),
        ConstConv("action", mi="12.e.1", value=BUTTON_BOTH_12),
        ConstConv("action", mi="13.e.1", value=BUTTON_BOTH_13),
        ConstConv("action", mi="14.e.1", value=BUTTON_BOTH_23),

        # Wireless switch
        # Native false = Wireless, Native true = Relay
        MapConv("wireless_1", "switch", mi="9.p.1", map={0: True, 1: False}),  # config
        MapConv("wireless_2", "switch", mi="10.p.1", map={0: True, 1: False}),  # config
        MapConv("wireless_3", "switch", mi="11.p.1", map={0: True, 1: False}),  # config

        # Others
        MapConv("power_on_state", "select", mi="7.p.1", map={0: "off", 1: "previous"}),  # config
        MapConv("temperature_alarm", "sensor", mi="8.p.1", map={0: "normal", 1: "protected", 2: "abnormal"}),

        # LED control
        BoolConv("led_inverted", "switch", mi="6.p.2"),  # config
        BoolConv("led_dnd", "switch", mi="6.p.1", entity=ENTITY_CONFIG),
        AqaraDNDTimeConv("led_dnd_time", "text", mi="6.p.3", entity=ENTITY_CONFIG)
    ]
}, {
    # required switch firmware 0.0.0_0030
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:switch:0000A003:lumi-b2naus01:1
    "lumi.switch.b2naus01": ["Aqara", "Double Wall Switch US (with N)", "WS-USC04"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        MathConv("energy", "sensor", mi="4.p.1", multiply=0.001, round=2),
        MathConv("power", "sensor", mi="4.p.2", round=2),
        BaseConv("action", "sensor"),
        ConstConv("action", mi="8.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="8.e.2", value=BUTTON_1_DOUBLE),
        ConstConv("action", mi="9.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="9.e.2", value=BUTTON_2_DOUBLE),
        ConstConv("action", mi="10.e.1", value=BUTTON_BOTH_SINGLE),
        BoolConv("led", "switch", mi="5.p.1"),  # uint8, config
        MapConv("power_on_state", "select", mi="6.p.1", map={0: "off", 1: "previous"}),  # config
        BoolConv("wireless_1", "switch", mi="8.p.1"),  # uint8, config
        BoolConv("wireless_2", "switch", mi="9.p.1"),  # uint8, config
    ],
}, {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:switch:0000A003:lumi-l1acn1:1
    "lumi.switch.l1acn1": ["Aqara", "Single Wall Switch H1 CN (no N)", "QBKG27LM"],
    "lumi.switch.l1aeu1": ["Aqara", "Single Wall Switch H1 EU (no N)", "WS-EUK01"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),
        BaseConv("action", "sensor"),
        ConstConv("action", mi="6.e.1", value=BUTTON_SINGLE),
        ConstConv("action", mi="6.e.2", value=BUTTON_DOUBLE),
        BoolConv("led", "switch", mi="3.p.1"),  # uint8, config
        MapConv("power_on_state", "select", mi="4.p.1", map={0: "off", 1: "previous"}),  # config
        BoolConv("wireless", "switch", mi="6.p.1"),  # uint8, config
    ],
}, {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:switch:0000A003:lumi-l2acn1:1
    "lumi.switch.l2acn1": ["Aqara", "Double Wall Switch H1 CN (no N)", "QBKG28LM"],
    "lumi.switch.l2aeu1": ["Aqara", "Double Wall Switch H1 EU (no N)", "WS-EUK02"],
    # "support": 5,
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        ConstConv("action", mi="7.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="7.e.2", value=BUTTON_1_DOUBLE),
        ConstConv("action", mi="8.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="8.e.2", value=BUTTON_2_DOUBLE),
        ConstConv("action", mi="9.e.1", value=BUTTON_BOTH_SINGLE),
        BaseConv("action", "sensor"),
        BoolConv("led", "switch", mi="4.p.1"),  # uint8, config
        MapConv("power_on_state", "select", mi="5.p.1", map={0: "off", 1: "previous"}),  # config
        BoolConv("wireless_1", "switch", mi="7.p.1"),  # uint8, config
        BoolConv("wireless_2", "switch", mi="8.p.1"),  # uint8, config
    ],
}, {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:switch:0000A003:lumi-n1acn1:1
    "lumi.switch.n1acn1": ["Aqara", "Single Wall Switch H1 CN (with N)", "QBKG30LM"],
    "lumi.switch.n1aeu1": ["Aqara", "Single Wall Switch H1 EU (with N)", "WS-EUK03"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),
        MathConv("energy", "sensor", mi="3.p.1", multiply=0.001, round=2),
        MathConv("power", "sensor", mi="3.p.2", round=2),
        BaseConv("action", "sensor"),
        ConstConv("action", mi="7.e.1", value=BUTTON_SINGLE),
        ConstConv("action", mi="7.e.2", value=BUTTON_DOUBLE),
        BoolConv("led", "switch", mi="4.p.1"),  # uint8, config
        BoolConv("led_reverse", "switch", mi="4.p.2"),  # uint8, config
        MapConv("power_on_state", "select", mi="5.p.1", map={0: "off", 1: "previous"}),  # config
        BoolConv("wireless", "switch", mi="7.p.1"),  # uint8, config
    ],
}, {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:switch:0000A003:lumi-n2acn1:1
    "lumi.switch.n2acn1": ["Aqara", "Double Wall Switch H1 CN (with N)", "QBKG31LM"],
    "lumi.switch.n2aeu1": ["Aqara", "Double Wall Switch H1 EU (with N)", "WS-EUK04"],
    # "support": 5,
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        MathConv("energy", "sensor", mi="4.p.1", multiply=0.001, round=2),
        MathConv("power", "sensor", mi="4.p.2", round=2),
        BaseConv("action", "sensor"),
        ConstConv("action", mi="8.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="8.e.2", value=BUTTON_1_DOUBLE),
        ConstConv("action", mi="9.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="9.e.2", value=BUTTON_2_DOUBLE),
        ConstConv("action", mi="10.e.1", value=BUTTON_BOTH_SINGLE),
        BoolConv("led", "switch", mi="5.p.1"),  # uint8, config
        BoolConv("led_reverse", "switch", mi="5.p.2"),  # uint8, config
        MapConv("power_on_state", "select", mi="6.p.1", map={0: "off", 1: "previous"}),  # config
        BoolConv("wireless_1", "switch", mi="8.p.1"),  # uint8, config
        BoolConv("wireless_2", "switch", mi="9.p.1"),  # uint8, config
    ],
}, {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:switch:0000A003:lumi-l3acn1:1
    "lumi.switch.l3acn1": ["Aqara", "Triple Wall Switch H1 CN (no N)", "QBKG29LM"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
        ConstConv("action", mi="8.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="8.e.2", value=BUTTON_1_DOUBLE),
        ConstConv("action", mi="9.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="9.e.2", value=BUTTON_2_DOUBLE),
        ConstConv("action", mi="10.e.1", value=BUTTON_3_SINGLE),
        ConstConv("action", mi="10.e.2", value=BUTTON_3_DOUBLE),
        ConstConv("action", mi="11.e.1", value=BUTTON_BOTH_12),
        ConstConv("action", mi="12.e.1", value=BUTTON_BOTH_13),
        ConstConv("action", mi="13.e.1", value=BUTTON_BOTH_23),
        BaseConv("action", "sensor"),
        BoolConv("led", "switch", mi="5.p.1"),  # uint8, config
        MapConv("power_on_state", "select", mi="6.p.1", map={0: "off", 1: "previous"}),  # config
        BoolConv("wireless_1", "switch", mi="8.p.1"),  # uint8, config
        BoolConv("wireless_2", "switch", mi="9.p.1"),  # uint8, config
        BoolConv("wireless_3", "switch", mi="10.p.1"),  # uint8, config
    ]
}, {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:switch:0000A003:lumi-n3acn1:1
    "lumi.switch.n3acn1": ["Aqara", "Triple Wall Switch H1 CN (with N)", "QBKG32LM"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
        MathConv("energy", "sensor", mi="5.p.1", multiply=0.001, round=2),
        MathConv("power", "sensor", mi="5.p.2", round=2),
        ConstConv("action", mi="9.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="9.e.2", value=BUTTON_1_DOUBLE),
        ConstConv("action", mi="10.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="10.e.2", value=BUTTON_2_DOUBLE),
        ConstConv("action", mi="11.e.1", value=BUTTON_3_SINGLE),
        ConstConv("action", mi="11.e.2", value=BUTTON_3_DOUBLE),
        ConstConv("action", mi="12.e.1", value=BUTTON_BOTH_12),
        ConstConv("action", mi="13.e.1", value=BUTTON_BOTH_13),
        ConstConv("action", mi="14.e.1", value=BUTTON_BOTH_23),
        BaseConv("action", "sensor"),
        BoolConv("led", "switch", mi="6.p.1"),  # uint8, config
        BoolConv("led_reverse", "switch", mi="6.p.2"),  # uint8, config
        MapConv("power_on_state", "select", mi="7.p.1", map={0: "off", 1: "previous"}),  # config
        MapConv("wireless_1", "switch", mi="9.p.1", map={0: True, 1: False}),  # config
        MapConv("wireless_2", "switch", mi="10.p.1", map={0: True, 1: False}),  # config
        MapConv("wireless_3", "switch", mi="11.p.1", map={0: True, 1: False}),  # config
    ]
}, {
    "lumi.remote.b28ac1": ["Aqara", "Double Wall Button H1", "WRS-R02"],
    "spec": [
        BaseConv("action", "sensor"),
        ConstConv("action", mi="3.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="3.e.2", value=BUTTON_1_DOUBLE),
        ConstConv("action", mi="3.e.3", value=BUTTON_1_HOLD),
        ConstConv("action", mi="4.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="4.e.2", value=BUTTON_2_DOUBLE),
        ConstConv("action", mi="4.e.3", value=BUTTON_2_HOLD),
        BatVoltConv("battery", "sensor", mi="6.p.2"),  # voltage
        MapConv("battery_low", "binary_sensor", mi="6.p.1", map={1: False, 2: True}),  # diagnostic
        MapConv("mode", "select", mi="8.p.1", map={1: "single_click", 2: "multi_click"}),  # config
    ]
}, {
    "lumi.sensor_smoke.acn03": ["Aqara", "Smoke Sensor", "JY-GZ-01AQ"],
    "spec": [
        BoolConv("smoke", "binary_sensor", mi="2.p.1"),
        BaseConv("smoke_density", "sensor", mi="2.p.3"),
        BoolConv("fault", "binary_sensor", mi="2.p.2"),  # diagnostic
        BoolConv("led", "switch", mi="5.p.1"),  # uint8, config
        MapConv("battery_low", "binary_sensor", mi="3.p.1", map={1: False, 2: True}),  # diagnostic
        BaseConv("battery_voltage", "sensor", mi="3.p.2"),  # diagnostic
    ]
}, {
    # https://github.com/AlexxIT/XiaomiGateway3/issues/865
    "lumi.sensor_gas.acn02": ["Aqara", "Gas Sensor", "JT-BZ-01AQ/A"],
    "spec": [
        MapConv("status", "sensor", mi="2.p.1", map={0: "Normal Monitoring", 1: "Alarm", 2: "Fault", 3: "Warm Up", 4: "End Of Life"}),
        BoolConv("fault", "binary_sensor", mi="2.p.2"),  # diagnostic
        BaseConv("gas_density", "sensor", mi="2.p.3"),  # percentage
        MapConv("sensitivity", "select", mi="5.p.1", map={1: "LEL15", 2: "LEL10"}),  # config
        BaseConv("remain_days", "sensor", mi="9.p.1"),
    ],
}, {
    "lumi.light.acn014": ["Aqara", "Bulb T1", "ZNLDP14LM"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        # BrightnessConv("brightness", mi="2.p.2"),
        # ColorTempKelvin("color_temp", mi="2.p.3"),
        ZLumiBrightness("brightness", mi="2.p.2"),
        ZLumiColorTemp("color_temp", mi="2.p.3"),
        ZTransitionConv("transition"),
    ],
}, {
    "lumi.remote.b1acn02": ["Aqara", "Button", "WXKG13LM"],
    "spec": [
        BaseConv("action", "sensor"),
        ConstConv("action", mi="3.e.1", value=BUTTON_SINGLE),
        ConstConv("action", mi="3.e.2", value=BUTTON_DOUBLE),
        ConstConv("action", mi="3.e.3", value=BUTTON_HOLD),
        BatVoltConv("battery", "sensor", mi="2.p.1"),  # voltage
        MapConv("battery_low", "binary_sensor", mi="4.p.1", map={1: False, 2: True}),  # diagnostic
    ]
}, {
    "lumi.light.acn003": ["Aqara", "L1-350 Ceiling Light", "ZNXDD01LM"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2"),
        ColorTempKelvin("color_temp", mi="2.p.3"),
        MapConv("mode", "select", mi="2.p.4", map={0: "day", 1: "reading", 2: "warm", 3: "tv", 4: "night"}),
        MapConv("power_on_state", "select", mi="3.p.2", map={False: "off", True: "previous"}),  # bool
    ],
}]

########################################################################################
# 3rd party zigbee
########################################################################################

DEVICES += [{
    # this model didn't supported in MiHome
    "lumi.light.cwac02": ["Aqara", "Bulb T1 CN", "ZNLDP13LM", "LEDLBT1-L01"],
    "spec": [
        ZOnOffConv("light", "light"),
        ZBrightnessConv("brightness"),
        ZColorTempConv("color_temp"),
        ZTransitionConv("transition"),
    ],
}, {
    "TS0121": ["BlitzWolf", "Plug", "BW-SHP13"],
    "support": 5,  # @AlexxIT
    "spec": [
        ZOnOffConv("plug", "switch"),
        ZVoltageConv("voltage", "sensor", entity={"poll": True}),  # once per 60 seconds
        ZCurrentConv("current", "sensor", multiply=0.001),
        ZPowerConv("power", "sensor"),
        ZEnergyConv("energy", "sensor", multiply=0.01),  # once per 5 minutes
        ZTuyaPowerOnConv("power_on_state", "select"),
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
        ZTuyaPowerOnConv("power_on_state", "select"),
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
        ZTuyaPowerOnConv("power_on_state", "select"),
        ZTuyaLEDModeConv("led", "select"),
        ZTuyaChildModeConv("child_lock", "switch"),
        ZTuyaPlugModeConv("mode", "select")
    ],
}, {
    # tuya relay with neutral, 1 gang
    "TS0001": ["Tuya", "Relay", "TS0001"],
    "support": 4,
    "spec": [
        ZOnOffConv("switch", "switch", bind=True),
        ZTuyaPowerOnConv("power_on_state", "select"),  # config
    ],
}, {
    # tuya relay with neutral, 2 gang
    "TS0002": ["Tuya", "Relay", "TS0002"],
    "support": 3,  # @zvldz
    "spec": [
        ZOnOffConv("channel_1", "switch", ep=1, bind=True),
        ZOnOffConv("channel_2", "switch", ep=2, bind=True),
        ZTuyaPowerOnConv("power_on_state", "select"),  # config
        ZTuyaPlugModeConv("mode", "select"),  # config
    ],
}, {
    # tuya relay with neutral, 3 gang
    "TS0003": ["Tuya", "Relay", "TS0003"],
    "support": 3,
    "spec": [
        ZOnOffConv("channel_1", "switch", ep=1, bind=True),
        ZOnOffConv("channel_2", "switch", ep=2, bind=True),
        ZOnOffConv("channel_3", "switch", ep=3, bind=True),
        ZTuyaPowerOnConv("power_on_state", "select"),
        ZTuyaPlugModeConv("mode", "select"),
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
        ZTuyaPowerOnConv("power_on_state", "select"),
        ZTuyaPlugModeConv("mode", "select"),
    ],
}, {
    "TS004F": ["Tuya", "Wireless Four Button", "RSH-Zigbee-SC04"],
    "spec": [
        ZTuyaButtonConfig("action", "sensor"),
        ZTuyaButtonConv("button_1", ep=1, bind=True),
        ZTuyaButtonConv("button_2", ep=2, bind=True),
        ZTuyaButtonConv("button_3", ep=3, bind=True),
        ZTuyaButtonConv("button_4", ep=4, bind=True),
        ZBatteryPercConv("battery", "sensor", bind=True),
        ZTuyaButtonModeConv("mode", "select"),  # config
    ],
}, {
    # very simple relays with binding
    "TS0011": ["Tuya", "Single Switch (no N)", "TS0011"],
    "support": 5,
    "spec": [
        ZOnOffConv("switch", "switch", bind=True),
        ZTuyaPowerOnConv("power_on_state", "select"),
        ZTuyaPlugModeConv("mode", "select"),
    ],
}, {
    # very simple 2 gang relays with binding
    "TS0012": ["Tuya", "Double Switch", "TS0012"],
    "support": 5,
    "spec": [
        ZOnOffConv("channel_1", "switch", ep=1, bind=True),
        ZOnOffConv("channel_2", "switch", ep=2, bind=True),
        ZTuyaPowerOnConv("power_on_state", "select"),
        ZTuyaPlugModeConv("mode", "select"),
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
        ZBatteryPercConv("battery", "sensor", report="1h 12h 0"),
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
    "spec": [ZOnOffConv("switch", "switch")]
}, {
    "ZBMINIL2": ["Sonoff", "Mini L2 (no N)", "ZBMINIL2"],
    "spec": [
        ZOnOffConv("switch", "switch"),
        ZPowerOnConv("power_on_state", "select")
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
        ZBatteryPercConv("battery", "sensor"),
    ],
}, {
    "MS01": ["Sonoff", "Motion Sensor", "SNZB-03"],
    "support": 5,  # @AlexxIT
    "spec": [
        ZIASZoneConv("occupancy", "binary_sensor"),
        ZBatteryPercConv("battery", "sensor", multiply=0.5),
        ZBatteryVoltConv("battery_voltage", "sensor"),
    ],
}, {
    "TH01": ["Sonoff", "TH Sensor", "SNZB-02"],
    "spec": [
        # temperature, humidity and battery binds by default
        # report config for battery_voltage also by default
        ZTemperatureConv("temperature", "sensor", report="10s 1h 100"),
        ZHumidityConv("humidity", "sensor", report="10s 1h 100"),
        ZBatteryPercConv("battery", "sensor", report="1h 12h 0"),
    ],
}, {
    # wrong zigbee model, some devices have model TH01 (ewelink bug)
    "DS01": ["Sonoff", "Door/Window Sensor", "SNZB-04"],
    "support": 5,
    "spec": [
        ZIASZoneConv("contact", "binary_sensor"),
        ZBatteryPercConv("battery", "sensor"),
    ],
}, {
    "SML001": ["Philips", "Hue motion sensor", "9290012607"],
    "support": 4,  # @AlexxIT TODO: sensitivity, led
    "spec": [
        ZOccupancyConv("occupancy", "binary_sensor", ep=2, bind=True, report="0s 1h 0"),
        ZIlluminanceConv("illuminance", "sensor", ep=2, bind=True, report="10s 1h 5"),
        ZTemperatureConv("temperature", "sensor", ep=2, bind=True, report="10s 1h 100"),
        ZBatteryPercConv("battery", "sensor", ep=2, bind=True, report="1h 12h 0"),
        ZOccupancyTimeoutConv("occupancy_timeout", "number", ep=2, entity=ENTITY_CONFIG),
    ],
}, {
    "LWB010": ["Philips", "Hue white 806 lm", "9290011370B"],
    "support": 2,
    "spec": [
        ZOnOffConv("light", "light", ep=11, entity={"poll": True}),
        ZBrightnessConv("brightness", ep=11),
        ZTransitionConv("transition"),
    ],
}, {
    "LCT001": ["Philips", "Hue Color 600 lm", "9290012573A"],
    "support": 4,
    "spec": [
        ZOnOffConv("light", "light", ep=11, entity={"poll": True}),
        ZBrightnessConv("brightness", ep=11),
        ZColorTempConv("color_temp", ep=11),
        ZColorHSConv("hs_color", ep=11),
        ZColorModeConv("color_mode", ep=11),
        ZTransitionConv("transition"),
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
    "FNB56-ZSC01LX1.2": [None, "Dimmer", "LXZ8-02A"],
    "TRADFRI bulb E27 W opal 1000lm": ["IKEA", "Bulb E27 1000 lm", "LED1623G12"],
    "TRADFRI bulb E27 WW 806lm": ["IKEA", "Bulb E27 806 lm", "LED1836G9"],
    "support": 3,  # @AlexxIT
    "spec": [
        ZOnOffConv("light", "light"),
        ZBrightnessConv("brightness"),
        ZTransitionConv("transition"),
    ],
}, {
    "TRADFRI bulb E14 WS opal 600lm": ["IKEA", "Bulb E14 WS opal 600lm", "LED1738G7"],
    "TRADFRI bulb E12 WS 450lm": ["IKEA", "Bulb E12 WS 450lm", "LED1903C5"],
    "TRADFRI bulb E14 WS 470lm": ["IKEA", "Bulb E14 WS 470lm", "LED1903C5"],
    "TRADFRI bulb E17 WS 440lm": ["IKEA", "Bulb E17 WS 440lm", "LED1903C5"],
    "spec": [
        ZOnOffConv("light", "light"),
        ZBrightnessConv("brightness"),
        ZColorTempConv("color_temp"),
        ZTransitionConv("transition"),
    ],
}, {
    "TRADFRI remote control": ["IKEA", "TRADFRI remote control", "E1524/E1810"],
    "support": 1,
    "spec": [
        # IKEARemoteConv1("action", "sensor", bind=True),
        # IKEARemoteConv2("action"),
    ],
}, {
    "TRADFRI Signal Repeater": ["IKEA", "TRADFRI signal repeater", "E1746"],
    "spec": [],  # just repeater, no spec
}, {
    "TRADFRI open/close remote": ["IKEA", "TRADFRI open/close remote", "E1766"],
    "support": 1,
    "spec": [
        ZBatteryPercConv("battery", "sensor", bind=True),
        ZBatteryVoltConv("battery_voltage", "sensor"),
    ],
}, {
    "FYRTUR block-out roller blind": ["IKEA", "FYRTUR roller blind", "E1757"],
    "support": 5,  # @AlexxIT
    "spec": [
        ZCoverCmd("motor", "cover", bind=True),
        ZCoverPos("position", report="1s 5h 1"),
        ZBatteryPercConv("battery", "sensor", bind=True, report="1h 12h 0"),
        ZBatteryVoltConv("battery_voltage", "sensor"),
    ],
}, {
    "Leak_Sensor": ["LifeControl", "Water Leak Sensor", "MCLH-07"],
    "spec": [
        ZIASZoneConv("moisture", "binary_sensor"),
        ZBatteryPercConv("battery", "sensor", multiply=1.0),
    ],
}, {
    "default": "zigbee",  # default zigbee device
    "spec": [
        ZModelConv("model", "sensor", entity={"category": "diagnostic", "icon": "mdi:information", "lazy": True}),

        ZOnOffConv("switch", "switch", ep=1, bind=True, entity=ENTITY_LAZY),
        ZOnOffConv("channel_2", "switch", ep=2, entity=ENTITY_LAZY),
        ZOnOffConv("channel_3", "switch", ep=3, entity=ENTITY_LAZY),
        ZOnOffConv("channel_4", "switch", ep=4, entity=ENTITY_LAZY),

        ZBrightnessConv("brightness", "number", entity={"lazy": True, "mode": "slider"}),
        ZColorTempConv("color_temp", "number", entity={"lazy": True, "mode": "slider"}),
        ZColorHSConv("hs_color"),
        ZCoverPos("position", "number", entity={"lazy": True, "mode": "slider"}),

        ZAnalogInput("analog", "sensor", round=2, entity=ENTITY_LAZY),
        ZBatteryPercConv("battery", "sensor", entity=ENTITY_LAZY),
        ZBatteryVoltConv("battery_voltage", "sensor", entity=ENTITY_LAZY),
        ZIASZoneConv("binary", "binary_sensor", entity=ENTITY_LAZY),
        ZCurrentConv("current", "sensor", entity=ENTITY_LAZY),
        ZEnergyConv("energy", "sensor", entity=ENTITY_LAZY),
        ZHumidityConv("humidity", "sensor", report="10s 1h 100", entity=ENTITY_LAZY),
        ZIlluminanceConv("illuminance", "sensor", report="10s 1h 100", entity=ENTITY_LAZY),
        ZMultistateInput("multistate", "sensor", entity=ENTITY_LAZY),
        ZOccupancyConv("occupancy", "binary_sensor", entity=ENTITY_LAZY),
        ZPowerConv("power", "sensor", entity=ENTITY_LAZY),
        ZTemperatureConv("temperature", "sensor", report="10s 1h 100", entity=ENTITY_LAZY),
        ZVoltageConv("voltage", "sensor", entity=ENTITY_LAZY),
    ],
}]

########################################################################################
# BLE
########################################################################################

# Xiaomi BLE MiBeacon only spec (mi=15, mi=4100..4121)
# https://custom-components.github.io/ble_monitor/by_brand
DEVICES += [{
    152: ["Xiaomi", "Flower Care", "HHCCJCY01", "hhcc.plantmonitor.v1"],  # 4100,4103,4104,4105
    "spec": [
        BLEMathConv("temperature", "sensor", mi=4100, multiply=0.1, round=1, signed=True),  # int16
        BLEMathConv("illuminance", "sensor", mi=4103),  # uint24
        BLEByteConv("moisture", "sensor", mi=4104),  # uint8
        BLEMathConv("conductivity", "sensor", mi=4105),  # uint16
        BLEByteConv("battery", "sensor", mi=4106, entity=ENTITY_LAZY),  # uint8
    ],
    "ttl": "10m"  # BLE every 10 sec!
}, {
    349: ["Xiaomi", "Flower Pot", "HHCCPOT002", "hhcc.bleflowerpot.v2"],  # 4104,4105
    "spec": [
        BLEByteConv("moisture", "sensor", mi=4104),  # uint8
        BLEMathConv("conductivity", "sensor", mi=4105),  # uint16
        BLEByteConv("battery", "sensor", mi=4106, entity=ENTITY_LAZY),  # uint8
    ],
}, {
    426: ["Xiaomi", "TH Sensor", "LYWSDCGQ/01ZM", "cleargrass.sensor_ht.dk1"],  # 4100,4102,4106
    839: ["Xiaomi", "Qingping TH Sensor", "CGG1", "cgllc.sensor_ht.g1"],
    903: ["Xiaomi", "ZenMeasure TH", "MHO-C401", "miaomiaoce.sensor_ht.h1"],
    1115: ["Xiaomi", "TH Clock", "LYWSD02MMC", "miaomiaoce.sensor_ht.t1"],
    1371: ["Xiaomi", "TH Sensor 2", "LYWSD03MMC", "miaomiaoce.sensor_ht.t2"],
    1398: ["Xiaomi", "Alarm Clock", "CGD1", "cgllc.clock.dove"],
    1647: ["Xiaomi", "Qingping TH Lite", "CGDK2", "cgllc.sensor_ht.dk2"],
    1747: ["Xiaomi", "ZenMeasure Clock", "MHO-C303", "miaomiaoce.clock.ht02"],
    2888: ["Xiaomi", "Qingping TH Sensor", "CGG1", "cgllc.sensor_ht.qpg1"],  # same model as 839?!
    "spec": [
        BLEMathConv("temperature", "sensor", mi=4100, multiply=0.1, round=1, signed=True),
        BLEMathConv("humidity", "sensor", mi=4102, multiply=0.1),
        BLEByteConv("battery", "sensor", mi=4106, entity=ENTITY_LAZY),  # no in new firmwares
        BLETempHumi("th", mi=4109),  # both temperature and humidity
    ],
}, {
    131: ["Xiaomi", "Kettle", "YM-K1501", "yunmi.kettle.v1"],  # CH, HK, RU version
    275: ["Xiaomi", "Kettle", "YM-K1501", "yunmi.kettle.v2"],  # international
    1116: ["Xiaomi", "Viomi Kettle", "V-SK152", "yunmi.kettle.v7"],  # international
    2528: ["Xiaomi", "Kettle Pro", "MJHWSHO2YM", "yunmi.kettle.v12"],  # RU
    "spec": [
        BLEKettle("power", "binary_sensor", mi=4101),  # power+state+temperature
        BaseConv("state", "sensor"),
        BaseConv("temperature", "sensor"),
    ],
    # "ttl": "12h",
}, {
    735: ["Xiaomi", "Honeywell Formaldehyde Monitor", "JQJCY01YM", "yuemee.airmonitor.mhfd1"],
    "spec": [
        BLEMathConv("temperature", "sensor", mi=4100, multiply=0.1, round=1, signed=True),  # int16
        BLEMathConv("humidity", "sensor", mi=4102, multiply=0.1),  # uint16
        BLEByteConv("battery", "sensor", mi=4106, entity=ENTITY_LAZY),  # no in new firmwares
        # https://github.com/AlexxIT/XiaomiGateway3/issues/1177
        BLEMathConv("formaldehyde", "sensor", mi=4112, multiply=0.01),  # uint16
    ],
}, {
    1161: ["Xiaomi", "Toothbrush T500", "MES601", "soocare.toothbrush.m1s"],
    "spec": [
        BaseConv("action", "sensor"),
        BLEByteConv("battery", "sensor", mi=4106),  # uint8
        BLEByteConv("supply", "sensor", mi=4115),  # uint8, Remaining percentage, range 0~100
        BLEToothbrush("toothbrush", mi=16),
    ],
}, {
    1249: ["Xiaomi", "Magic Cube", "XMMF01JQD", "jiqid.robot.cube"],  # 4097
    "spec": [
        BLEMapConv("action", "sensor", mi=4097, map={"000000": "right", "010000": "left"}),
    ],
    # "ttl": "7d",  # don't send any data
}, {
    1694: ["Aqara", "Door Lock N100 (Bluetooth)", "ZNMS16LM", "lumi.lock.bzacn2"],  # 6,7,8,11,4106,4110,4111
    1695: ["Aqara", "Door Lock N200", "ZNMS17LM", "lumi.lock.bzacn1"],  # 6,7,8,11,4106,4110,4111
    7735: ["Lockin", "Smart Door Lock S50M", "loock.lock.fvl109"],  # 6,7,8,11,4106,4110,4111
    "spec": [
        BaseConv("action", "sensor"),
        BaseConv("contact", "binary_sensor"),  # from mi=7
        BLEFinger("fingerprint", mi=6),
        BLEDoor("door", mi=7),
        BLEMapConv("action", mi=8, map={"00": "disarmed", "01": "armed"}),
        BLELock("lock", mi=11),
        BLEByteConv("battery", "sensor", mi=4106),
        BLEMapConv("lock", "binary_sensor", mi=4110, map={"00": True, "01": False}),  # reverse
        BLEMapConv("door", "binary_sensor", mi=4111, map={"00": True, "01": False}),  # reverse
    ]
}, {
    1809: ["Xiaomi", "Air Quality Monitor", "PTH-1", "fbs.airmonitor.pth02"],
    "spec": [
        BLEMathConv("temperature", "sensor", mi=4100, multiply=0.1, round=1, signed=True),  # int16
        BLEMathConv("humidity", "sensor", mi=4102, multiply=0.1),  # uint16
        BLEByteConv("battery", "sensor", mi=4106, entity=ENTITY_LAZY),  # no in new firmwares
        # https://github.com/AlexxIT/XiaomiGateway3/issues/1127
        BLEMathConv("formaldehyde", "sensor", mi=4112, multiply=0.001),  # uint16
    ]
}, {
    1983: ["Yeelight", "Button S1", "YLAI003", "yeelink.remote.remote"],  # 4097,4097
    "spec": [
        BLEMapConv("action", "sensor", mi=4097, map={"000000": "single", "000001": "double", "000002": "hold"}),
        BLEByteConv("battery", "sensor", mi=4106, entity=ENTITY_LAZY),
    ],
    # "ttl": "60m",  # battery every 5 min
}, {
    2038: ["Xiaomi", "Night Light 2", "MJYD02YL-A", "yeelink.light.nl1"],  # 15,4103,4106,4119
    "spec": [
        ConstConv("motion", "binary_sensor", mi=15, value=True),
        BLEMapConv("light", "binary_sensor", mi=15, map={"010000": False, "640000": True}),
        BLEMapConv("light", mi=4103, map={"010000": False, "640000": True}),  # 1 - no light, 100 - light
        BLEByteConv("battery", "sensor", mi=4106),
        BLEMathConv("idle_time", "sensor", mi=4119),
    ],
}, {
    2147: ["Xiaomi", "Water Leak Sensor", "SJWS01LM", "lumi.flood.bmcn01"],
    "spec": [
        BLEMapConv("water_leak", "binary_sensor", mi=4116, map={"00": False, "01": True}),
        BLEMathConv("battery", "sensor", mi=4106),
        BLEMapConv("action", "sensor", mi=4097, map={"000000": BUTTON_SINGLE}, entity=ENTITY_DISABLED),  # button click
    ],
    # "ttl": "60m"  # battery every 4? hour
}, {
    2455: ["Honeywell", "Smoke Alarm", "JTYJ-GD-03MI", "lumi.sensor_smoke.mcn02"],
    "spec": [
        BLEMapConv("smoke", "binary_sensor", mi=4117, map={"00": False, "01": True}),
        BLEMapConv("action", "sensor", mi=4117, map={"02": "error"}, entity=ENTITY_DISABLED),
        BLEByteConv("battery", "sensor", mi=4106),
    ],
    # "ttl": "60m",  # battery every 4:30 min
}, {
    # https://github.com/AlexxIT/XiaomiGateway3/issues/180
    2701: ["Xiaomi", "Motion Sensor 2", "RTCGQ02LM", "lumi.motion.bmgl01"],  # 15,4119,4120,4123
    "spec": [
        ConstConv("motion", "binary_sensor", mi=15, value=True),
        BLEMapConv("light", "binary_sensor", mi=15, map={"000000": False, "000100": True}),  # 0 - moving no light, 256 - moving with light
        BLEByteConv("battery", "sensor", mi=4106),
        BLEMathConv("idle_time", "sensor", mi=4119),
        BLEMapConv("light", mi=4120, map={"00": False, "01": True}),
    ],
}, {
    # https://github.com/AlexxIT/XiaomiGateway3/issues/1012
    2691: ["Xiaomi", "Qingping Motion Sensor", "CGPR1", "cgllc.motion.cgpr1"],  # 15,4103,4119,4120
    "spec": [
        ConstConv("motion", "binary_sensor", mi=15, value=True),
        BLEMathConv("illuminance", "sensor", mi=15),  # moving with illuminance data
        BLEMathConv("illuminance", mi=4103),  # uint24
        BLEBattery2691("battery", "sensor", mi=4106, entity=ENTITY_LAZY),  # battery data with bug
        BaseConv("idle_time", "sensor", mi=4119),  # diagnostic
        BLEMapConv("light", "binary_sensor", mi=4120, map={"00": False, "01": True}),
    ],
    # "ttl": "60m",  # battery every 11 min
}, {
    2443: ["Xiaomi", "Door/Window Sensor 2", "MCCGQ02HL", "isa.magnet.dw2hl"],
    "spec": [
        # https://github.com/AlexxIT/XiaomiGateway3/issues/19
        # 0x00: open the door, 0x01: close the door,
        # 0x02: not closed after timeout, 0x03: device reset
        # hass: On means open, Off means closed
        BLEMapConv("contact", "binary_sensor", mi=4121, map={"00": True, "01": False}),
        BLEMapConv("action", "sensor", mi=4121, map={"02": "timeout", "03": "reset"}, entity=ENTITY_DISABLED),
        BLEMapConv("light", "binary_sensor", mi=4120, map={"00": False, "01": True}),
        BLEByteConv("battery", "sensor", mi=4106, entity=ENTITY_LAZY),
    ],
    # "ttl": "3d",  # battery every 1 day
}]

# Xiaomi BLE MiBeacon2 + MIoT spec
DEVICES += [{
    4611: ["Xiaomi", "TH Sensor", "XMWSDJ04MMC", "miaomiaoce.sensor_ht.t6"],
    "spec": [
        # mibeacon2 spec
        BLEFloatConv("temperature", "sensor", mi=19457, round=1),  # float
        BLEFloatConv("humidity", "sensor", mi=19464, round=1),  # float
        BLEByteConv("battery", "sensor", mi=18435),  # uint8
        # miot https://github.com/AlexxIT/XiaomiGateway3/issues/929
        MathConv("temperature", mi="3.p.1001", round=1),
        MathConv("humidity", mi="3.p.1008", round=1),
        BaseConv("battery", mi="2.p.1003"),
    ],
}, {
    # linp.remote.k9b11
    5481: ["Linptech", "Wireless Button", "k9b11"],
    "spec": [  
        # mibeacon2 spec
        BLEMapConv("action", "sensor", mi=4097, map={"000000": BUTTON_1_SINGLE, "000001": BUTTON_1_DOUBLE, "000002": BUTTON_1_HOLD, "010000": BUTTON_2_SINGLE, "010001": BUTTON_2_DOUBLE, "010002": BUTTON_2_HOLD}),
        BLEByteConv("battery", "sensor", mi=18435, entity=ENTITY_LAZY),  # uint8
        # miot spec
        ConstConv("action", mi="2.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="2.e.2", value=BUTTON_1_DOUBLE),
        ConstConv("action", mi="2.e.3", value=BUTTON_1_HOLD),
        ConstConv("action", mi="4.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="4.e.2", value=BUTTON_2_DOUBLE),
        ConstConv("action", mi="4.e.3", value=BUTTON_2_HOLD),
        BaseConv("battery", mi="3.p.1003"),        
    ],
    # "ttl": "6h"  # battery every 6 hours
}, {
    6473: ["Yeelight", "Double Button", "XMWXKG01YL", "yeelink.remote.contrl"],
    "spec": [
        # mibeacon2 spec
        MapConv("action", mi=19980, map={"01": BUTTON_1_SINGLE, "02": BUTTON_2_SINGLE, "03": BUTTON_BOTH_SINGLE}),
        MapConv("action", mi=19981, map={"01": BUTTON_1_DOUBLE, "02": BUTTON_2_DOUBLE}),
        MapConv("action", mi=19982, map={"01": BUTTON_1_HOLD, "02": BUTTON_2_HOLD}),
        # miot spec
        BaseConv("battery", "sensor", mi="2.p.1003"),
        BaseConv("action", "sensor"),
        MapConv("action", mi="3.e.1012.p.1", map={1: BUTTON_1_SINGLE, 2: BUTTON_2_SINGLE, 3: BUTTON_BOTH_SINGLE}),
        MapConv("action", mi="3.e.1013.p.1", map={1: BUTTON_1_DOUBLE, 2: BUTTON_2_DOUBLE}),
        MapConv("action", mi="3.e.1014.p.1", map={1: BUTTON_1_HOLD, 2: BUTTON_2_HOLD}),
    ],
    # "ttl": "60m",  # battery every 5 min
}, {
    # https://github.com/AlexxIT/XiaomiGateway3/issues/826
    7184: ["Linptech", "Wireless Button", "K11", "linp.remote.k9b01"],
    "spec": [
        # mibeacon2 spec
        BLEMapConv("action", "sensor", mi=19980, map={"01": BUTTON_SINGLE, "08": BUTTON_HOLD, "0F": BUTTON_DOUBLE}),
        BLEByteConv("battery", "sensor", mi=18435),  # uint8
        # miot spec
        MapConv("action", mi="3.e.1012.p.1", map={1: BUTTON_SINGLE, 8: BUTTON_HOLD, 15: BUTTON_DOUBLE}),
        BaseConv("battery", mi="2.p.1003"),
    ],
    # "ttl": "6h"  # battery every 6 hours
}, {
    15895: ["Linptech", "Wireless Button KS1Pro", "KS1PBB", "linp.sensor_ht.ks1bp"],
    "spec": [
        # mibeacon2 https://github.com/AlexxIT/XiaomiGateway3/pull/1228
        BLEFloatConv("temperature", "sensor", mi=18433, round=1),  # float
        BLEFloatConv("humidity", "sensor", mi=18440, round=1),  # float
        BLEByteConv("battery", "sensor", mi=20483),  # uint8
        BaseConv("action", "sensor"),
        BLEMapConv("action", mi=22028, map={"01": BUTTON_1_SINGLE, "02": BUTTON_2_SINGLE, "03": BUTTON_3_SINGLE, "04": BUTTON_4_SINGLE}),
        BLEMapConv("action", mi=22029, map={"01": BUTTON_1_DOUBLE, "02": BUTTON_2_DOUBLE, "03": BUTTON_3_DOUBLE, "04": "button_4_double"}),
        BLEMapConv("action", mi=22030, map={"01": BUTTON_1_HOLD, "02": BUTTON_2_HOLD, "03": BUTTON_3_HOLD, "04": BUTTON_4_HOLD}),
        # miot https://github.com/AlexxIT/XiaomiGateway3/pull/1229
        MathConv("temperature", mi="2.p.1001", round=1),
        MathConv("humidity", mi="2.p.1008", round=1),
        BaseConv("battery", mi="4.p.1003"),
        MapConv("action", mi="5.e.1012.p.1", map={1: BUTTON_1_SINGLE, 2: BUTTON_2_SINGLE, 3: BUTTON_3_SINGLE, 4: BUTTON_4_SINGLE}),
        MapConv("action", mi="5.e.1013.p.1", map={1: BUTTON_1_DOUBLE, 2: BUTTON_2_DOUBLE, 3: BUTTON_3_DOUBLE, 4: "button_4_double"}),
        MapConv("action", mi="5.e.1014.p.1", map={1: BUTTON_1_HOLD, 2: BUTTON_2_HOLD, 3: BUTTON_3_HOLD, 4: BUTTON_4_HOLD}),
    ],
    # "ttl": "6h"  # battery every 6 hours
}, {
    9095: ["Xiaomi", "Wireless Button", "XMWXKG01LM", "lumi.remote.mcn001"],
    "spec": [
        # mibeacon2 spec
        BaseConv("action", "sensor"),
        ConstConv("action", mi=19980, value=BUTTON_SINGLE),
        ConstConv("action", mi=19981, value=BUTTON_DOUBLE),
        ConstConv("action", mi=19982, value=BUTTON_HOLD),
        BLEByteConv("battery", "sensor", mi=18435, entity=ENTITY_LAZY),  # uint8
        # miot spec
        ConstConv("action", mi="3.e.1012", value=BUTTON_SINGLE),
        ConstConv("action", mi="3.e.1013", value=BUTTON_DOUBLE),
        ConstConv("action", mi="3.e.1014", value=BUTTON_HOLD),
        BaseConv("battery", mi="2.p.1003"),
    ],
    # "ttl": "6h"  # battery every 6 hours
}, {
    5860: ["Xiaomi", "TH Clock", "LYWSD02MMC", "miaomiaoce.sensor_ht.o2"],
    9538: ["Xiaomi", "TH Clock Pro", "LYWSD02MMC", "miaomiaoce.sensor_ht.t8"],
    10290: ["Xiaomi", "TH Sensor 3", "MJWSD05MMC", "miaomiaoce.sensor_ht.t9"],
    "spec": [
        # mibeacon2 spec
        BLEFloatConv("temperature", "sensor", mi=19457, round=1),  # float
        BLEByteConv("humidity", "sensor", mi=19458),  # uint8
        BLEByteConv("battery", "sensor", mi=18435, entity=ENTITY_LAZY),  # uint8
        # miot spec
        BaseConv("temperature", mi="3.p.1001"),
        BaseConv("humidity", mi="3.p.1002"),
        BaseConv("battery", mi="2.p.1003"),
    ]
}, {
    10987: ["Linptech", "Motion Sensor 2", "HS1BB", "linp.motion.hs1bb1"],
    "spec": [
        # mibeacon2 spec
        ConstConv("motion", "binary_sensor", mi=18952, value=True),
        BLEFloatConv("illuminance", "sensor", mi=18952, round=0),  # float
        BLEMathConv("idle_time", "sensor", mi=18456),  # uint16
        BLEByteConv("battery", "sensor", mi=19459),  # uint8
        BaseConv("unknown", mi=18953),
        # miot spec
        MathConv("illuminance", mi="2.e.1008.p.1005", round=0),
        ConstConv("motion", mi="2.e.1008", value=True),
        BaseConv("battery", mi="3.p.1003"),
        BaseConv("idle_time", mi="2.p.1024"),
    ],
}, {
    # https://home.miot-spec.com/spec/xiaomi.sensor_occupy.03
    18051: ["Xiaomi", "Occupancy Sensor", "XMOSB01XS", "xiaomi.sensor_occupy.03"],
    "spec": [
        # main sensors
        BoolConv("occupancy", "binary_sensor", mi="2.p.1078"),
        BaseConv("illuminance", "sensor", mi="2.p.1005"),
        # other sensors
        BaseConv("battery", "sensor", mi="3.p.1003", entity=ENTITY_LAZY),
        BaseConv("has_someone_duration", "sensor", mi="2.p.1081", entity=ENTITY_DISABLED),
        BaseConv("no_one_duration", "sensor", mi="2.p.1082", entity=ENTITY_DISABLED),
    ],
}, {
    # https://github.com/AlexxIT/XiaomiGateway3/pull/1118
    13617: ["xiaomi", "Motion Sensor 2s", "XMPIRO25XS", "xiaomi.motion.pir1"],
    "spec": [
        # miot format
        ConstConv("motion", "binary_sensor", mi="2.e.1008", value=True),
        BaseConv("illuminance", "sensor", mi="2.p.1005"),
        BaseConv("battery", "sensor", mi="3.p.1003"),
        BaseConv("idle_time", "sensor", mi="2.p.1024"),  # no-motion-duration
        # BaseConv("idle_time", mi="2.p.1053"),  # custom-no-motion-time
    ],
}, {
    8613: ["H+", "Double Wall Switch", "huca.switch.dh2"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
    ],    
}, {
    12382: ["H+", "Wireless Button", "huca.remote.wx8"],
    "spec": [
        BaseConv("action", "sensor"),
        BaseConv("battery", "sensor", mi="13.p.1003"),
        MapConv("action", mi="12.e.1012.p.1", map={1: BUTTON_1_SINGLE, 2: BUTTON_2_SINGLE, 3: BUTTON_3_SINGLE, 4: BUTTON_4_SINGLE, 5: "button_5_single", 6: "button_6_single", 7: "button_7_single", 8: "button_8_single"}),
        MapConv("action", mi="12.e.1013.p.1", map={1: BUTTON_1_DOUBLE, 2: BUTTON_2_DOUBLE, 3: BUTTON_3_DOUBLE, 4: "button_4_double", 5: "button_5_double", 6: "button_6_double", 7: "button_7_double", 8: "button_8_double"}),
    ],
    # "ttl": "6h"  # battery every 6 hours
}, {
    6742: ["LeMesh", "Wireless Button", "lemesh.remote.ts1"],
    "spec": [
        BaseConv("action", "sensor"),
        MapConv("action", mi="2.e.1012.p.1", map={1: BUTTON_1_SINGLE, 2: BUTTON_2_SINGLE, 3: BUTTON_3_SINGLE, 4: BUTTON_4_SINGLE, 5: "button_5_single", 6: "button_6_single", 7: "button_7_single", 8: "button_8_single"}),
        MapConv("action", mi="2.e.1013.p.1", map={1: BUTTON_1_DOUBLE, 2: BUTTON_2_DOUBLE, 3: BUTTON_3_DOUBLE, 4: "button_4_double", 5: "button_5_double", 6: "button_6_double", 7: "button_7_double", 8: "button_8_double"}),
        MapConv("action", mi="2.e.1014.p.1", map={1: BUTTON_1_HOLD, 2: BUTTON_2_HOLD, 3: BUTTON_3_HOLD, 4: BUTTON_4_HOLD, 5: "button_5_hold", 6: "button_6_hold", 7: "button_7_hold", 8: "button_8_hold"}),
    ]
}, {
    16186: ["Smartfrog", "Wireless Button", "giot.remote.v58kwm"],
    "spec": [
        BaseConv("action", "sensor"),
        MapConv("action", mi="2.e.1012.p.1", map={1: BUTTON_1_SINGLE, 2: BUTTON_2_SINGLE, 3: BUTTON_3_SINGLE, 4: BUTTON_4_SINGLE, 5: "button_5_single", 6: "button_6_single", 7: "button_7_single", 8: "button_8_single"}),
        MapConv("action", mi="2.e.1013.p.1", map={1: BUTTON_1_DOUBLE, 2: BUTTON_2_DOUBLE, 3: BUTTON_3_DOUBLE, 4: "button_4_double", 5: "button_5_double", 6: "button_6_double", 7: "button_7_double", 8: "button_8_double"}),
        MapConv("action", mi="2.e.1014.p.1", map={1: BUTTON_1_HOLD, 2: BUTTON_2_HOLD, 3: BUTTON_3_HOLD, 4: BUTTON_4_HOLD, 5: "button_5_hold", 6: "button_6_hold", 7: "button_7_hold", 8: "button_8_hold"}),
    ]
}, {
    # https://home.miot-spec.com/spec?type=urn:miot-spec-v2:device:timer:0000A0BD:hoto-kt:1
    9385: ["Mijia", "Timer", "hoto.timer.kt"],
    "spec": [
        BaseConv("action", "sensor"),
        ConstConv("action", mi="2.e.1025", value="timer1"),
        ConstConv("action", mi="3.e.1025", value="timer2"),
    ],
}, {
    16143: ["Linptech", "Submersion Sensor", "RS1BB", "linp.flood.rs1bb"],
    "spec": [
        BLEMapConv("water_leak", "binary_sensor", mi=18438, map={"00": False, "01": True}),
        BLEByteConv("battery", "sensor", mi=19459),
        BaseConv("water_leak", mi="2.p.1006"),  # bool
        BaseConv("battery", mi="3.p.1003"),  # uint8
    ],
}, {
    16204: ["Linptech", "Pressure Sensor", "PS1BB", "linp.senpres.ps1bb"],
    "spec": [
        BoolConv("pressure", "binary_sensor", mi="2.p.1060"),  # bool
        BaseConv("battery", "sensor", mi="3.p.1003"),  # uint8
        # just converters
        BaseConv("present_duration", mi="2.p.1061"),  # uint32, seconds
        BaseConv("not_present_duration", mi="2.p.1062"),  # uint32, seconds
        BaseConv("present_time_set", mi="2.p.1063"),  # uint32, seconds
        BaseConv("not_present_time_set", mi="2.p.1064"),  # uint32, seconds
        # BaseConv("led", "sensor", mi="4.p.1"),  # bool
    ],
}, {
    6281: ["Linptech", "Door/Window Sensor", "MS1BB", "linp.magnet.m1"],
    "spec": [
        MapConv("contact", "binary_sensor", mi="2.p.1004", map={1: True, 2: False}),
        BaseConv("battery", "sensor", mi="3.p.1003"),
    ],
    # "ttl": "60m",
}, {
    6017: ["Xiaomi", "Face Recognition Smart Door Lock", "XMZNMS09LM", "lumi.lock.mcn002"],
    "spec": [
        BaseConv("action", "sensor"),
        BaseConv("battery", "sensor", mi="4.p.1003"),
        # Hass: On means open (unlocked), Off means closed (locked)
        MapConv("lock", "binary_sensor", mi="2.e.1020.p.3", map={1: False, 2: True, 3: False, 4: False, 5: True}),
        # error action
        ConstConv("action", mi="2.e.1007", value="error"),
        BaseConv("error_id", mi="2.e.1007.p.4"),
        BaseConv("timestamp", mi="2.e.1007.p.2"),
        # lock action
        ConstConv("action", mi="2.e.1020", value="lock"),
        BaseConv("key_id", mi="2.e.1020.p.1"),
        BaseConv("timestamp", mi="2.e.1020.p.2"),
        BaseConv("action_id", mi="2.e.1020.p.3"),
        MapConv("action", mi="2.e.1020.p.3", map={1: "lock", 2: "unlock", 3: "lock_outside", 4: "lock_inside", 5: "unlock_inside", 6: "enable_child_lock", 7: "disable_child_lock", 8: "enable_away", 9: "disable_away"}),
        BaseConv("method_id", mi="2.e.1020.p.5"),
        MapConv("method", mi="2.e.1020.p.5", map={1: "mobile", 2: "fingerprint", 3: "password", 4: "nfc", 5: "face", 8: "key", 9: "one_time_password", 10: "periodic_password", 12: "coerce", 15: "manual", 16: "auto"}),
        MapConv("position", mi="2.e.1020.p.6", map={1: "indoor", 2: "outdoor", 3: "not tell indoor or outdoor"}),
        # doorbell
        ConstConv("action", mi="5.e.1006", value="doorbell"),
        BaseConv("timestamp", mi="5.e.1006.p.1"),
    ],
    # "ttl": "25h"
}, {
    # https://github.com/AlexxIT/XiaomiGateway3/issues/973
    10249: ["Xiaomi", "Door Lock E10", "XMZNMS01OD", "oms.lock.dl01"],
    "spec": [
        BaseConv("action", "sensor"),
        MapConv("door", "sensor", mi="4.p.1021", map={1: "locked", 2: "unlocked", 3: "timeout", 4: "ajar"}),
        BaseConv("battery", "sensor", mi="5.p.1003"),
        # lock action
        MapConv("action", mi="3.e.1020.p.3", map={1: "lock", 2: "unlock", 3: "lock_outside", 4: "lock_inside", 5: "unlock_inside", 8: "enable_away", 9: "disable_away"}),
        BaseConv("key_id", mi="3.e.1020.p.1"),
        BaseConv("method_id", mi="3.e.1020.p.2"),
        MapConv("method", mi="3.e.1020.p.2", map={1: "mobile", 2: "fingerprint", 3: "password", 4: "nfc", 8: "key", 9: "one_time_password", 10: "periodic_password", 12: "coerce", 15: "manual"}),
        BaseConv("action_id", mi="3.e.1020.p.3"),
        MapConv("position", mi="3.e.1020.p.4", map={1: "indoor", 2: "outdoor"}),
        BaseConv("timestamp", mi="3.e.1020.p.6"),
        # doorbell action
        ConstConv("action", mi="6.e.1006", value="doorbell"),
        BaseConv("timestamp", mi="6.e.1006.p.1"),
    ],
    # "ttl": "25h"
}, {
    1393: ["Xiaomi", "Safe Cayo Anno 30Z", "lcrmcr.safe.ms30b"],
    "spec": [
        BaseConv("action", "sensor"),
        BaseConv("battery", "sensor", mi="4.p.1"),
        # open action
        ConstConv("action", mi="2.e.1", value="open"),
        MapConv("method", mi="2.e.1.p.1", map={0: "mobile", 2: "fingerprint", 4: "key"}),
        BaseConv("action_id", mi="2.e.1.p.2"),
        # error action
        ConstConv("action", mi="2.e.4", value="error"),
        MapConv("error", mi="2.e.4.p.3", map={1: "wrong_fingerprint", 3: "lockpicking", 8: "timeout_not_locked"}),
        BaseConv("timestamp", mi="2.e.4.p.4"),
        # battery action
        ConstConv("action", mi="4.e.1", value="battery_low"),
    ],
    # "ttl": "25h"
}, {
    # https://home.miot-spec.com/spec/lcrmcr.lock.cb2207
    11450: ["CRMCR", "intelligent glass door lock", "lcrmcr.lock.cb2207"],
    "spec": [
        BaseConv("action", "sensor"),  # state changes when below actions are triggered, like wireless button
        ConstConv("action", mi="3.e.1020", value="lock_event"),
        ConstConv("action", mi="3.e.1007", value="exception_occurred"),
        ConstConv("action", mi="5.e.1001", value="low_battery"), 
        BaseConv("last_lock_action", "sensor", mi="3.e.1020.p.1"),  # seems no use, sensor always "0"
        MapConv("last_method", "sensor", mi="3.e.1020.p.2", map={1: "ble", 2: "password", 3: "fingerprint", 4: "nfc", 5: "otp", 6: "indoor", 7: "remoter"}),
        MathConv("last_user_id", "sensor", mi="3.e.1020.p.3", min=0, max=65534),  # blocked sensor revert to "65535"
        MapConv("last_error", "sensor", mi="3.e.1007.p.5", map={1: "wrong_password", 2: "wrong_fingerprint", 3: "worng_nfc", 4: "battery_low"}),
        BaseConv("battery", "sensor", mi="5.p.1003"),
    ],
    # "ttl": "25h"
}, {
    11273: ["PTX", "BLE Wireless situation knob switch", "PTX-X6-QMIMB", "090615.remote.x6xnsw"],
    "spec": [
        BaseConv("action", "sensor"),
        ConstConv("action", mi="2.e.1012", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="2.e.1013", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="2.e.1014", value=BUTTON_3_SINGLE),
        ConstConv("action", mi="2.e.1028", value=BUTTON_4_SINGLE),
        ConstConv("action", mi="3.e.1012", value="knob_increasing"),
        ConstConv("action", mi="3.e.1013", value="knob_reduced"),
        ConstConv("action", mi="3.e.1014", value="knob_press"),
    ],
    # "ttl": "7d"
}, {
    12183: ["Lockin", "Door Lock M20 Pro", "loock.lock.r2"],
    "spec": [
        # lock action
        BaseConv("action", "sensor"),
        MapConv("position", mi="2.e.1020.p.1", map={1: "indoor", 2: "outdoor", 3: "unknown"}),
        BaseConv("method_id", mi="2.e.1020.p.2"),
        BaseConv("action_id", mi="2.e.1020.p.3"),
        BaseConv("key_id", mi="2.e.1020.p.4"),
        BaseConv("timestamp", mi="2.e.1020.p.5"),
        MapConv("action", mi="2.e.1020.p.3", map={1: "lock", 2: "unlock", 3: "lock_outside", 4: "lock_inside", 5: "unlock_inside", 6: "child_lock", 7: "child_unlock", 8: "enable_away", 9: "disable_away"}),
        MapConv("method", mi="2.e.1020.p.2", map={1: "mobile", 2: "fingerprint", 3: "password", 4: "nfc", 5: "face", 8: "key", 9: "one_time_password", 10: "periodic_password", 12: "coerce", 15: "manual", 16: "auto"}),
        # door state, On means open, Off means closed
        MapConv("door", "binary_sensor", mi="3.p.1021", map={16: STATE_LOCKED, 20: STATE_LOCKED, 24: STATE_LOCKED, 28: STATE_LOCKED, 32: STATE_UNLOCK, 36: STATE_UNLOCK, 40: STATE_UNLOCK, 44: STATE_UNLOCK}),
        # doorbell action
        ConstConv("action", mi="5.e.1006", value="doorbell"),
        BaseConv("timestamp", mi="5.e.1006.p.1"),
        # lock binary_sensor
        MapConv("lock", "binary_sensor", mi="2.e.1020.p.3", map={1: STATE_LOCKED, 2: STATE_UNLOCK}),
    ],
    # "ttl": "25h"
}, {
    14456: ["LeMesh", "Scenario wireless knob switch K4", "lemesh.remote.ts4"],
    "spec": [
        BaseConv("battery", "sensor", mi="4.p.1003"),  # uint8
        BaseConv("action", "sensor"),
        MapConv("action", mi="5.e.1012.p.1", map={1: "knob_single", 2: BUTTON_1_SINGLE, 3: BUTTON_2_SINGLE, 4: BUTTON_3_SINGLE, 5: BUTTON_4_SINGLE, 6: "knob_increasing", 7: "knob_reduced", 8: "knob_hold_increasing", 9: "knob_hold_reduced"}),
        MapConv("action", mi="5.e.1013.p.1", map={1: "knob_double", 2: BUTTON_1_DOUBLE, 3: BUTTON_2_DOUBLE, 4: BUTTON_3_DOUBLE, 5: BUTTON_4_DOUBLE}),
        MapConv("action", mi="5.e.1014.p.1", map={1: "knob_hold", 2: BUTTON_1_HOLD, 3: BUTTON_2_HOLD, 4: BUTTON_3_HOLD, 5: BUTTON_4_HOLD}),
    ],
    # "ttl": "6h"  # battery every 6 hours
}, {
    14468: ["LeMesh", "Triple Wall Switch", "lemesh.switch.sw3f01"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
    ],
}, {
    14469: ["LeMesh", "Double Wall Switch", "lemesh.switch.sw2f01"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
    ],
}, {
    14523: ["PTX", "BLE Wireless Switch", "090615.remote.btsw1"],
    "spec": [
        BaseConv("action", "sensor"),
        ConstConv("action", mi="2.e.1012", value=BUTTON_SINGLE),
        ConstConv("action", mi="2.e.1013", value=BUTTON_DOUBLE),
        ConstConv("action", mi="2.e.1014", value=BUTTON_HOLD),
    ],
}, {
    14608: ["PTX", "Mesh Wireless Switch", "PTX-AK1-QMIMC", "090615.remote.akswr1"],
    "spec": [
        BaseConv("action", "sensor"),
        ConstConv("action", mi="2.e.1012", value=BUTTON_SINGLE),
        ConstConv("action", mi="2.e.1014", value=BUTTON_HOLD),
        ConstConv("action", mi="3.e.1001", value="low_battery"),
    ],
}, {
    14609: ["PTX", "Mesh Double Wireless Switch", "PTX-AK2-QMIMB", "090615.remote.akswr2"],
    "spec": [
        BaseConv("action", "sensor"),
        ConstConv("action", mi="2.e.1012", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="2.e.1014", value=BUTTON_1_HOLD),
        ConstConv("action", mi="3.e.1001", value="low_battery"),
        ConstConv("action", mi="4.e.1012", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="4.e.1014", value=BUTTON_2_HOLD),
    ],
}, {
    14610: ["PTX", "Mesh Triple Wireless Switch", "PTX-AK3-QMIMB", "090615.remote.akswr3"],
    "spec": [
        BaseConv("action", "sensor"),
        ConstConv("action", mi="2.e.1012", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="2.e.1014", value=BUTTON_1_HOLD),
        ConstConv("action", mi="3.e.1001", value="low_battery"),
        ConstConv("action", mi="4.e.1012", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="4.e.1014", value=BUTTON_2_HOLD),
        ConstConv("action", mi="5.e.1012", value=BUTTON_3_SINGLE),
        ConstConv("action", mi="5.e.1014", value=BUTTON_3_HOLD),
    ],
}, {
    # https://github.com/AlexxIT/XiaomiGateway3/pull/1294
    14945: ["Linptech", "Wireless Button KS1", "linp.remote.ks1"],
    "spec": [
        BaseConv("battery", mi="4.p.1003"),
        BaseConv("action", "sensor"),
        MapConv("action", mi="5.e.1012.p.1", map={1: BUTTON_1_SINGLE, 2: BUTTON_2_SINGLE, 3: BUTTON_3_SINGLE, 4: BUTTON_4_SINGLE}),
        MapConv("action", mi="5.e.1013.p.1", map={1: BUTTON_1_DOUBLE, 2: BUTTON_2_DOUBLE, 3: BUTTON_3_DOUBLE, 4: BUTTON_4_DOUBLE}),
        MapConv("action", mi="5.e.1014.p.1", map={1: BUTTON_1_HOLD, 2: BUTTON_2_HOLD, 3: BUTTON_3_HOLD, 4: BUTTON_4_HOLD}),
    ],
    # "ttl": "6h"  # battery every 6 hours
}, {
    # https://github.com/AlexxIT/XiaomiGateway3/pull/1303
    17825: ["Unknown", "Eight scene knob switch", "cxw.remote.ble006"],
    "spec": [
        BaseConv("battery", mi="7.p.1003"),  # uint8
        BaseConv("action", "sensor"),
        MapConv("action", mi="5.e.1012.p.1", map={1: BUTTON_1_SINGLE, 2: BUTTON_2_SINGLE, 3: BUTTON_3_SINGLE, 4: BUTTON_4_SINGLE, 5: "button_5_single", 6: "button_6_single", 7: "button_7_single", 8: "button_8_single"}),
        MapConv("action", mi="5.e.1013.p.1", map={1: BUTTON_1_DOUBLE, 2: BUTTON_2_DOUBLE, 3: BUTTON_3_DOUBLE, 4: BUTTON_4_DOUBLE, 5: "button_5_double", 6: "button_6_double", 7: "button_7_double", 8: "button_8_double"}),
        MapConv("action", mi="5.e.1014.p.1", map={1: BUTTON_1_HOLD, 2: BUTTON_2_HOLD, 3: BUTTON_3_HOLD, 4: BUTTON_4_HOLD, 5: "button_5_hold", 6: "button_6_hold", 7: "button_7_hold", 8: "button_8_hold"}),
        ConstConv("action", mi="5.e.1036", value="rotate"),
        BaseConv("rotate", mi="5.e.1036.p.2"),
    ],
    # "ttl": "6h"  # battery every 6 hours
}, {
    # https://home.miot-spec.com/spec/ailol.remote.ts4
    18250: ["ZXFANS", "ZXFANS F2 smart knob remote control", "ailol.remote.ts4"],
    "spec": [
        BaseConv("battery", "sensor", mi="4.p.1003"),
        BaseConv("action", "sensor"),
        MapConv("action", mi="5.e.1012.p.1", map={1: BUTTON_1_SINGLE, 2: BUTTON_2_SINGLE, 3: BUTTON_3_SINGLE, 4: BUTTON_4_SINGLE, 5: "knob_increasing", 6: "knob_reduced"}),
        MapConv("action", mi="5.e.1013.p.1", map={1: BUTTON_1_DOUBLE, 2: BUTTON_2_DOUBLE, 3: BUTTON_3_DOUBLE, 4: BUTTON_4_DOUBLE}),
        MapConv("action", mi="5.e.1014.p.1", map={1: BUTTON_1_HOLD, 2: BUTTON_2_HOLD, 3: BUTTON_3_HOLD, 4: BUTTON_4_HOLD}),
    ]
}, {
    # BLE devices can be supported witout spec. New spec will be added "on the fly" when
    # device sends them. But better to rewrite right spec for each device
    "default": "ble",  # default BLE device
    794: ["Xiaomi", "Door Lock", "MJZNMS02LM", "lumi.lock.mcn01"],
    955: [None, "Lock M2", "ydhome.lock.m2silver"],
    982: ["Xiaomi", "Qingping Door Sensor", "CGH1", "cgllc.magnet.hodor"],
    1034: ["Xiaomi", "Mosquito Repellent", "WX08ZM", "zimi.mosq.v1"],
    # https://github.com/AlexxIT/XiaomiGateway3/issues/1001
    1203: ["Dessmann ", "Q3", "dsm.lock.q3"],
    1433: ["Xiaomi", "Door Lock", "MJZNMS03LM", "lumi.lock.bzacn2"],
    2054: ["Xiaomi", "Toothbrush T700", "MES604", "k0918.toothbrush.t700"],
    # https://github.com/AlexxIT/XiaomiGateway3/issues/657
    2444: ["Lockin", "Door Lock", "XMZNMST02YD", "loock.lock.t1"],
    2480: ["Lockin", "Safe Box", "BGX-5/X1-3001", "loock.safe.v1"],
    3051: ["Aqara", "Door Lock D100", "ZNMS20LM", "lumi.lock.bacn01"],
    3343: ["Lockin", "Door Lock Classic 2X Pro", "loock.lock.cc2xpro"],
    3641: ["Xiaomi", "Door Lock 1S", "XMZNMS08LM", "lumi.lock.bmcn04"],
    # https://github.com/AlexxIT/XiaomiGateway3/issues/776
    3685: ["Xiaomi", "Face Recognition Smart Door Lock X", "XMZNMS06LM", "lumi.lock.bmcn05"],
    # https://github.com/AlexxIT/XiaomiGateway3/issues/1156
    3899: ["Lockin", "Door Lock", "XMZNMSTO3YD", "loock.lock.t1pro"],
    6032: ["Xiaomi", "Toothbrush T700i", "MES604", "k0918.toothbrush.t700i"],
    "spec": [
        # https://iot.mi.com/new/doc/accesses/direct-access/embedded-development/ble/object-definition
        # old link: https://iot.mi.com/new/doc/embedded-development/ble/object-definition
        # sensors
        BaseConv("action", "sensor", mi=4097, entity=ENTITY_LAZY),
        BLEMapConv("sleep", "binary_sensor", mi=4098, map={"00": False, "01": True}, entity=ENTITY_LAZY),
        BLEByteConv("rssi", "sensor", mi=4099, entity=ENTITY_LAZY),  # uint8, Signal strength value
        BLEMathConv("temperature", "sensor", mi=4100, multiply=0.1, round=1, signed=True, entity=ENTITY_LAZY),  # int16
        BLEKettle("power", "sensor", mi=4101, entity=ENTITY_LAZY),
        BLEMathConv("humidity", "sensor", mi=4102, multiply=0.1, round=1, entity=ENTITY_LAZY),  # uint16
        BLEMathConv("illuminance", "sensor", mi=4103, entity=ENTITY_LAZY),  # uint24, Range: 0-120000, lux
        BLEByteConv("moisture", "sensor", mi=4104, entity=ENTITY_LAZY),  # uint8, Humidity percentage, range: 0-100
        BLEMathConv("conductivity", "sensor", mi=4105, entity=ENTITY_LAZY),  # uint16, Soil EC value, Unit us/cm, range: 0-5000
        BLEByteConv("battery", "sensor", mi=4106, entity=ENTITY_LAZY),  # uint8
        BLEMapConv("lock", "binary_sensor", mi=4110, map={"00": True, "01": False}, entity=ENTITY_LAZY),  # reverse
        BLEMapConv("door", "binary_sensor", mi=4111, map={"00": True, "01": False}, entity=ENTITY_LAZY),  # reverse
        BLEMathConv("formaldehyde", "sensor", mi=4112, multiply=0.01, entity=ENTITY_LAZY),  # uint16
        BLEMapConv("opening", "binary_sensor", mi=4114, map={"00": False, "01": True}, entity=ENTITY_LAZY),
        BLEByteConv("supply", "sensor", mi=4115, entity=ENTITY_LAZY),  # uint8, Remaining percentage, range 0~100
        BLEMapConv("water_leak", "binary_sensor", mi=4116, map={"00": False, "01": True}, entity=ENTITY_LAZY),
        BLEMapConv("smoke", "binary_sensor", mi=4117, map={"00": False, "01": True}, entity=ENTITY_LAZY),
        BLEMapConv("gas", "binary_sensor", mi=4118, map={"00": False, "01": True}, entity=ENTITY_LAZY),
        BLEMathConv("idle_time", "sensor", mi=4119, entity=ENTITY_LAZY),  # uint16
        BLEMapConv("light", "binary_sensor", mi=4120, map={"00": False, "01": True}, entity=ENTITY_LAZY),
        BLEMapConv("contact", "binary_sensor", mi=4121, map={"00": True, "01": False}, entity=ENTITY_LAZY),  # reverse
        ConstConv("motion", "binary_sensor", mi=15, value=True, entity=ENTITY_LAZY),
        # just converters
        BLETempHumi("temp_humi", mi=4109),  # temperature + humidity
        BLEFinger("fingerprint", mi=6),
        BLEDoor("door", mi=7),
        ConstConv("action", mi=8, value="armed"),
        BLELock("lock", mi=11),
        BLEToothbrush("toothbrush", mi=16),
    ],
}]

########################################################################################
# Mesh
########################################################################################


DEVICES += [{
    # brightness 1..65535, color_temp 2700..6500
    948: ["Yeelight", "Mesh Downlight", "YLSD01YL", "yeelink.light.dnlight2"],  # flex
    995: ["Yeelight", "Mesh Bulb E14", "YLDP09YL", "yeelink.light.meshbulb2"],  # flex
    996: ["Yeelight", "Mesh Bulb E27", "YLDP10YL", "yeelink.light.meshbulb1"],  # flex
    997: ["Yeelight", "Mesh Spotlight", "YLSD04YL", "yeelink.light.spot1"],  # flex
    1771: ["Xiaomi", "Mesh Bulb", "MJDP09YL", "yeelink.light.mbulb3"],  # flex
    1772: ["Xiaomi", "Mesh Downlight", "MJTS01YL/MJTS003", "yeelink.light.light3"],  # flex
    3291: ["Yeelight", "Mesh Downlight M1", "YLSD001", "yeelink.light.ml3"],  # flex
    2076: ["Yeelight", "Mesh Downlight M2", "YLTS02YL/YLTS04YL", "yeelink.light.ml1"],  # flex
    2342: ["Yeelight", "Mesh Bulb M2", "YLDP25YL/YLDP26YL", "yeelink.light.ml2"],  # flex
    "support": 4,  # @AlexxIT TODO: power_on_state values
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", max=65535),
        ColorTempKelvin("color_temp", mi="2.p.3"),
        BoolConv("flex_switch", "switch", mi="3.p.5"),  # uint8, config
        MapConv("power_on_state", "select", mi="3.p.11", map={0: "off", 1: "default"}),  # uint32, config
    ],
}, {
    # https://home.miot-spec.com/spec/crzm.light.w00a01
    2292: ["crzm", "Mesh Light", "crzm.light.w00a01"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", max=100),
    ]
}, {
    # brightness 1..100, color_temp 2700..6500
    3416: ["PTX", "Mesh Downlight", "090615.light.mlig01"],
    4924: ["PTX", "Mesh Downlight", "090615.light.mlig02"],
    4945: ["PTX", "Mesh Lightstrip", "090615.light.mdd02"],
    7057: ["PTX", "Mesh Light", "090615.light.cxlg01"],
    15169: ["PTX", "Mesh Downlight", "090615.light.mylg04"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3"),
    ]
}, {
    # brightness 1..100, color_temp 3000..6400
    1910: ["LeMesh", "Mesh Light (RF ready)", "lemesh.light.wy0c02"],
    2293: [None, "Mesh Lightstrip (RF ready)", "crzm.light.wy0a01"],
    2351: ["LeMesh", "Mesh Downlight", "lemesh.light.wy0c05"],
    2584: ["XinGuang", "Light", "LIBMDA09X", "wainft.light.wy0a01"],
    3164: ["LeMesh", "Mesh Light (RF ready)", "lemesh.light.wy0c07"],
    7136: ["LeMesh", "Mesh Light v2", "lemesh.light.wy0c09"],
    9439: ["GDDS", "Mesh Light", "gdds.light.wy0a01"],
    12757: ["KOEY", "Mesh Downlight", "koey.light.wy0a01"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", mink=3000, maxk=6400),
    ]
}, {
    3531: ["LeMesh", "Mesh Light", "lemesh.light.wy0c08"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", mink=3000, maxk=6400),
        MapConv("mode", "select", mi="2.p.5", map={0: "WY", 4: "day", 5: "night", 8: "TV", 9: "reading", 10: "computer", 11: "hospitality", 12: "entertainment", 13: "wakeup", 14: "dusk", 15: "sleep"}),
        MapConv("power_on_state", "select", mi="4.p.1", map={0: "default", 1: "on"}),
        BoolConv("save_state", "switch", mi="4.p.2"),
        MapConv("dimming", "select", mi="4.p.3", map={0: "Gradient", 1: "Immediately"}),
        BoolConv("night_light", "switch", mi="4.p.5"),
    ]
}, {
    11901: ["Yeelight", "Mesh Light Strip C1", "yeelink.light.stripf"],
    11667: ["Yeelight", "Mesh Downlight C1", "YCCBC1019/YCCBC1020", "yeelink.light.ml9"],  # flex
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", mink=3000, maxk=6400),
        MapConv("mode", "select", mi="2.p.5", map={0: "WY", 4: "day", 5: "night", 8: "TV", 9: "reading", 10: "computer", 11: "hospitality", 12: "entertainment", 13: "wakeup", 14: "dusk", 15: "sleep"}),
        BaseConv("flex_switch", "switch", mi="2.p.6"),  # uint8, config
        MapConv("power_on_state", "select", mi="2.p.7", map={0: "default", 1: "on"}),  # config
        BoolConv("save_state", "switch", mi="4.p.2"),
        MapConv("dimming", "select", mi="4.p.3", map={0: "Gradient", 1: "Immediately"}),
        BoolConv("night_light", "switch", mi="4.p.5"),
    ]
}, {
    10055: ["Symi", "Mesh Light", "symi.light.wy0a01"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", mink=3000, maxk=6400),
        MapConv("mode", "select", mi="2.p.5", map={0: "WY", 4: "day", 5: "night", 7: "Warmth", 8: "TV", 9: "reading", 10: "computer", 11: "hospitality", 12: "entertainment", 13: "wakeup", 14: "dusk", 15: "sleep", 16: "Respiration", 17: "Loop Jump"}),
        BaseConv("flex_switch", "switch", mi="2.p.6"),  # uint8, config
        MapConv("power_on_state", "select", mi="2.p.7", map={0: "default", 1: "on"}),  # config
        BoolConv("save_state", "switch", mi="4.p.2"),
        MapConv("dimming", "select", mi="4.p.3", map={0: "Gradient", 1: "Immediately"}),
        BoolConv("night_light", "switch", mi="4.p.5"),
    ]
}, {
    13471: ["LeMesh", "Mesh Light", "lemesh.light.wy0c14"],
    13525: ["LeMesh", "Mesh Light", "lemesh.light.wy0c15"],
    14335: ["Yeelight", "Yeelight Smart Light", "yeelink.light.wy0a03"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", mink=2700, maxk=6500),
        MapConv("mode", "select", mi="2.p.5", map={0: "WY", 4: "day", 5: "night", 8: "TV", 9: "reading", 10: "computer", 11: "hospitality", 12: "entertainment", 13: "wakeup", 14: "dusk", 15: "sleep"}),
        BaseConv("flex_switch", "switch", mi="2.p.6"),  # uint8, config
        MapConv("power_on_state", "select", mi="2.p.7", map={0: "default", 1: "on"}),  # config
        BoolConv("save_state", "switch", mi="4.p.2"),
        MapConv("dimming", "select", mi="4.p.3", map={0: "Gradient", 1: "Immediately"}),
        BoolConv("night_light", "switch", mi="4.p.5"),
    ]
}, {
    16697: ["LeMesh", "Mesh Light", "lemesh.light.wy0a20"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", mink=2700, maxk=6500),
        MapConv("mode", "select", mi="2.p.7", map={0: "None", 4: "lighting", 5: "night", 7: "warmth", 8: "TV", 9: "reading", 10: "computer", 11: "hospitality", 12: "entertainment", 13: "wakeup", 14: "dusk", 15: "sleep"}),
        MapConv("power_on_state", "select", mi="2.p.9", map={0: "default", 1: "on", 2: "off"}),
    ],
}, {
    17964: ["LeMesh", "Smart downlight Mesh version", "mvs.light.wy0a01"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", mink=2700, maxk=6500),
        MapConv("mode", "select", mi="2.p.7", map={0: "None", 4: "Sun", 5: "Moon", 7: "Warmth", 8: "Cinema", 9: "Reading", 10: "Computer", 11: "Hospitality", 12: "Entertainment", 13: "Wakeup", 14: "Dusk", 15: "Sleep", 16: "Custom1", 17: "Custom2", 18: "Custom3", 19: "Custom4"}),
        MapConv("power_on_state", "select", mi="2.p.9", map={0: "Default", 1: "ON", 2: "OFF"}),  # config
        BaseConv("flex_switch", "switch", mi="2.p.12"),  # uint8, config
        BoolConv("night_light", "switch", mi="2.p.13", entity=ENTITY_CONFIG),  # config
        BoolConv("save_state", "switch", mi="5.p.1", entity=ENTITY_CONFIG),  # config
        MapConv("dimming", "select", mi="5.p.2", map={0: "Gradient", 1: "Immediately"}, entity=ENTITY_CONFIG),  # config
    ]
}, {
    17157: ["LeMesh", "Scene Mesh monochrome light V2S series", "lemesh.light.w00a02"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", max=100),
        MapConv("mode", "select", mi="2.p.7", map={0: "None", 4: "Sun", 5: "Moon", 7: "Warmth", 8: "Cinema", 9: "Reading", 10: "Computer", 11: "Hospitality", 12: "Entertainment", 13: "Wakeup", 14: "Dusk", 15: "Sleep", 16: "Custom1", 17: "Custom2", 18: "Custom3", 19: "Custom4", 20: "Breath", 21: "Jump"}),
        MapConv("power_on_state", "select", mi="2.p.9", map={0: "Default", 1: "ON", 2: "OFF"}),  # config
        BaseConv("flex_switch", "switch", mi="2.p.12"),  # uint8, config
        BoolConv("night_light", "switch", mi="2.p.13", entity=ENTITY_CONFIG),  # config
        BoolConv("save_state", "switch", mi="5.p.1", entity=ENTITY_CONFIG),  # config
        MapConv("dimming", "select", mi="5.p.2", map={0: "Gradient", 1: "Immediately"}, entity=ENTITY_CONFIG),  # config
    ]
}, {
    10729: [None, "Mesh Light", "jymc.light.falmp"],
    12066: [None, "Mesh Light", "ftd.light.ftdlmp"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", mink=3000, maxk=6500),
        BoolConv("flex_switch", "switch", mi="2.p.4"),  # config
        MapConv("mode", "select", mi="2.p.5", map={0: "Warmth", 1: "TV", 2: "Reading", 3: "Night", 4: "Hospitality", 5: "Leisure", 6: "Office", 255: "Normal"}),
    ],
}, {
    # https://home.miot-spec.com/s/ftd.light.dsplmp
    13233: [None, "Mesh Light", "ftd.light.dsplmp"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", mink=3000, maxk=6500),
        MapConv("mode", "select", mi="2.p.5", map={0: "warmth", 1: "TV", 2: "reading", 3: "night", 4: "hospitality", 5: "leisure", 6: "office", 7: "sleep", 8: "wakeup", 255: "normal"}),
    ],
}, {
    15745: ["Yeelight", "Mesh Downlight Z1", "YCCSLI001", "yeelink.light.ml10"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", mink=2700, maxk=6000),
        MapConv("mode", "select", mi="2.p.7", map={0: "WY", 4: "Lighting", 5: "Night Light", 7: "Warmth", 8: "TV", 9: "Reading", 10: "Computer", 11: "Hospitality", 12: "Entertainment", 13: "Wake Up", 14: "Dusk", 15: "Sleep", 16: "Mode-1", 17: "Mode-2", 18: "Mode-3", 19: "Mode-4"})
    ]
}, {
    12455: ["Yeelight", "K Series Single Wall Switch", "YLYKG-0025/0020", "yeelink.switch.ylsw4"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),
        MapConv("power_on_state", "select", mi="2.p.2", map={1: "On", 2: "Off", 3: "Default"}),  # config
        MapConv("wireless", "select", mi="2.p.3", map={0: "default", 1: "Wireless", 2: "Wireless", 3: "Wireless"}),  # config
        BaseConv("led", "switch", mi="5.p.1"),  # config
        MapConv("mode", "select", mi="8.p.1", map={1: "Top Speed Mode", 2: "Standard Mode"}),  # config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="14.e.1", value=BUTTON_SINGLE),
        ConstConv("action", mi="14.e.2", value=BUTTON_DOUBLE),
        ConstConv("action", mi="14.e.3", value=BUTTON_HOLD),
    ],
}, {
    12456: ["Yeelight", "K Series Double Wall Switch", "YLYKG-0026/0021", "yeelink.switch.ylsw5"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        MapConv("power_on_state_1", "select", mi="2.p.2", map={1: "On", 2: "Off", 3: "Default"}),  # config
        MapConv("power_on_state_2", "select", mi="3.p.2", map={1: "On", 2: "Off", 3: "Default"}),  # config
        MapConv("wireless_1", "select", mi="2.p.3", map={0: "default", 1: "Wireless", 2: "Wireless", 3: "Wireless"}),  # config
        MapConv("wireless_2", "select", mi="3.p.3", map={0: "default", 1: "Wireless", 2: "Wireless", 3: "Wireless"}),  # config
        BaseConv("led", "switch", mi="5.p.1"),  # config
        MapConv("mode", "select", mi="8.p.1", map={1: "Top Speed Mode", 2: "Standard Mode"}),  # config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="14.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="14.e.2", value=BUTTON_1_DOUBLE),
        ConstConv("action", mi="14.e.3", value=BUTTON_1_HOLD),
        ConstConv("action", mi="15.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="15.e.2", value=BUTTON_2_DOUBLE),
        ConstConv("action", mi="15.e.3", value=BUTTON_2_HOLD),
    ],
}, {
    12457: ["Yeelight", "K Series Triple Wall Switch", "YLYKG-0026/0021", "yeelink.switch.ylsw6"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
        MapConv("power_on_state_1", "select", mi="2.p.2", map={1: "On", 2: "Off", 3: "Default"}),  # config
        MapConv("power_on_state_2", "select", mi="3.p.2", map={1: "On", 2: "Off", 3: "Default"}),  # config
        MapConv("power_on_state_3", "select", mi="4.p.2", map={1: "On", 2: "Off", 3: "Default"}),  # config
        MapConv("wireless_1", "select", mi="2.p.3", map={0: "default", 1: "Wireless", 2: "Wireless", 3: "Wireless"}),  # config
        MapConv("wireless_2", "select", mi="3.p.3", map={0: "default", 1: "Wireless", 2: "Wireless", 3: "Wireless"}),  # config
        MapConv("wireless_3", "select", mi="4.p.3", map={0: "default", 1: "Wireless", 2: "Wireless", 3: "Wireless"}),  # config
        BaseConv("led", "switch", mi="5.p.1"),  # config
        MapConv("mode", "select", mi="8.p.1", map={1: "Top Speed Mode", 2: "Standard Mode"}),  # config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="14.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="14.e.2", value=BUTTON_1_DOUBLE),
        ConstConv("action", mi="14.e.3", value=BUTTON_1_HOLD),
        ConstConv("action", mi="15.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="15.e.2", value=BUTTON_2_DOUBLE),
        ConstConv("action", mi="15.e.3", value=BUTTON_2_HOLD),
        ConstConv("action", mi="16.e.1", value=BUTTON_3_SINGLE),
        ConstConv("action", mi="16.e.2", value=BUTTON_3_DOUBLE),
        ConstConv("action", mi="16.e.3", value=BUTTON_3_HOLD),
    ],
}, {
    # LeMesh generic. Pro model has 4 extra scene buttons, but their action replaces normal wireless button so the converter is exactly the same.
    14460: ["LeMesh", "Scene Mesh four key Switch Pro", "lemesh.switch.sw4f01"],
    12458: ["Yeelight", "K Series 4-Key Wall Switch", "YLYKG-0028/0023", "yeelink.switch.ylsw7"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
        BaseConv("channel_4", "switch", mi="12.p.1"),
        MapConv("power_on_state_1", "select", mi="2.p.2", map={1: "On", 2: "Off", 3: "Default"}),  # config
        MapConv("power_on_state_2", "select", mi="3.p.2", map={1: "On", 2: "Off", 3: "Default"}),  # config
        MapConv("power_on_state_3", "select", mi="4.p.2", map={1: "On", 2: "Off", 3: "Default"}),  # config
        MapConv("power_on_state_4", "select", mi="12.p.2", map={1: "On", 2: "Off", 3: "Default"}),  # config
        MapConv("wireless_1", "select", mi="2.p.3", map={0: "default", 1: "Wireless", 2: "Wireless", 3: "Wireless"}),  # config
        MapConv("wireless_2", "select", mi="3.p.3", map={0: "default", 1: "Wireless", 2: "Wireless", 3: "Wireless"}),  # config
        MapConv("wireless_3", "select", mi="4.p.3", map={0: "default", 1: "Wireless", 2: "Wireless", 3: "Wireless"}),  # config
        MapConv("wireless_4", "select", mi="12.p.3", map={0: "default", 1: "Wireless", 2: "Wireless", 3: "Wireless"}),  # config
        BaseConv("led", "switch", mi="5.p.1"),  # config
        MapConv("mode", "select", mi="8.p.1", map={1: "Top Speed Mode", 2: "Standard Mode"}),  # config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="14.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="14.e.2", value=BUTTON_1_DOUBLE),
        ConstConv("action", mi="14.e.3", value=BUTTON_1_HOLD),
        ConstConv("action", mi="15.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="15.e.2", value=BUTTON_2_DOUBLE),
        ConstConv("action", mi="15.e.3", value=BUTTON_2_HOLD),
        ConstConv("action", mi="16.e.1", value=BUTTON_3_SINGLE),
        ConstConv("action", mi="16.e.2", value=BUTTON_3_DOUBLE),
        ConstConv("action", mi="16.e.3", value=BUTTON_3_HOLD),
        ConstConv("action", mi="17.e.1", value=BUTTON_4_SINGLE),
        ConstConv("action", mi="17.e.2", value=BUTTON_4_DOUBLE),
        ConstConv("action", mi="17.e.3", value=BUTTON_4_HOLD),
    ],
}, {
    1945: ["Xiaomi", "Mesh Wall Switch", "DHKG01ZM", "zimi.switch.dhkg01"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),
        BaseConv("led", "switch", mi="10.p.1"),  # config
        BoolConv("wireless", "switch", mi="2.p.2"),  # config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="8.e.1", value=BUTTON_SINGLE),
    ],
}, {
    2007: ["LeMesh", "Mesh Switch Controller", "lemesh.switch.sw0a01"],
    3150: ["XinGuang", "Mesh Switch", "wainft.switch.sw0a01"],
    3169: ["LeMesh", "Mesh Switch Controller", "lemesh.switch.sw0a02"],
    3170: ["LeMesh", "Mesh Switch Controller", "lemesh.switch.sw0a04"],
    4252: [None, "Mesh Switch", "dwdz.switch.sw0a01"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),
    ],
}, {
    8194: ["LeMesh", "Mesh Switch", "lemesh.switch.sw4a02"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
        BaseConv("channel_4", "switch", mi="12.p.1"),
    ],
}, {
    2258: ["PTX", "Mesh Single Wall Switch", "PTX-SK1M", "090615.switch.mesw1"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),
        BoolConv("led", "switch", mi="8.p.1"),  # config
        BoolConv("wireless", "switch", mi="8.p.2"),
    ],
}, {
    # Mesh Switches
    1946: ["Xiaomi", "Mesh Double Wall Switch", "DHKG02ZM", "zimi.switch.dhkg02"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("led", "switch", mi="10.p.1"),  # config
        BoolConv("wireless_1", "switch", mi="2.p.2"),  # config
        BoolConv("wireless_2", "switch", mi="3.p.2"),  # config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="8.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="9.e.1", value=BUTTON_2_SINGLE),
    ],
}, {
    2257: ["PTX", "Mesh Double Wall Switch", "PTX-SK2M", "090615.switch.mesw2"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BoolConv("led", "switch", mi="8.p.1"),  # config
        BoolConv("wireless_1", "switch", mi="8.p.2"),  # config
        BoolConv("wireless_2", "switch", mi="8.p.3"),  # config
    ],
}, {
    # https://www.ixbt.com/live/chome/umnaya-rozetka-xiaomi-zncz01zm-s-energomonitoringom-i-bluetooth-mesh-integraciya-v-home-assistant.html
    3083: ["Xiaomi", "Electrical Outlet", "ZNCZ01ZM", "zimi.plug.zncz01"],
    "spec": [
        BaseConv("outlet", "switch", mi="2.p.1"),
        MathConv("power", "sensor", mi="3.p.1", multiply=0.01),
        BaseConv("led", "switch", mi="4.p.1"),  # config
        BaseConv("power_protect", "switch", mi="7.p.1", entity=ENTITY_CONFIG),
        MathConv("power_value", "number", mi="7.p.2", multiply=0.01, min=0, max=163840000, entity=ENTITY_CONFIG),
    ],
}, {
    2093: ["PTX", "Mesh Triple Wall Switch", "PTX-TK3/M", "090615.switch.mesw3"],
    3878: ["PTX", "Mesh Triple Wall Switch", "PTX-SK3M", "090615.switch.mets3"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
        BoolConv("led", "switch", mi="8.p.1"),  # config
        BoolConv("wireless_1", "switch", mi="8.p.2"),  # config
        BoolConv("wireless_2", "switch", mi="8.p.3"),  # config
        BoolConv("wireless_3", "switch", mi="8.p.4"),  # config
    ],
}, {
    5937: ["Xiaomi", "Mesh Triple Wall Switch", "DHKG05", "zimi.switch.dhkg05"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
        BaseConv("led", "switch", mi="10.p.1"),  # config
        BoolConv("wireless_1", "switch", mi="2.p.2"),  # config
        BoolConv("wireless_2", "switch", mi="3.p.2"),  # config
        BoolConv("wireless_3", "switch", mi="4.p.2"),  # config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="5.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="6.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="7.e.1", value=BUTTON_3_SINGLE),
        BaseConv("anti_flick", "switch", mi="9.p.1"),
    ],
}, {
    8255: ["ZNSN", "Mesh Wall Switch ML3", "znsn.switch.zm3d"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
    ],
}, {
    12054: ["ZNSN", "Mesh Single Wall Switch", "znsn.switch.zg1m"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),
        MapConv("wireless", "select", mi="2.p.2", map={0: "Normal", 1: "Wireless", 2: "Atom", 3: "Scene"}),  # config
        MapConv("power_on_state", "select", mi="2.p.3", map={0: "Default", 1: "Off", 2: "On"}),  # config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="6.e.2", value=BUTTON_SINGLE),
    ],
}, {
    12055: ["ZNSN", "Mesh Double Wall Switch", "znsn.switch.zg2m"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        MapConv("wireless_1", "select", mi="2.p.2", map={0: "Normal", 1: "Wireless", 2: "Atom", 3: "Scene"}),  # config
        MapConv("wireless_2", "select", mi="3.p.2", map={0: "Normal", 1: "Wireless", 2: "Atom", 3: "Scene"}),  # config
        MapConv("power_on_state_1", "select", mi="2.p.3", map={0: "Default", 1: "Off", 2: "On"}),  # config
        MapConv("power_on_state_2", "select", mi="3.p.3", map={0: "Default", 1: "Off", 2: "On"}),  # config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="6.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="6.e.3", value=BUTTON_2_SINGLE),
    ],
}, {
    12058: ["ZNSN", "Mesh Triple Wall Switch", "znsn.switch.zg3m"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
        MapConv("wireless_1", "select", mi="2.p.2", map={0: "Normal", 1: "Wireless", 2: "Atom", 3: "Scene"}),  # config
        MapConv("wireless_2", "select", mi="3.p.2", map={0: "Normal", 1: "Wireless", 2: "Atom", 3: "Scene"}),  # config
        MapConv("wireless_3", "select", mi="4.p.2", map={0: "Normal", 1: "Wireless", 2: "Atom", 3: "Scene"}),  # config
        MapConv("power_on_state_1", "select", mi="2.p.3", map={0: "Default", 1: "Off", 2: "On"}),  # config
        MapConv("power_on_state_2", "select", mi="3.p.3", map={0: "Default", 1: "Off", 2: "On"}),  # config
        MapConv("power_on_state_3", "select", mi="4.p.3", map={0: "Default", 1: "Off", 2: "On"}),  # config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="6.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="6.e.2", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="6.e.3", value=BUTTON_3_SINGLE),
    ],
}, {
    12059: ["ZNSN", "Mesh Four-Key Wall Switch", "znsn.switch.zg4m"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
        BaseConv("channel_4", "switch", mi="5.p.1"),
        MapConv("wireless_1", "select", mi="2.p.2", map={0: "Normal", 1: "Wireless", 2: "Atom", 3: "Scene"}),  # config
        MapConv("wireless_2", "select", mi="3.p.2", map={0: "Normal", 1: "Wireless", 2: "Atom", 3: "Scene"}),  # config
        MapConv("wireless_3", "select", mi="4.p.2", map={0: "Normal", 1: "Wireless", 2: "Atom", 3: "Scene"}),  # config
        MapConv("wireless_4", "select", mi="5.p.2", map={0: "Normal", 1: "Wireless", 2: "Atom", 3: "Scene"}),  # config
        MapConv("power_on_state_1", "select", mi="2.p.3", map={0: "Default", 1: "Off", 2: "On"}),  # config
        MapConv("power_on_state_2", "select", mi="3.p.3", map={0: "Default", 1: "Off", 2: "On"}),  # config
        MapConv("power_on_state_3", "select", mi="4.p.3", map={0: "Default", 1: "Off", 2: "On"}),  # config
        MapConv("power_on_state_4", "select", mi="5.p.3", map={0: "Default", 1: "Off", 2: "On"}),  # config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="6.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="6.e.2", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="6.e.3", value=BUTTON_3_SINGLE),
        ConstConv("action", mi="6.e.4", value=BUTTON_4_SINGLE),
    ],
}, {
    2715: ["Xiaomi", "Mesh Single Wall Switch", "ZNKG01HL", "isa.switch.kg01hl"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),
        MathConv("humidity", "sensor", mi="6.p.1", round=2),
        MathConv("temperature", "sensor", mi="6.p.7", round=2),
        BoolConv("wireless", "switch", mi="2.p.2"),  # config
        BaseConv("child_lock", "switch", mi="11.p.1"),  # config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="16.e.1", value=BUTTON_SINGLE),
    ]
}, {
    2716: ["Xiaomi", "Mesh Double Wall Switch", "ZNKG02HL", "isa.switch.kg02hl"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        MathConv("humidity", "sensor", mi="6.p.1", round=2),
        MathConv("temperature", "sensor", mi="6.p.7", round=2),
        BoolConv("wireless_1", "switch", mi="2.p.2"),  # config
        BoolConv("wireless_2", "switch", mi="3.p.2"),  # config
        BaseConv("child_lock", "switch", mi="11.p.1"),  # config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="16.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="18.e.1", value=BUTTON_2_SINGLE),
    ]
}, {
    2717: ["Xiaomi", "Mesh Triple Wall Switch", "ZNKG03HL", "ISA-KG03HL", "isa.switch.kg03hl"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
        MathConv("humidity", "sensor", mi="6.p.1", round=2),
        MathConv("temperature", "sensor", mi="6.p.7", round=2),
        BoolConv("wireless_1", "switch", mi="2.p.2"),  # config
        BoolConv("wireless_2", "switch", mi="3.p.2"),  # config
        BoolConv("wireless_3", "switch", mi="4.p.2"),  # config
        BaseConv("child_lock", "switch", mi="11.p.1"),  # config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="16.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="17.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="18.e.1", value=BUTTON_3_SINGLE),
    ],
}, {
    6266: ["Gosund", "Mesh Triple Wall Switch S6AM", "cuco.switch.s6amts"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
        MapConv("wireless_1", "select", mi="6.p.1", map={0: "close", 1: "open-close", 2: "open-open"}),  # config
        MapConv("wireless_2", "select", mi="6.p.2", map={0: "close", 1: "open-close", 2: "open-open"}),  # config
        MapConv("wireless_3", "select", mi="6.p.3", map={0: "close", 1: "open-close", 2: "open-open"}),  # config
        BaseConv("led", "switch", mi="8.p.1"),  # bool, config
        BaseConv("mode", "switch", mi="8.p.2"),  # bool, config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="9.e.2", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="9.e.3", value=BUTTON_1_DOUBLE),
        ConstConv("action", mi="9.e.5", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="9.e.6", value=BUTTON_2_DOUBLE),
        ConstConv("action", mi="9.e.8", value=BUTTON_3_SINGLE),
        ConstConv("action", mi="9.e.9", value=BUTTON_3_DOUBLE),
    ]
}, {
    6267: ["Gosund", "Mesh double Wall Switch S5AM", "cuco.switch.s5amts"],
    "spec": [
        BaseConv("left_switch", "switch", mi="2.p.1"),
        BaseConv("right_switch", "switch", mi="3.p.1"),
        MapConv("wireless_1", "select", mi="6.p.1", map={0: "close", 1: "open-close", 2: "open-open"}),  # config
        MapConv("wireless_2", "select", mi="6.p.2", map={0: "close", 1: "open-close", 2: "open-open"}),  # config
        BaseConv("led", "switch", mi="8.p.1"),  # bool, config
        BaseConv("mode", "switch", mi="8.p.2"),  # bool, config
    ]
}, {
    4160: ["Xiaomi", "Mosquito Repeller 2", "WX10ZM", "zimi.mosq.v2"],
    # "support": 5,  # @AlexxIT need some tests
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),  # bool
        BaseConv("battery", "sensor", mi="3.p.1"),  # percentage 0-100
        BaseConv("supply", "sensor", mi="4.p.1"),  # percentage 0-100
        MapConv("led", "switch", mi="9.p.1", map={False: True, True: False}),  # bool, config
        MapConv("power_mode", "select", mi="2.p.2", map={0: "auto", 1: "battery", 2: "usb"}, entity=ENTITY_CONFIG)
    ],
    "ttl": "1440m"  # https://github.com/AlexxIT/XiaomiGateway3/issues/804
}, {
    4737: ["Yeelight", "Charging Table Lamp", "MJTD04YL", "yeelink.light.lamp21"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3"),
        BaseConv("battery", "sensor", mi="4.p.1"),
        MapConv("battery_charging", "binary_sensor", mi="4.p.2", map={1: True, 2: False, 3: False}),  # diagnostic
    ],
    "ttl": "7d",
}, {
    4736: ["Yeelight", "Mesh Night Light", "MJYD05YL", "yeelink.light.nl2"],
    "spec": [
        BaseConv("switch", "light", mi="2.p.1"),  # bool
        BoolConv("light", "binary_sensor", mi="3.p.1")  # uint8 0-Dark 1-Bright
    ],
}, {
    4896: ["Xiaomi", "Mesh Power Strip 2", "XMZNCXB01QM", "qmi.plug.psv3"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),  # bool
        BaseConv("mode", "switch", mi="2.p.2"),  # int8
        MathConv("chip_temperature", "sensor", mi="2.p.3", round=2),  # float, diagnostic
        MathConv("energy", "sensor", mi="3.p.1", multiply=0.1, round=2),
        MathConv("power", "sensor", mi="3.p.2", round=2),  # float
        MathConv("voltage", "sensor", mi="3.p.3", multiply=0.001, round=2),  # float
        MathConv("current", "sensor", mi="3.p.4", multiply=0.001, round=2),  # float
    ]
}, {
    3129: ["Xiaomi", "Curtain Motor", "MJSGCLBL01LM", "lumi.curtain.hmcn02"],
    "spec": [
        MapConv("motor", "cover", mi="2.p.1", map={0: "stop", 1: "open", 2: "close"}),
        BaseConv("target_position", mi="2.p.2"),
        CurtainPosConv("position", mi="2.p.6"),
        MapConv("run_state", mi="2.p.3", map={0: "stop", 1: "opening", 2: "closing"}),
        BaseConv("battery", "sensor", mi="5.p.1"),  # percent
        BoolConv("light", "binary_sensor", mi="3.p.11"),
        BoolConv("motor_reverse", "switch", mi="2.p.5"),  # uint8, config
        MapConv("battery_charging", "binary_sensor", mi="5.p.2", map={1: True, 2: False, 3: False}),  # diagnostic
        BaseConv("battery_temp_warning", mi="3.p.16"),
    ],
}, {
    3789: ["PTX", "Mesh Double Wall Switch", "090615.switch.meshk2"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
    ],
}, {
    3788: ["PTX", "Mesh Triple Wall Switch", "090615.switch.meshk3"],
    # https://github.com/AlexxIT/XiaomiGateway3/issues/993
    11356: ["PTX", "Mesh Triple Wall Switch", "090615.switch.aksk3"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
    ],
}, {
    11333: ["PTX", "Mesh Single Wall Switch", "090615.switch.aksk1"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),
        BoolConv("wireless", "switch", mi="2.p.2"),  # config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="8.e.1", value=BUTTON_SINGLE),
    ],
}, {
    11332: ["PTX", "Mesh Double Wall Switch", "090615.switch.aksk2"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BoolConv("wireless", "switch", mi="2.p.2"),  # config
        BoolConv("wireless", "switch", mi="3.p.2"),  # config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="8.e.1", value=BUTTON_SINGLE),
        ConstConv("action", mi="8.e.2", value=BUTTON_DOUBLE),
    ],
}, {
    12471: ["PTX", "Mesh Double Wall Switch (no N)", "090615.switch.aidh2"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BoolConv("wireless", "switch", mi="2.p.2"),  # config
        BoolConv("wireless", "switch", mi="3.p.2"),  # config
        BoolConv("led", "switch", mi="9.p.1"),  # config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="6.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="7.e.1", value=BUTTON_2_SINGLE),
    ],
}, {
    12470: ["PTX", "Mesh Single Wall Switch (no N)", "090615.switch.aidh1"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),
        BoolConv("wireless", "switch", mi="2.p.2"),  # config
        BoolConv("led", "switch", mi="9.p.1"),  # config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="6.e.1", value=BUTTON_SINGLE),
    ],
}, {
    6379: ["Xiaomi", "Mesh Wall Switch (with N)", "XMQBKG01LM", "lumi.switch.acn016"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),
        MathConv("power", "sensor", mi="5.p.6", round=1),
        BaseConv("led", "switch", mi="7.p.1"),  # config
        BoolConv("wireless", "switch", mi="2.p.2"),  # config
        MapConv("device_fault", mi="2.p.3", map={0: "nofaults", 1: "overtemperature", 2: "overload", 3: "overtemperature-overload"}),
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="6.e.1", value=BUTTON_SINGLE),
    ],
}, {
    6380: ["Xiaomi", "Mesh Double Wall Switch (with N)", "XMQBKG02LM", "lumi.switch.acn017"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        MathConv("power", "sensor", mi="4.p.6", round=1),
        BoolConv("wireless_1", "switch", mi="2.p.2"),  # config
        BoolConv("wireless_2", "switch", mi="3.p.2"),  # config
        BaseConv("led", "switch", mi="5.p.1"),  # config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="6.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="7.e.1", value=BUTTON_2_SINGLE),
        MapConv("device_fault_1", mi="2.p.3", map={0: "nofaults", 1: "overtemperature", 2: "overload", 3: "overtemperature-overload"}),
        MapConv("device_fault_2", mi="3.p.3", map={0: "nofaults", 1: "overtemperature", 2: "overload", 3: "overtemperature-overload"}),
    ],
}, {
    6381: ["Xiaomi", "Mesh Triple Wall Switch (with N)", "XMQBKG03LM", "lumi.switch.acn018"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
        MathConv("power", "sensor", mi="5.p.6", round=1),
        BoolConv("wireless_1", "switch", mi="2.p.2"),  # config
        BoolConv("wireless_2", "switch", mi="3.p.2"),  # config
        BoolConv("wireless_3", "switch", mi="4.p.2"),  # config
        BaseConv("led", "switch", mi="9.p.1"),  # config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="6.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="7.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="8.e.1", value=BUTTON_3_SINGLE),
        MapConv("device_fault_1", mi="2.p.3", map={0: "nofaults", 1: "overtemperature", 2: "overload", 3: "overtemperature-overload"}),
        MapConv("device_fault_2", mi="3.p.3", map={0: "nofaults", 1: "overtemperature", 2: "overload", 3: "overtemperature-overload"}),
        MapConv("device_fault_3", mi="4.p.3", map={0: "nofaults", 1: "overtemperature", 2: "overload", 3: "overtemperature-overload"}),
    ],
}, {
    5195: ["YKGC", "LS Smart Curtain Motor", "LSCL", "lonsam.curtain.lscl"],
    "spec": [
        MapConv("motor", "cover", mi="2.p.1", map={0: "stop", 1: "open", 2: "close"}),
        BaseConv("target_position", mi="2.p.6"),
        CurtainPosConv("position", mi="2.p.2"),
        BaseConv("motor_reverse", "switch", mi="2.p.5"),  # config
        BoolConv("on", "switch", mi="2.p.9"),  # ???
    ],
}, {
    10356: ["ZiQing", "IZQ Presence Sensor Lite", "IZQ-24", "izq.sensor_occupy.24"],
    "spec": [
        BoolConv("occupancy", "binary_sensor", mi="2.p.1"),
        MathConv("no_one_determine_time", "number", mi="2.p.2", min=0, max=10000),
        MathConv("has_someone_duration", "sensor", mi="2.p.3"),
        MathConv("idle_time", "sensor", mi="2.p.4", multiply=60),  # diagnostic
        MathConv("illuminance", "sensor", mi="2.p.5"),
        MathConv("distance", "sensor", mi="2.p.6", multiply=0.01),
        BaseConv("led", "switch", mi="3.p.1"),  # config
        BaseConv("pir", "switch", mi="3.p.3"),
        MathConv("detect_range", "number", mi="3.p.2", min=0, max=8, step=0.1),
        MathConv("enterin_confirm_time", "number", mi="3.p.5", min=0, max=60),
        MapConv("occupancy_status", "sensor", mi="2.p.1", map={0: "NoOne", 1: "EnterIn", 2: "SmallMove", 3: "MicroMove", 4: "Approaching", 5: "MoveAway"}),
    ],
}, {
    10441: ["Linptech", "Presence Sensor ES1", "ES1ZB", "linp.sensor_occupy.hb01"],
    "spec": [
        # main sensors
        BoolConv("occupancy", "binary_sensor", mi="2.p.1"),
        MathConv("distance", "sensor", mi="3.p.3"),
        BaseConv("illuminance", "sensor", mi="2.p.5"),
        MapConv("action", "sensor", mi="3.e.1.p.1", map={0: "stop", 1: "approach", 2: "away"}),
        # other sensors
        MathConv("occupancy_duration", "sensor", mi="2.p.3", entity={"category": "diagnostic", "enabled": False, "units": UNIT_MINUTES}),
        MathConv("not_occupancy_duration", "sensor", mi="2.p.4", entity={"category": "diagnostic", "enabled": False, "units": UNIT_MINUTES}),
        # occupancy settings
        MathConv("occupancy_timeout", "number", mi="2.p.2", min=3, max=10000, entity={"category": "config", "enabled": False, "units": UNIT_SECONDS}),
        InductionRange("induction_range", "text", mi="3.p.2", entity=ENTITY_CONFIG),
        MathConv("approach_distance", "number", mi="3.p.4", min=1, max=5, entity={"category": "config", "units": UNIT_METERS}),
        BaseConv("led", "switch", mi="4.p.1"),  # bool, config
    ],
}, {
    13156: ["AInice", "AInice Dual Presence Sensor", "ainice.sensor_occupy.rd"],
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
        BaseConv("switch", "switch", mi="2.p.1"),  # bool
        BoolConv("led", "switch", mi="5.p.1"),  # uint8, config
    ],
}, {
    10789: ["Zxgs", "Mesh Two Color Scene Light", "zxgs.light.bdcl01"],
    16108: ["WLG", "Smart Light", "wlg.light.wy0a01"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", mink=2700, maxk=6500),
    ],
}, {
    6084: ["Leishi", "NVC Smart Light Source Module Switch", "leishi.light.wy0a09"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3"),
    ],
}, {
    10920: [None, "Mesh Smart Plug V3", "giot.plug.v3shsm"],
    "spec": [
        BaseConv("plug", "switch", mi="2.p.1"),
        MapConv("power_on_state", "select", mi="2.p.3", map={0: "off", 1: "on", 2: "previous"}),
        # Inching mode
        BoolConv("inching_mode", "switch", mi="2.p.2"),
        MapConv("inching_state", "select", mi="3.p.1", map={False: "off", True: "on"}),
        MathConv("inching_time", "number", mi="3.p.2", multiply=0.5, min=1, max=7200, step=1, round=1),
        MapConv("led", "select", mi="4.p.1", map={0: "follow_switch", 1: "opposite_to_switch", 2: "off", 3: "on"})
    ]
}, {
    # A third party module widely used in small brand wall switches
    6514: [None, "Mesh Single Wall Switch (with N)", "babai.switch.201m"],
    # A third party module widely used in small brand wall switches
    7219: [None, "Mesh Single Wall Switch (no N)", "babai.switch.201ml"],
    "spec": [
        BaseConv("channel", "switch", mi="2.p.1"),
        # Either Default/Wireless or Default/Atom, depending on hardware
        BoolConv("wireless", "switch", mi="2.p.2"),  # config
    ]
}, {
    # A third party module widely used in small brand wall switches
    6528: [None, "Mesh Double Wall Switch (with N)", "babai.switch.202m"],
    # A third party module widely used in small brand wall switches
    7220: [None, "Mesh Double Wall Switch (no N)", "babai.switch.202ml"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        # Either Default/Wireless or Default/Atom, depending on hardware
        BoolConv("wireless_1", "switch", mi="2.p.2"),  # config
        BoolConv("wireless_2", "switch", mi="3.p.2"),  # config
    ]
}, {
    # A third party module widely used in small brand wall switches
    6529: [None, "Mesh Triple Wall Switch (with N)", "babai.switch.203m"],
    # A third party module widely used in small brand wall switches
    7221: [None, "Mesh Triple Wall Switch (no N)", "babai.switch.203ml"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
        # Either Default/Wireless or Default/Atom, depending on hardware
        BoolConv("wireless_1", "switch", mi="2.p.2"),  # config
        BoolConv("wireless_2", "switch", mi="3.p.2"),  # config
        BoolConv("wireless_3", "switch", mi="4.p.2"),  # config
    ]
}, {
    5045: ["Linptech", "Mesh Triple Wall Switch (no N)", "QE1SB-W3(MI)", "linp.switch.q4s3"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
        BoolConv("wireless_1", "switch", mi="2.p.3"),
        BoolConv("wireless_2", "switch", mi="3.p.3"),
        BoolConv("wireless_3", "switch", mi="4.p.3"),
        BaseConv("led", "switch", mi="5.p.1"),
        BaseConv("compatible_mode", "switch", mi="7.p.4", entity=ENTITY_CONFIG),
        BaseConv("action", "sensor"),
        ConstConv("action", mi="7.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="7.e.2", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="7.e.3", value=BUTTON_3_SINGLE),
    ],
}, {
    2428: ["Linptech", "Lingpu Single Wall Switch", "linp.switch.q3s1"],
    5043: ["Linptech", "Lingpu Single Wall Switch", "linp.switch.q4s1"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="7.e.1", value=BUTTON_SINGLE),
        BaseConv("led", "switch", mi="5.p.1"),
    ],
}, {
    2429: ["Linptech", "Lingpu Double Wall Switch", "linp.switch.q3s2"],
    5044: ["Linptech", "Lingpu Double Wall Switch", "linp.switch.q4s2"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BoolConv("wireless_1", "switch", mi="2.p.3"),
        BoolConv("wireless_2", "switch", mi="3.p.3"),
        BaseConv("led", "switch", mi="5.p.1"),
        BaseConv("compatible_mode", "switch", mi="7.p.4"),
        BaseConv("action", "sensor"),
        ConstConv("action", mi="7.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="7.e.2", value=BUTTON_2_SINGLE),
    ],
}, {
    15658: ["Linptech", "Single Wall Switch QT1", "linp.switch.qt1db1"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),
        BoolConv("wireless", "switch", mi="2.p.2"),
        BaseConv("led", "switch", mi="11.p.1"),
        BaseConv("action", "sensor"),
        MapConv("touch", "select", mi="12.p.1", map={0: "Off", 1: "Low", 2:"Medium", 3:"High"}),
        ConstConv("action", mi="3.e.1", value=BUTTON_SINGLE),  
    ],
}, {
    15659: ["Linptech", "Double Wall Switch QT1", "linp.switch.qt1db2"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BoolConv("wireless_1", "switch", mi="2.p.2"),
        BoolConv("wireless_2", "switch", mi="3.p.2"),
        BaseConv("led", "switch", mi="11.p.1"),
        BaseConv("action", "sensor"),
        MapConv("touch", "select", mi="12.p.1", map={0: "Off", 1: "Low", 2:"Medium", 3:"High"}),
        ConstConv("action", mi="4.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="5.e.1", value=BUTTON_2_SINGLE),
    ],
}, {
    15660: ["Linptech", "Triple Wall Switch QT1", "linp.switch.qt1db3"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
        BoolConv("wireless_1", "switch", mi="2.p.2"),
        BoolConv("wireless_2", "switch", mi="3.p.2"),
        BoolConv("wireless_3", "switch", mi="4.p.2"),
        BaseConv("led", "switch", mi="11.p.1"),
        BaseConv("action", "sensor"),
        MapConv("touch", "select", mi="12.p.1", map={0: "Off", 1: "Low", 2:"Medium", 3:"High"}),
        ConstConv("action", mi="5.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="6.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="7.e.1", value=BUTTON_3_SINGLE),
    ],
}, {
    15661: ["Linptech", "Quadruple Wall Switch QT1", "linp.switch.qt1db4"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
        BaseConv("channel_4", "switch", mi="5.p.1"),
        BoolConv("wireless_1", "switch", mi="2.p.2"),
        BoolConv("wireless_2", "switch", mi="3.p.2"),
        BoolConv("wireless_3", "switch", mi="4.p.2"),
        BoolConv("wireless_4", "switch", mi="5.p.2"),
        BaseConv("led", "switch", mi="11.p.1"),
        BaseConv("action", "sensor"),
        MapConv("action", mi="6.e.1.p.1", map={1: BUTTON_1_SINGLE, 2: BUTTON_2_SINGLE, 3: BUTTON_3_SINGLE, 4: BUTTON_4_SINGLE}),
        MapConv("touch", "select", mi="12.p.1", map={0: "Off", 1: "Low", 2:"Medium", 3:"High"}),
    ],
}, {
    2274: ["Linptech", "Lingpu Triple Wall Switch", "linp.switch.q3s3"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="7.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="7.e.2", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="7.e.3", value=BUTTON_3_SINGLE),
        BaseConv("led", "switch", mi="5.p.1"),
    ],
}, {
    1350: ["Chuangmi", "Single Wall Switch K1-A (with N)", "chuangmi.switch.mesh"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),
        MapConv("led", "switch", mi="3.p.3", map={1: False, 2: True}),
    ]
}, {
    1490: ["Chuangmi", "Double Wall Switch K1-B (with N)", "chuangmi.switch.meshb01"],
    "spec": [
        BaseConv("left_switch", "switch", mi="2.p.1"),
        BaseConv("right_switch", "switch", mi="3.p.1"),
        MapConv("led", "switch", mi="4.p.3", map={1: False, 2: True}),
    ]
}, {
    1489: ["Chuangmi", "Triple Wall Switch K1-C (with N)", "chuangmi.switch.meshc01"],
    "spec": [
        BaseConv("left_switch", "switch", mi="2.p.1"),
        BaseConv("middle_switch", "switch", mi="3.p.1"),
        BaseConv("right_switch", "switch", mi="4.p.1"),
        MapConv("led", "switch", mi="5.p.3", map={1: False, 2: True}),
    ]
}, {
    7855: [None, "Mesh Single Wall Switch (no N)", "frfox.switch.bl01"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),
        MapConv("mode", "select", mi="2.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),
        BaseConv("action", "sensor"),
        ConstConv("action", mi="3.e.1", value=BUTTON_SINGLE),
        BaseConv("backlight", "switch", mi="4.p.1"),
        BaseConv("led", "switch", mi="4.p.2"),
    ]
}, {
    7856: [None, "Mesh Double Wall Switch (no N)", "frfox.switch.bl02"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        MapConv("mode_1", "select", mi="2.p.2", map={0: "default", 1: "wireless", 2: "flex", 3: "scene"}),
        MapConv("mode_2", "select", mi="3.p.2", map={0: "default", 1: "wireless", 2: "flex", 3: "scene"}),
        BaseConv("action", "sensor"),
        ConstConv("action", mi="4.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="5.e.1", value=BUTTON_2_SINGLE),
        BaseConv("backlight", "switch", mi="6.p.1"),
        BaseConv("led", "switch", mi="6.p.2"),
    ]
}, {
    9804: ["Yeelight", "Magnetic Track Array Spotlight", "yeelink.light.ml6"],
    9811: ["Yeelight", "Magnetic Track Light Bar", "yeelink.light.ml7"],
    9812: ["Yeelight", "Magnetic Track Spotlight", "yeelink.light.ml8"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", mink=2700, maxk=6500),
        MapConv("power_on_state", "select", mi="2.p.4", map={0: "Off", 1: "On", 2: "Default"}),
        MapConv("mode", "select", mi="2.p.5", map={0: "Dummy", 1: "Lighting", 2: "Night Light", 3: "TV", 4: "Reading", 5: "Hospitality", 6: "Warmth"}),
        MathConv("light_off_gradient_time", "number", mi="2.p.7", multiply=0.5, min=0, max=10),
        MathConv("light_on_gradient_time", "number", mi="2.p.8", multiply=0.5, min=0, max=10),
    ],
}, {
    11253: ["LianXun", "Switch Four-key Mesh", "lxun.switch.lxswm4"],
    "spec": [
        BaseConv("switch_1", "switch", mi="2.p.1"),
        BaseConv("switch_2", "switch", mi="3.p.1"),
        BaseConv("switch_3", "switch", mi="4.p.1"),
        BaseConv("switch_4", "switch", mi="12.p.1"),
        MapConv("backlight", "select", mi="5.p.1", map={0: "off", 1: "on"}),
        MapConv("backlight_1", "select", mi="9.p.1", map={1: "reverse", 2: "open", 3: "close", 4: "flash"}),
        MapConv("backlight_2", "select", mi="9.p.2", map={1: "reverse", 2: "open", 3: "close", 4: "flash"}),
        MapConv("backlight_3", "select", mi="9.p.3", map={1: "reverse", 2: "open", 3: "close", 4: "flash"}),
        MapConv("backlight_4", "select", mi="9.p.4", map={1: "reverse", 2: "open", 3: "close", 4: "flash"}),
        MapConv("mode_1", "select", mi="10.p.1", map={1: "normal", 2: "scene", 3: "flex"}),
        MapConv("mode_2", "select", mi="10.p.2", map={1: "normal", 2: "scene", 3: "flex"}),
        MapConv("mode_3", "select", mi="10.p.3", map={1: "normal", 2: "scene", 3: "flex"}),
        MapConv("mode_4", "select", mi="10.p.4", map={1: "normal", 2: "scene", 3: "flex"}),
        BaseConv("action", "sensor"),
        ConstConv("action", mi="11.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="11.e.2", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="11.e.3", value=BUTTON_3_SINGLE),
        ConstConv("action", mi="11.e.4", value=BUTTON_4_SINGLE),
        ConstConv("action", mi="11.e.5", value=BUTTON_1_DOUBLE),
        ConstConv("action", mi="11.e.6", value=BUTTON_2_DOUBLE),
        ConstConv("action", mi="11.e.7", value=BUTTON_3_DOUBLE),
        ConstConv("action", mi="11.e.8", value=BUTTON_4_DOUBLE),
        ConstConv("action", mi="11.e.9", value=BUTTON_1_HOLD),
        ConstConv("action", mi="11.e.10", value=BUTTON_2_HOLD),
        ConstConv("action", mi="11.e.11", value=BUTTON_3_HOLD),
        ConstConv("action", mi="11.e.12", value=BUTTON_4_HOLD),
    ]
}, {
    12987: ["LianXun", "Switch 8-key Mesh", "lxun.switch.sw08"],
    "spec": [
        BaseConv("switch_1", "switch", mi="2.p.1"),
        BaseConv("switch_2", "switch", mi="3.p.1"),
        BaseConv("switch_3", "switch", mi="4.p.1"),
        BaseConv("switch_4", "switch", mi="12.p.1"),
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
        BaseConv("action", "sensor"),
        ConstConv("action", mi="11.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="11.e.2", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="11.e.3", value=BUTTON_3_SINGLE),
        ConstConv("action", mi="11.e.4", value=BUTTON_4_SINGLE),
        ConstConv("action", mi="11.e.5", value=BUTTON_1_DOUBLE),
        ConstConv("action", mi="11.e.6", value=BUTTON_2_DOUBLE),
        ConstConv("action", mi="11.e.7", value=BUTTON_3_DOUBLE),
        ConstConv("action", mi="11.e.8", value=BUTTON_4_DOUBLE),
        ConstConv("action", mi="11.e.9", value=BUTTON_1_HOLD),
        ConstConv("action", mi="11.e.10", value=BUTTON_2_HOLD),
        ConstConv("action", mi="11.e.11", value=BUTTON_3_HOLD),
        ConstConv("action", mi="11.e.12", value=BUTTON_4_HOLD),
        ConstConv("action", mi="11.e.13", value="button_5_single"),
        ConstConv("action", mi="11.e.14", value="button_6_single"),
        ConstConv("action", mi="11.e.15", value="button_7_single"),
        ConstConv("action", mi="11.e.16", value="button_8_single"),
        ConstConv("action", mi="11.e.17", value="button_5_double"),
        ConstConv("action", mi="11.e.18", value="button_6_double"),
        ConstConv("action", mi="11.e.19", value="button_7_double"),
        ConstConv("action", mi="11.e.20", value="button_8_double"),
        ConstConv("action", mi="11.e.21", value="button_5_hold"),
        ConstConv("action", mi="11.e.22", value="button_6_hold"),
        ConstConv("action", mi="11.e.23", value="button_7_hold"),
        ConstConv("action", mi="11.e.24", value="button_8_hold"),
    ]
}, {
    7857: [None, "Mesh Triple Wall Switch (no N)", "frfox.switch.bl03"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
        MapConv("mode_1", "select", mi="2.p.2", map={0: "default", 1: "wireless", 2: "flex", 3: "scene"}),
        MapConv("mode_2", "select", mi="3.p.2", map={0: "default", 1: "wireless", 2: "flex", 3: "scene"}),
        MapConv("mode_3", "select", mi="4.p.2", map={0: "default", 1: "wireless", 2: "flex", 3: "scene"}),
        BaseConv("action", "sensor"),
        ConstConv("action", mi="5.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="6.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="7.e.1", value=BUTTON_3_SINGLE),
        BaseConv("backlight", "switch", mi="8.p.1"),
        BaseConv("led", "switch", mi="8.p.2"),
    ]
}, {
    10939: ["Linptech", "Sliding Window Driver WD1", "WD1", "linp.wopener.wd1lb"],
    "spec": [
        MapConv("motor", "cover", mi="2.p.1", map={0: "stop", 1: "open", 2: "close"}),
        BaseConv("target_position", mi="2.p.3"),
        CurtainPosConv("position", mi="2.p.2"),
        BaseConv("battery", "sensor", mi="3.p.1"),
        BaseConv("security_mode", "switch", mi="4.p.6", entity=ENTITY_CONFIG),
        BaseConv("power_replenishment", "sensor", mi="7.p.1", entity={"category": "diagnostic", "enabled": False, "lazy": True, "units": "mAh"}),
        BaseConv("realtime_current_in", "sensor", mi="7.p.2", entity={"category": "diagnostic", "enabled": False, "class": "current", "units": "mA"}),
    ],
}, {
    10813: ["Yeelink", "Curtain Motor C1", "YCCBCI008", "yeelink.curtain.crc1"],
    "spec": [
        MapConv("motor", "cover", mi="2.p.1", map={0: "stop", 1: "open", 2: "close"}),
        BaseConv("target_position", mi="2.p.2"),
        CurtainPosConv("position", mi="2.p.3"),
        BaseConv("motor_reverse", "switch", mi="2.p.4"),  # config
        MapConv("mode", "select", mi="2.p.5", map={0: "default", 1: "doublmode", 2: "leftmode", 3: "rightmode"}),  # config
    ],
    "ttl": "7d",
}, {
    15069: ["PTX", "Curtain Motor", "090615.curtain.crus6"],
    "spec": [
        MapConv("motor", "cover", mi="2.p.1", map={0: "stop", 1: "open", 2: "close"}),
        BaseConv("target_position", mi="2.p.2"),
        CurtainPosConv("position", mi="2.p.3"),
        MapConv("run_state", mi="2.p.6", map={0: "stop", 1: "opening", 2: "closing"}),
        BaseConv("motor_reverse", "switch", mi="2.p.4"),  # config
        MapConv("mode", "select", mi="2.p.5", map={0: "default", 1: "doublmode", 2: "leftmode", 3: "rightmode"}),  # config
        MapConv("fault", "sensor", mi="2.p.7", map={0: "No faults", 1: "Faults"}, entity=ENTITY_DIAGNOSTIC),
    ],
    "ttl": "7d",
}, {
    4722: ["Xiaomi", "Curtain Motor", "MJZNCL02LM", "lumi.curtain.acn006"],
    "spec": [
        MapConv("motor", "cover", mi="2.p.1", map={0: "stop", 1: "open", 2: "close"}),
        BaseConv("target_position", mi="2.p.2"),
        CurtainPosConv("position", mi="2.p.6"),
        MapConv("run_state", mi="2.p.3", map={0: "stop", 1: "opening", 2: "closing", 3: "busy"}),
        BaseConv("battery", "sensor", mi="5.p.1"),  # percent, diagnostic
        MapConv("battery_charging", "binary_sensor", mi="5.p.2", map={1: True, 2: False, 3: False}),  # diagnostic
        BaseConv("motor_reverse", "switch", mi="2.p.5"),  # config
    ],
}, {
    13804: ["giot", "Curtain Motor", "giot.curtain.v5icm"],
    "spec": [
        MapConv("motor", "cover", mi="2.p.1", map={0: "stop", 1: "open", 2: "close"}),
        BaseConv("target_position", mi="2.p.7"),
        CurtainPosConv("position", mi="2.p.6"),
        BaseConv("battery", "sensor", mi="3.p.1"),  # diagnostic
        BaseConv("motor_reverse", "switch", mi="2.p.8"),  # config
    ],
    "ttl": "7d",
}, {
    11724: ["GranwinIoT", "Mesh Light V5", "giot.light.v5ssm"],
    15504: ["GranwinIoT", "Mesh Light V8", "giot.light.v8ssm"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", mink=2700, maxk=6500),
        MapConv("mode", "select", mi="2.p.4", map={0: "Auto", 1: "Day", 2: "Night", 3: "Warmth", 4: "TV", 5: "Reading", 6: "Computer", 7: "Sleeping Aid", 8: "Wakeup Aid"}),
        BaseConv("flex_switch", "switch", mi="2.p.5"),
        # Converter("ac_status", "sensor", mi="3.p.1"),
        MapConv("power_on_state", "select", mi="3.p.2", map={0: "off", 1: "on"}),
        MapConv("turn_on_state", "select", mi="3.p.3", map={0: "previous", 1: "default"}, entity=ENTITY_CONFIG),
        MathConv("default_brightness", "number", mi="3.p.4", min=1, max=100, entity=ENTITY_CONFIG),
        MathConv("default_temp", "number", mi="3.p.5", min=2700, max=6500, entity=ENTITY_CONFIG),
        MathConv("sleep_aid_minutes", "number", mi="3.p.7", min=1, max=60, entity=ENTITY_CONFIG),
        BaseConv("sleep_aid_use_custom", "switch", mi="3.p.8", entity=ENTITY_CONFIG),
        MathConv("sleep_aid_custom_init_brightness", "number", mi="3.p.9", min=1, max=100, entity=ENTITY_CONFIG),
        MathConv("sleep_aid_custom_init_temp", "number", mi="3.p.10", min=2700, max=6500, entity=ENTITY_CONFIG),
        MathConv("wakeup_minutes", "number", mi="3.p.11", min=1, max=60, entity=ENTITY_CONFIG),
        BaseConv("wakeup_use_custom", "switch", mi="3.p.12", entity=ENTITY_CONFIG),
        MathConv("wakeup_custom_final_brightness", "number", mi="3.p.13", min=1, max=100, entity=ENTITY_CONFIG),
        MathConv("wakeup_custom_final_temp", "number", mi="3.p.14", min=2700, max=6500, entity=ENTITY_CONFIG),
        BaseConv("night_light", "switch", mi="3.p.15", entity=ENTITY_CONFIG),
        MathConv("turn_on_transit_sec", "number", mi="3.p.17", multiply=0.001, min=100, max=30000, step=100, round=1, entity=ENTITY_CONFIG),
        MathConv("turn_off_transit_sec", "number", mi="3.p.18", multiply=0.001, min=100, max=30000, step=100, round=1, entity=ENTITY_CONFIG),
        MathConv("change_transit_sec", "number", mi="3.p.19", multiply=0.001, min=100, max=30000, step=100, round=1, entity=ENTITY_CONFIG),
        MathConv("min_brightness", "number", mi="3.p.23", multiply=0.1, min=1, max=500, step=1, round=1, entity=ENTITY_CONFIG),
        GiotTimePatternConv("night_light_time", "text", mi="3.p.16", entity=ENTITY_CONFIG)
        # Converter("fill_light_detection", "sensor", mi="3.p.20"),
        # Converter("fill_light_switch", "switch", mi="3.p.21"),
        # MathConv("min_bri_factory", "number", mi="3.p.16", min=1, max=500),
    ]
}, {
    3661: ["Opple", "Bare Light Panel", "opple.light.barelp"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", mink=3000, maxk=5700),
        MapConv("mode", "select", mi="2.p.4", map={0: "Reception", 1: "Entertainment", 2: "Cinema", 3: "Night", 4: "Wakeup", 5: "Sleep", 6: "Sunset", 7: "None", 8: "Invert"}),
    ],
}, {
    13586: ["LeMesh", "Mesh Switch Controller V2S", "lemesh.switch.sw0a04"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),  # Tested
        MapConv("power_on_state", "select", mi="2.p.2", map={0: "previous", 1: "on", 2: "off"}),  # config
        BoolConv("flex_switch", "switch", mi="3.p.4"),  # uint8, config
    ],
}, {
    # run_state attribute is not available according to the spec
    6461: ["PTX", "Curtain Motor", "090615.curtain.s2mesh"],
    "spec": [
        MapConv("motor", "cover", mi="2.p.1", map={0: "stop", 1: "open", 2: "close"}),
        BaseConv("target_position", mi="2.p.2"),
        CurtainPosConv("position", mi="2.p.3"),
        BaseConv("motor_reverse", "switch", mi="2.p.4"),  # config
    ],
}, {
    13140: ["GranwinIoT", "Three-Button Switch (Mesh) V5", "giot.switch.v53ksm"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
        BaseConv("switch_status_1", "switch", mi="11.p.1"),
        BaseConv("switch_status_2", "switch", mi="12.p.1"),
        BaseConv("switch_status_3", "switch", mi="13.p.1"),
        MapConv("mode_1", "select", mi="2.p.2", map={0: "normal_switch", 1: "wireless_switch", 2: "smart_switch", 3: "toggle_switch"}),  # config
        MapConv("mode_2", "select", mi="3.p.2", map={0: "normal_switch", 1: "wireless_switch", 2: "smart_switch", 3: "toggle_switch"}),  # config
        MapConv("mode_3", "select", mi="4.p.2", map={0: "normal_switch", 1: "wireless_switch", 2: "smart_switch", 3: "toggle_switch"}),  # config
    ]
}, {
    # https://home.miot-spec.com/spec/giot.switch.v54ksm
    13141: ["GranwinIoT", "Four-Button Switch (Mesh) V5", "giot.switch.v54ksm"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
        BaseConv("channel_4", "switch", mi="5.p.1"),
        BaseConv("action", "sensor"),
        ConstConv("action", mi="11.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="12.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="13.e.1", value=BUTTON_3_SINGLE),
        ConstConv("action", mi="14.e.1", value=BUTTON_4_SINGLE),
        MapConv("mode_1", "select", mi="2.p.2", map={0: "Normal", 1: "Wireless", 2: "Flex", 3: "Toggle"}),  # config
        MapConv("mode_2", "select", mi="3.p.2", map={0: "Normal", 1: "Wireless", 2: "Flex", 3: "Toggle"}),  # config
        MapConv("mode_3", "select", mi="4.p.2", map={0: "Normal", 1: "Wireless", 2: "Flex", 3: "Toggle"}),  # config
        MapConv("mode_4", "select", mi="5.p.2", map={0: "Normal", 1: "Wireless", 2: "Flex", 3: "Toggle"}),  # config
        MapConv("led_mode_normal", "select", mi="6.p.1", map={0: "Follow Switch State", 1: "Opposite To Switch State", 2: "Normally Off", 3: "Normally On"}, entity=ENTITY_CONFIG),  # config
        MapConv("led_mode_special", "select", mi="6.p.2", map={0: "Follow Switch State", 1: "Opposite To Switch State", 2: "Normally Off", 3: "Normally On"}, entity=ENTITY_CONFIG),  # config
        BaseConv("backlight", "switch", mi="6.p.3"),
    ]
}, {
    9609: ["Bean", "Mesh Single Wall Switch (L)", "bean.switch.bl01"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),
        MapConv("mode", "select", mi="2.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),  # config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="3.e.1", value=BUTTON_SINGLE),
    ],
}, {
    9610: ["Bean", "Mesh Double Wall Switch (L)", "bean.switch.bl02"],
    "spec": [
        BaseConv("switch_1", "switch", mi="2.p.1"),
        BaseConv("switch_2", "switch", mi="3.p.1"),
        MapConv("mode_1", "select", mi="2.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),  # config
        MapConv("mode_2", "select", mi="3.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),  # config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="4.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="5.e.1", value=BUTTON_2_SINGLE),
    ],
}, {
    9611: ["Bean", "Mesh Triple Wall Switch (L)", "bean.switch.bl03"],
    "spec": [
        BaseConv("switch_1", "switch", mi="2.p.1"),
        BaseConv("switch_2", "switch", mi="3.p.1"),
        BaseConv("switch_3", "switch", mi="4.p.1"),
        MapConv("mode_1", "select", mi="2.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),
        MapConv("mode_2", "select", mi="3.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),
        MapConv("mode_3", "select", mi="4.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),
        BaseConv("action", "sensor"),
        ConstConv("action", mi="5.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="6.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="7.e.1", value=BUTTON_3_SINGLE),
    ],
}, {
    9612: ["Bean", "Mesh Single Wall Switch (LN)", "bean.switch.bl01"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),
        MapConv("mode", "select", mi="2.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),  # config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="3.e.1", value=BUTTON_SINGLE),
    ]
}, {
    9613: ["Bean", "Mesh Double Wall Switch (LN)", "bean.switch.bl02"],
    "spec": [
        BaseConv("switch_1", "switch", mi="2.p.1"),
        BaseConv("switch_2", "switch", mi="3.p.1"),
        MapConv("mode_1", "select", mi="2.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),  # config
        MapConv("mode_2", "select", mi="3.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),  # config
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="4.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="5.e.1", value=BUTTON_2_SINGLE),
    ]
}, {
    9614: ["Bean", "Mesh Triple Wall Switch (LN)", "bean.switch.bl03"],
    "spec": [
        BaseConv("switch_1", "switch", mi="2.p.1"),
        BaseConv("switch_2", "switch", mi="3.p.1"),
        BaseConv("switch_3", "switch", mi="4.p.1"),
        MapConv("mode_1", "select", mi="2.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),
        MapConv("mode_2", "select", mi="3.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),
        MapConv("mode_3", "select", mi="4.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),
        BaseConv("action", "sensor"),
        ConstConv("action", mi="5.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="6.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="7.e.1", value=BUTTON_3_SINGLE),
    ]
}, {
    10147: ["Unkown", "Mesh Four-Key Wall Switch", "bean.switch.bln04"],
    "spec": [
        BaseConv("switch_1", "switch", mi="2.p.1"),
        BaseConv("switch_2", "switch", mi="3.p.1"),
        BaseConv("switch_3", "switch", mi="4.p.1"),
        BaseConv("switch_4", "switch", mi="5.p.1"),
        MapConv("mode_1", "select", mi="2.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),
        MapConv("mode_2", "select", mi="3.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),
        MapConv("mode_3", "select", mi="4.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),
        MapConv("mode_4", "select", mi="5.p.2", map={0: "off", 1: "wireless", 2: "flex", 3: "scene"}),
        BaseConv("action", "sensor"),
        ConstConv("action", mi="6.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="7.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="8.e.1", value=BUTTON_3_SINGLE),
        ConstConv("action", mi="9.e.1", value=BUTTON_4_SINGLE),
    ],
}, {
    14431: ["Xiaomi", "Xiaomi Smart Wall Switch Pro (1 Gang)", "XMQBKG04LM", "xiaomi.switch.pro1"],
    # White variant
    17767: ["Xiaomi", "Xiaomi Smart Wall Switch Pro (1 Gang)", "XMQBKG04LM", "xiaomi.switch.wpro1"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="3.e.1", value=BUTTON_SINGLE),
        ConstConv("action", mi="3.e.2", value=BUTTON_DOUBLE),
        ConstConv("action", mi="3.e.3", value=BUTTON_HOLD),
        MapConv("fault", "sensor", mi="2.p.3", map={0: "No Faults", 1: "Over Temperature", 2: "Overload", 3: "Overload And Overheat"}),
        MathConv("power", "sensor", mi="4.p.2", round=1),
        BaseConv("led", "switch", mi="5.p.1"),
    ],
}, {
    14432: ["Xiaomi", "Xiaomi Smart Wall Switch Pro (2 Gang)", "XMQBKG05LM", "xiaomi.switch.pro2"],
    # White variant
    17768: ["Xiaomi", "Xiaomi Smart Wall Switch Pro (2 Gang)", "XMQBKG05LM", "xiaomi.switch.wpro2"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="4.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="4.e.2", value=BUTTON_1_DOUBLE),
        ConstConv("action", mi="4.e.3", value=BUTTON_1_HOLD),
        ConstConv("action", mi="5.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="5.e.2", value=BUTTON_2_DOUBLE),
        ConstConv("action", mi="5.e.3", value=BUTTON_2_HOLD),
        MapConv("fault", "sensor", mi="2.p.3", map={0: "No Faults", 1: "Over Temperature", 2: "Overload", 3: "Overload And Overheat"}),
        MathConv("power", "sensor", mi="6.p.2", round=1),
        BaseConv("led", "switch", mi="7.p.1"),
    ],
}, {
    14433: ["Xiaomi", "Xiaomi Smart Wall Switch Pro (3 Gang)", "XMQBKG06LM", "xiaomi.switch.pro3"],
    # White variant
    17769: ["Xiaomi", "Xiaomi Smart Wall Switch Pro (3 Gang)", "XMQBKG05LM", "xiaomi.switch.wpro3"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
        BaseConv("action", "sensor", entity=ENTITY_DISABLED),
        ConstConv("action", mi="5.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="5.e.2", value=BUTTON_1_DOUBLE),
        ConstConv("action", mi="5.e.3", value=BUTTON_1_HOLD),
        ConstConv("action", mi="6.e.1", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="6.e.2", value=BUTTON_2_DOUBLE),
        ConstConv("action", mi="6.e.3", value=BUTTON_2_HOLD),
        ConstConv("action", mi="7.e.1", value=BUTTON_3_SINGLE),
        ConstConv("action", mi="7.e.2", value=BUTTON_3_DOUBLE),
        ConstConv("action", mi="7.e.3", value=BUTTON_3_HOLD),
        MapConv("fault", "sensor", mi="2.p.3", map={0: "No Faults", 1: "Over Temperature", 2: "Overload", 3: "Overload And Overheat"}),
        MathConv("power", "sensor", mi="8.p.2", round=1),
        BaseConv("led", "switch", mi="9.p.1"),
    ],
}, {
    13521: ["Xiaomi", "Xiaomi Smart Wall Outlet Pro", "XMZNCZ01LM", "xiaomi.plug.mcn001"],
    17885: ["Xiaomi", "Xiaomi Smart Wall Outlet Pro", "XMZNCZ01LM", "xiaomi.plug.mcn003"],
    "spec": [
        BaseConv("outlet", "switch", mi="2.p.1"),
        MapConv("power_on_state", "select", mi="2.p.2", map={0: "default", 1: "off", 2: "on"}),
        MapConv("fault", "sensor", mi="2.p.3", map={0: "No Faults", 1: "Over Temperature", 2: "Overload", 3: "Overload And Overheat"}),
        MathConv("energy", "sensor", mi="3.p.1", round=2, step=0.01),
        MathConv("power", "sensor", mi="3.p.6", round=1),
        BaseConv("power_consumption_accumulation_way", "binary_sensor", mi="3.p.7", entity=ENTITY_DIAGNOSTIC),
        BaseConv("led", "switch", mi="4.p.1"),
        BaseConv("child_lock", "switch", mi="5.p.1"),  # config
    ],
}, {
    7082: ["pmfbj", "Panasonic Ceiling Light", "pmfbj.light.xsx340"],
    6857: ["pmfbj", "Panasonic Ceiling Light", "pmfbj.light.xsx341"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", mink=2700, maxk=6500),
        MapConv("effect", mi="2.p.4", map={0: "Default", 1: "Daily", 2: "Leisure", 3: "Comfortable", 4: "Night", 5: "SY"})
    ]
}, {
    6435: ["PTX", "PTX Smart Quadruple Switch", "090615.switch.sk4k"],
    "spec": [
        BaseConv("switch_1", "switch", mi="2.p.1"),
        BaseConv("switch_2", "switch", mi="3.p.1"),
        BaseConv("switch_3", "switch", mi="4.p.1"),
        BaseConv("switch_4", "switch", mi="5.p.1"),
        MapConv("mode_1", "select", mi="2.p.2", map={0: "Wired And Wireless", 1: "Wireless"}),
        MapConv("mode_2", "select", mi="3.p.2", map={0: "Wired And Wireless", 1: "Wireless"}),
        MapConv("mode_3", "select", mi="4.p.2", map={0: "Wired And Wireless", 1: "Wireless"}),
        MapConv("mode_4", "select", mi="5.p.2", map={0: "Wired And Wireless", 1: "Wireless"}),
        BaseConv("backlight", "switch", mi="8.p.1"),
    ],
}, {
    10944: [None, "Mesh Smart Switch V3", "giot.switch.v3oodm"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),
        MapConv("power_on_state", "select", mi="2.p.3", map={0: "off", 1: "on", 2: "previous"}),
        BoolConv("inching_mode", "switch", mi="2.p.2"),
        MapConv("inching_state", "select", mi="3.p.1", map={False: "off", True: "on"}),
        MathConv("inching_time", "number", mi="3.p.2", multiply=0.5, min=1, max=7200, step=1, round=1),
        MapConv("led", "select", mi="4.p.1", map={0: "follow_switch", 1: "opposite_to_switch", 2: "off", 3: "on"})
    ]
}, {
    15461: [None, "V6 Intelligent On-off Device(Mesh)", "giot.switch.v6oodm"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),
        MapConv("power_on_state", "select", mi="2.p.6", map={0: "OFF", 1: "ON", 2: "Last State"}),
        MapConv("led", "select", mi="4.p.1", map={0: "Follow Switch State", 1: "Opposite To Switch State", 2: "Normally OFF", 3: "Normally ON"}),
        BoolConv("flex_switch", "switch", mi="5.p.1"),
        MapConv("rocker_switch", "select", mi="6.p.1", map={0: "Self-resetting Mode", 1: "Flip Mode", 2: "Sync Mode"}, entity=ENTITY_CONFIG),
        BoolConv("inching_mode", "switch", mi="2.p.5", entity=ENTITY_CONFIG),
        MapConv("inching_state", "select", mi="3.p.1", map={False: "Default OFF", True: "Default ON"}, entity=ENTITY_CONFIG),
        MathConv("inching_time", "number", mi="3.p.2", multiply=0.5, min=1, max=7200, step=1, round=1, entity=ENTITY_CONFIG)
    ]
}, {
    13139: ["GranwinIoT", "Two-Button Switch (Mesh) V5", "giot.switch.v52ksm"],
    "spec": [
        BaseConv("left_switch", "switch", mi="2.p.1"),
        BaseConv("right_switch", "switch", mi="3.p.1"),
        MapConv("left_switch_mode", "select", mi="2.p.2", map={0: "normal_switch", 1: "wireless_switch", 2: "smart_switch", 3: "button_switch"}),
        MapConv("right_switch_mode", "select", mi="3.p.2", map={0: "normal_switch", 1: "wireless_switch", 2: "smart_switch", 3: "button_switch"}),
    ]
}, {
    # https://github.com/AlexxIT/XiaomiGateway3/issues/1063
    10371: ["PTX", "Mesh Multifunction Wireless Switch", "PTX-AK3-QMIMB", "090615.remote.mlsw0a"],
    "spec": [
        BaseConv("action", "sensor"),
        ConstConv("action", mi="2.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="2.e.2", value=BUTTON_2_SINGLE),
        ConstConv("action", mi="2.e.3", value=BUTTON_3_SINGLE),
        ConstConv("action", mi="2.e.4", value=BUTTON_4_SINGLE),
        ConstConv("action", mi="2.e.5", value="button_5_single"),
        ConstConv("action", mi="3.e.1", value="button_6_single"),
        ConstConv("action", mi="3.e.2", value=BUTTON_1_HOLD),
        ConstConv("action", mi="3.e.3", value=BUTTON_2_HOLD),
        ConstConv("action", mi="3.e.4", value=BUTTON_3_HOLD),
        ConstConv("action", mi="3.e.5", value=BUTTON_4_HOLD),
        ConstConv("action", mi="3.e.6", value="button_5_hold"),
        ConstConv("action", mi="3.e.7", value="button_6_hold"),
        BaseConv("battery", "sensor", mi="4.p.1"),
    ],
    "ttl": "25h"
}, {
    12385: [None, "Mesh Ceiling Fan Light", "xingh.light.fsd2"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", mink=2700, maxk=6500),
        MapConv("light_mode", "select", mi="2.p.4", map={0: "Reading", 1: "Office", 2: "Night", 3: "Leisure", 4: "W", 5: "WY", 6: "Night Light", 7: "Y", 8: "None"}),
        BaseConv("fan", "switch", mi="3.p.1"),
        BaseConv("horizontal_swing", "switch", mi="3.p.3"),
        BaseConv("wind_reverse", "switch", mi="3.p.12"),
        BoolConv("natural_wind", "switch", mi="3.p.7"),
        MapConv("fan_level", "select", mi="3.p.2", map={1: "1", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6"}),
    ]
}, {
    14050: ["Scdvb", "Air Conditioner", "scdvb.aircondition.acm"],
    "spec": [
        BaseConv("climate", "climate", mi="2.p.1"),
        MapConv("hvac_mode", mi="2.p.2", map={0: "cool", 1: "heat", 2: "fan_only", 3: "dry"}),
        MapConv("fan_mode", mi="3.p.1", map={0: "auto", 1: "low", 2: "medium", 3: "high"}),
        BaseConv("current_temp", mi="4.p.1"),
        BaseConv("target_temp", mi="2.p.3"),
    ],
}, {
    11971: ["Unknown", "Mesh Light", "shhf.light.slcwb3"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", mink=3000, maxk=6400),
        MapConv("mode", "select", mi="2.p.4", map={0: "None", 1: "Day", 2: "Night", 3: "Warmth", 4: "Reading", 5: "Tv", 6: "Computer"}),
        BoolConv("flex_switch", "switch", mi="2.p.5"),
        MapConv("power_on_state", "select", mi="2.p.6", map={0: "Default", 1: "On", 2: "Off"}),
        BoolConv("wake_up_mode", "switch", mi="2.p.7", entity=ENTITY_CONFIG),
        BoolConv("sleep_aid_mode", "switch", mi="2.p.8", entity=ENTITY_CONFIG),
        MapConv("flow", "select", mi="2.p.9", map={0: "Auto", 1: "Immediately"}, entity=ENTITY_CONFIG),
    ]
}, {
    5741: ["Yeelight", "Mesh Light", "yeelink.light.spot2"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1"),
        BrightnessConv("brightness", mi="2.p.2", max=100),
        ColorTempKelvin("color_temp", mi="2.p.3", mink=2700, maxk=6500),
        MapConv("power_on_state", "select", mi="2.p.4", map={0: "Off", 1: "On", 2: "Default"}),
        MapConv("mode", "select", mi="2.p.5", map={0: "Dummy", 1: "Lighting", 2: "Night Light", 3: "Tv", 4: "Reading", 5: "Hospitality", 6: "Warmth"}),
        BoolConv("flex_switch", "switch", mi="2.p.6"),
        MathConv("light_off_gradient_time", "number", mi="2.p.7", multiply=0.5, min=0, max=10, entity=ENTITY_CONFIG),
        MathConv("light_on_gradient_time", "number", mi="2.p.8", multiply=0.5, min=0, max=10, entity=ENTITY_CONFIG),
    ]
}, {
    5093: [None, "Two Key Mesh Switch", "topwit.switch.rzw02"],
    "spec": [
        BaseConv("switch_1", "switch", mi="2.p.1"),
        BaseConv("switch_2", "switch", mi="3.p.1"),
        MapConv("mode_1", "select", mi="2.p.2", map={0: "Default", 1: "Wireless", 2: "Flex"}),
        MapConv("mode_2", "select", mi="3.p.2", map={0: "Default", 1: "Wireless", 2: "Flex"}),
        BaseConv("action", "sensor"),
        ConstConv("action", mi="4.e.1", value=BUTTON_1_SINGLE),
        ConstConv("action", mi="5.e.1", value=BUTTON_2_SINGLE),
    ]
}, {
    15082: ["Unknown", "Smart Quadruple Switch", "topwit.switch.rzw34"],
    "spec": [
        BaseConv("switch_1", "switch", mi="2.p.1"),
        BaseConv("switch_2", "switch", mi="3.p.1"),
        BaseConv("switch_3", "switch", mi="4.p.1"),
        BaseConv("switch_4", "switch", mi="23.p.1"),
        MapConv("mode_1", "select", mi="2.p.2", map={0: "off", 1: "wireless"}),
        MapConv("mode_2", "select", mi="3.p.2", map={0: "off", 1: "wireless"}),
        MapConv("mode_3", "select", mi="4.p.2", map={0: "off", 1: "wireless"}),
        MapConv("mode_4", "select", mi="23.p.4", map={0: "off", 1: "wireless"}),
        BaseConv("action", "sensor"),
        MapConv("action", mi="5.e.1.p.2", map={1: BUTTON_1_SINGLE, 2: BUTTON_2_SINGLE, 3: BUTTON_3_SINGLE, 4: BUTTON_BOTH_SINGLE}),
        MapConv("action", mi="5.e.2.p.2", map={1: BUTTON_1_DOUBLE, 2: BUTTON_2_DOUBLE, 3: BUTTON_3_DOUBLE, 4: BUTTON_BOTH_DOUBLE}),
        MapConv("action", mi="5.e.3.p.2", map={1: BUTTON_1_HOLD, 2: BUTTON_2_HOLD, 3: BUTTON_3_HOLD, 4: BUTTON_BOTH_HOLD}),
    ]
}, {
    12261: ["Lingju", "Bluetooth Mesh Switch", "linju.switch.sw0a01"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),  # bool
        MapConv("power_on_state", "select", mi="2.p.2", map={0: "default", 1: "on", 2: "off"}),
        BoolConv("led", "switch", mi="3.p.2"),
        MapConv("interactive_switch", "select", mi="3.p.3", map={1: "control", 2: "decontrol"}, entity=ENTITY_CONFIG),
        BoolConv("flex_switch", "switch", mi="3.p.4", entity=ENTITY_CONFIG),
        MapConv("icon_style", "select", mi="3.p.5", map={0: "Lamp-bulb", 1: "Cylindrical-spotlight", 2: "Ceiling-light", 3: "Hanging-lamp", 4: "Lamp-belt", 5: "Small-electric-appliance", 6: "Socket", 7: "Valve", 8: "Electrical-machinery"}, entity=ENTITY_CONFIG),
        BoolConv("pilot_switch", "switch", mi="3.p.6", entity=ENTITY_CONFIG),
    ],
}, {
    17725: ["Unknown", "Intelligent On-off Device(Mesh)", "iot.switch.tdq3"],
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1"),
        BoolConv("fault", "binary_sensor", mi="2.p.3", entity=ENTITY_DISABLED),
        MapConv("power_on_state", "select", mi="2.p.5", map={0: "Default", 1: "Off", 2: "On"}),
        BaseConv("led", "switch", mi="6.p.1"),
        MathConv("double_click_close", "number", mi="7.p.4", min=0, max=1439, entity=ENTITY_DISABLED),
        MathConv("local_timing", "number", mi="7.p.5", min=0, max=4294967295, entity=ENTITY_DISABLED),
        MathConv("jog_mode", "number", mi="7.p.6", min=1, max=4294967295, entity=ENTITY_DISABLED),
        BaseConv("child_lock", "switch", mi="7.p.7", entity=ENTITY_DISABLED),
        MapConv("rocker_switch", "select", mi="7.p.8", map={0: "Self-resetting Mode", 1: "Flip Mode", 2: "Sync Mode"}, entity=ENTITY_DISABLED),
    ]
}, {
    16854: ["ZNSN", "Mesh Six-Key Oled Wall Switch", "znsn.switch.oled6"],
    "spec": [
        BaseConv("channel_1", "switch", mi="2.p.1"),
        BaseConv("channel_2", "switch", mi="3.p.1"),
        BaseConv("channel_3", "switch", mi="4.p.1"),
        BaseConv("channel_4", "switch", mi="5.p.1"),
        BaseConv("channel_5", "switch", mi="13.p.1"),
        BaseConv("channel_6", "switch", mi="14.p.1"),
        MapConv("mode_1", "select", mi="2.p.6", map={0: "Normal", 1: "Linkage", 2: "Atom"}),  # config
        MapConv("mode_2", "select", mi="3.p.4", map={0: "Normal", 1: "Linkage", 2: "Atom"}),  # config
        MapConv("mode_3", "select", mi="4.p.4", map={0: "Normal", 1: "Linkage", 2: "Atom"}),  # config
        MapConv("mode_4", "select", mi="5.p.4", map={0: "Normal", 1: "Linkage", 2: "Atom"}),  # config
        MapConv("mode_5", "select", mi="13.p.2", map={0: "Scene", 1: "Wireless"}),  # config
        MapConv("mode_6", "select", mi="14.p.2", map={0: "Scene", 1: "Wireless"}),  # config
        MapConv("power_on_state_1", "select", mi="2.p.5", map={0: "Default", 1: "Off", 2: "On"}),  # config
        MapConv("power_on_state_2", "select", mi="3.p.3", map={0: "Default", 1: "Off", 2: "On"}),  # config
        MapConv("power_on_state_3", "select", mi="4.p.3", map={0: "Default", 1: "Off", 2: "On"}),  # config
        MapConv("power_on_state_4", "select", mi="5.p.3", map={0: "Default", 1: "Off", 2: "On"}),  # config
        BaseConv("action", "sensor"),
        MapConv("action", mi="6.e.1.p.2", map={1: BUTTON_1_SINGLE, 2: BUTTON_2_SINGLE, 3: BUTTON_3_SINGLE, 4: BUTTON_4_SINGLE, 5: "button_5_single", 6: "button_6_single"}),
    ],
}, {
    "default": "mesh",  # default Mesh device
    "spec": [
        BaseConv("switch", "switch", mi="2.p.1", entity=ENTITY_LAZY),  # bool
    ],
}]

# Mesh groups
DEVICES += [{
    1054: ["Yeelight", "Mesh Group", "yeelink.light.mb1grp"],
    68286: ["Xiaomi", "Light Group", "mijia.light.group3"],
    "spec": [
        BaseConv("light", "light", mi="2.p.1", entity={"icon": "mdi:lightbulb-group"}),  # bool
        BrightnessConv("brightness", mi="2.p.2", max=65535),  # uint16
        ColorTempKelvin("color_temp", mi="2.p.3"),  # uint32, 2700..6500
    ]
}, {
    71017: ["Xiaomi", "Curtain Group", "lumi.curtain.hmcn04"],
    "spec": [
        MapConv("motor", "cover", mi="2.p.1", map={0: "stop", 1: "open", 2: "close"}),  # uint8
        BaseConv("target_position", mi="2.p.2"),  # percentage, 0..100
        CurtainPosConv("position"),
    ],
}]

# Matter
DEVICES += [{
    "matter.plug.mplug": [None, "Matter Plug"],
    "spec": [
        BaseConv("switch", "switch", mi="2.1.1"),
    ],
}, {
    "matter.light.mlight": [None, "Matter Light"],
    "spec": [
        BaseConv("light", "light", mi="5.1.1"),
        BrightnessConv("brightness", mi="5.1.3"),
        ColorTempKelvin("color_temp", mi="5.1.5", mink=1000, maxk=10000),
        MathConv("color", "number", mi="5.1.4", min=1, max=16777215),
        MapConv("color_mode", mi="5.1.8", map={1: "rgb", 2: "color_temp"}),
        MapConv("power_on_state", "select", mi="5.1.7", map={0: "default", 1: "off", 2: "on"}),
    ],
}]
