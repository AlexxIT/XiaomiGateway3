"""Set entity attributes based on converter settings."""
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.cover import CoverDeviceClass
from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import (
    CONCENTRATION_MILLIGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_PARTS_PER_MILLION,
    LIGHT_LUX,
    MAJOR_VERSION,
    MINOR_VERSION,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfElectricPotential,
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfLength,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.helpers.entity import Entity, EntityCategory

from ..core.converters.base import BaseConv
from ..core.converters.const import ENTITY_LAZY

if (MAJOR_VERSION, MINOR_VERSION) >= (2024, 11):
    from homeassistant.const import UnitOfConductivity

    CONDUCTIVITY = UnitOfConductivity.MICROSIEMENS_PER_CM
elif (MAJOR_VERSION, MINOR_VERSION) >= (2024, 7):
    from homeassistant.const import UnitOfConductivity

    CONDUCTIVITY = UnitOfConductivity.MICROSIEMENS
else:
    from homeassistant.const import CONDUCTIVITY

# just to reduce the code
CELSIUS = UnitOfTemperature.CELSIUS
CONFIG = EntityCategory.CONFIG
DIAGNOSTIC = EntityCategory.DIAGNOSTIC
SENSOR = SensorDeviceClass

# convert key from entity description to Entity attribute
ENTITY_KEYS = {
    "category": "_attr_entity_category",
    "class": "_attr_device_class",
    "enabled": "_attr_entity_registry_enabled_default",
    "force": "_attr_force_update",
    "icon": "_attr_icon",
    "mode": "_attr_mode",  # NumberMode
    "name": "_attr_name",
    "poll": "_attr_should_poll",
    "statistics": "_attr_state_class",
    "units": "_attr_native_unit_of_measurement",
    "visible": "_attr_entity_registry_visible_default",
    "translation_key": "_attr_translation_key",
}

# description with class should be used with "domain.attr"
# other descriptions can be used with only "attr"
ENTITY_DESCRIPTIONS: dict[str, dict] = {
    ##
    # sensors with device class
    "sensor.current": {"class": SENSOR.CURRENT, "units": UnitOfElectricCurrent.AMPERE},
    "sensor.distance": {"class": SENSOR.DISTANCE, "units": UnitOfLength.METERS},
    "sensor.illuminance": {"class": SENSOR.ILLUMINANCE, "units": LIGHT_LUX},
    "sensor.humidity": {"class": SENSOR.HUMIDITY, "units": PERCENTAGE},
    "sensor.moisture": {"class": SENSOR.MOISTURE, "units": PERCENTAGE},
    "sensor.power": {"class": SENSOR.POWER, "units": UnitOfPower.WATT, "translation_key": "power"},
    "sensor.pressure": {"class": SENSOR.PRESSURE, "units": UnitOfPressure.HPA},
    "sensor.temperature": {"class": SENSOR.TEMPERATURE, "units": CELSIUS},
    "sensor.voltage": {"class": SENSOR.VOLTAGE, "units": UnitOfElectricPotential.VOLT},
    ##
    # binary sensors with device class
    "binary_sensor.contact": {"class": BinarySensorDeviceClass.DOOR, "translation_key": "contact"},
    "binary_sensor.latch": {"class": BinarySensorDeviceClass.LOCK, "translation_key": "latch"},
    "binary_sensor.moisture": {"class": BinarySensorDeviceClass.MOISTURE},
    "binary_sensor.plug_detection": {"class": BinarySensorDeviceClass.PLUG},
    "binary_sensor.pressure": {"class": BinarySensorDeviceClass.VIBRATION, "translation_key": "pressure"},
    "binary_sensor.reverse": {"class": BinarySensorDeviceClass.LOCK, "translation_key": "reverse"},
    "binary_sensor.square": {"class": BinarySensorDeviceClass.LOCK, "translation_key": "square"},
    "binary_sensor.water_leak": {"class": BinarySensorDeviceClass.MOISTURE},
    ##
    # sensors without device class
    "action": {"icon": "mdi:bell", "translation_key": "action"},
    "conductivity": {"icon": "mdi:flower", "units": CONDUCTIVITY, "translation_key": "conductivity"},
    "formaldehyde": {"units": CONCENTRATION_MILLIGRAMS_PER_CUBIC_METER, "translation_key": "formaldehyde"},
    "gas_density": {"icon": "mdi:google-circles-communities", "units": "% LEL", "translation_key": "gas_density"},
    "rssi": {"units": SIGNAL_STRENGTH_DECIBELS_MILLIWATT, "translation_key": "rssi"},
    "smoke_density": {"icon": "mdi:google-circles-communities", "units": "% obs/ft", "translation_key": "smoke_density"},
    "supply": {"icon": "mdi:gauge", "units": PERCENTAGE, "translation_key": "supply"},
    "tvoc": {"icon": "mdi:cloud", "units": CONCENTRATION_PARTS_PER_BILLION, "translation_key": "tvoc"},
    "eco_two": {"icon": "mdi:molecule-co2", "units": CONCENTRATION_PARTS_PER_MILLION, "translation_key": "e_co2"},
    ##
    # stats sensors
    "binary_sensor.gateway": {
        "class": BinarySensorDeviceClass.CONNECTIVITY,
        "icon": "mdi:router-wireless",
        "translation_key": "gateway",
    },
    "binary_sensor.ble": {
        "class": BinarySensorDeviceClass.CONNECTIVITY,
        "category": DIAGNOSTIC,
        "icon": "mdi:bluetooth",
        "translation_key": "ble",
    },
    "binary_sensor.mesh": {
        "class": BinarySensorDeviceClass.CONNECTIVITY,
        "category": DIAGNOSTIC,
        "icon": "mdi:bluetooth",
        "translation_key": "mesh",
    },
    "binary_sensor.zigbee": {
        "class": BinarySensorDeviceClass.CONNECTIVITY,
        "category": DIAGNOSTIC,
        "icon": "mdi:zigbee",
        "translation_key": "zigbee",
    },
    "sensor.ble": {
        "class": SENSOR.TIMESTAMP,
        "category": DIAGNOSTIC,
        "icon": "mdi:bluetooth",
        "translation_key": "ble",
    },
    "sensor.mesh": {
        "class": SENSOR.TIMESTAMP,
        "category": DIAGNOSTIC,
        "icon": "mdi:bluetooth",
        "translation_key": "mesh",
    },
    "sensor.zigbee": {
        "class": SENSOR.TIMESTAMP,
        "category": DIAGNOSTIC,
        "icon": "mdi:zigbee",
        "translation_key": "zigbee",
    },
    ##
    # main controls
    "alarm_trigger": {"icon": "mdi:alarm-bell", "translation_key": "alarm_trigger"},
    "fan": {"icon": "mdi:fan", "translation_key": "fan"},
    "light.light": {"name": None},
    "switch.channel": {"class": SwitchDeviceClass.SWITCH, "translation_key": "channel"},
    "switch.outlet": {"class": SwitchDeviceClass.OUTLET, "icon": "mdi:power-socket-us", "translation_key": "outlet"},
    "switch.plug": {"class": SwitchDeviceClass.OUTLET, "icon": "mdi:power-plug", "translation_key": "plug"},
    "switch.switch": {"class": SwitchDeviceClass.SWITCH, "translation_key": "switch"},
    "usb": {"icon": "mdi:usb-port"},
    ##
    # batteries and energy sensors
    "sensor.battery": {
        "class": SENSOR.BATTERY,
        "units": PERCENTAGE,
        "category": DIAGNOSTIC,
    },
    "sensor.battery_original": {
        "class": SENSOR.BATTERY,
        "units": PERCENTAGE,
        "category": DIAGNOSTIC,
        "enabled": False,
        "translation_key": "battery_original",
    },
    "sensor.battery_voltage": {
        "class": SENSOR.VOLTAGE,
        "units": UnitOfElectricPotential.MILLIVOLT,
        "category": DIAGNOSTIC,
        "translation_key": "battery_voltage",
    },
    "binary_sensor.battery_charging": {
        "class": BinarySensorDeviceClass.BATTERY_CHARGING,
        "category": DIAGNOSTIC,
        "enabled": False,
    },
    "binary_sensor.battery_low": {
        "class": BinarySensorDeviceClass.BATTERY,
        "category": DIAGNOSTIC,
        "enabled": False,
    },
    "sensor.energy": {
        "class": SENSOR.ENERGY,
        "statistics": SensorStateClass.TOTAL,
        "units": UnitOfEnergy.KILO_WATT_HOUR,
        "translation_key": "power_consumption",
    },
    ##
    # CONFIG controls
    "backlight": {"category": CONFIG, "enabled": False, "translation_key": "backlight"},
    "blind_time": {"category": CONFIG, "enabled": False, "translation_key": "blind_time"},
    "charge_protect": {"category": CONFIG, "enabled": False, "translation_key": "charge_protect"},
    "child_lock": {"category": CONFIG, "enabled": False, "icon": "mdi:baby-carriage", "translation_key": "child_lock"},
    "display_unit": {"category": CONFIG, "enabled": False, "translation_key": "display_unit"},
    "flex_switch": {"category": CONFIG, "enabled": False, "translation_key": "flex_switch"},
    "led": {"category": CONFIG, "enabled": False, "icon": "mdi:led-off", "translation_key": "led"},
    "led_reverse": {"category": CONFIG, "enabled": False, "icon": "mdi:led-off", "translation_key": "led_reverse"},
    "mode": {"category": CONFIG, "enabled": False, "icon": "mdi:cog", "translation_key": "mode"},
    "motor_reverse": {"category": CONFIG, "enabled": False, "translation_key": "motor_reverse"},
    "motor_speed": {"category": CONFIG, "enabled": False, "translation_key": "motor_speed"},
    "power_off_memory": {"category": CONFIG, "enabled": False, "translation_key": "power_off_memory"},
    "power_on_state": {"category": CONFIG, "enabled": False, "translation_key": "power_on_state"},
    "sensitivity": {"category": CONFIG, "enabled": False, "translation_key": "sensitivity"},
    "wireless": {"category": CONFIG, "enabled": False, "translation_key": "wireless"},
    ##
    # DIAGNOSTIC controls
    "command": {"category": DIAGNOSTIC, "icon": "mdi:apple-keyboard-command", "translation_key": "command"},
    "data": {"category": DIAGNOSTIC, "icon": "mdi:information-box", "translation_key": "data"},
    ##
    # CONFIG and DIAGNOSTIC sensors
    "sensor.chip_temperature": {
        "class": SENSOR.TEMPERATURE,
        "units": UnitOfTemperature.CELSIUS,
        "category": DIAGNOSTIC,
        "enabled": False,
        "translation_key": "chip_temperature",
    },
    "fault": {"category": DIAGNOSTIC, "translation_key": "fault"},
    "sensor.idle_time": {
        "class": SENSOR.DURATION,
        "icon": "mdi:timer",
        "units": UnitOfTime.SECONDS,
        "category": DIAGNOSTIC,
        "enabled": False,
        "translation_key": "idle_time",
    },
}

DOMAIN_CLASSES = {
    "binary_sensor": BinarySensorDeviceClass,
    "cover": CoverDeviceClass,
    "number": NumberDeviceClass,
    "sensor": SensorDeviceClass,
    "switch": SwitchDeviceClass,
}


def setup_entity_description(entity: Entity, conv: BaseConv) -> bool:
    # 1. auto match entity description based on converter domain and attr name
    key = conv.attr.rstrip("_01234567890")  # remove tail _1, _2, _3
    tail_index = conv.attr[len(key)+1:]  # get tail 1, 2, 3
    domain_key = f"{conv.domain}.{key}"
    desc = ENTITY_DESCRIPTIONS.get(domain_key) or ENTITY_DESCRIPTIONS.get(key)

    # 2. overwrite desc via custom conv entity description
    if conv.entity:
        desc = desc | conv.entity if desc else conv.entity

    # 3. auto match only device_class based on converter domain
    if not desc or desc == ENTITY_LAZY:
        if domain_class := DOMAIN_CLASSES.get(conv.domain):
            if key in iter(domain_class):
                entity._attr_device_class = domain_class(key)
                return True
        return False

    for k, v in desc.items():
        if k == "lazy" or (v is None and k != "name"):
            continue
        if k == "category" and type(v) is str:
            v = EntityCategory(v)
        elif k == "class" and type(v) is str:
            if domain_class := DOMAIN_CLASSES.get(conv.domain):
                v = domain_class(v)
        elif k == "translation_key" and tail_index:
            v = f"{v}_n"
            setattr(entity, "_attr_translation_placeholders", {"n": tail_index})
        setattr(entity, ENTITY_KEYS.get(k) or k, v)

    # sensor with unit_of_measurement and without state_class will be MEASUREMENT
    # https://developers.home-assistant.io/docs/core/entity/sensor/#long-term-statistics
    if (
        conv.domain == "sensor"
        and hasattr(entity, "_attr_native_unit_of_measurement")
        and not hasattr(entity, "_attr_state_class")
    ):
        setattr(entity, "_attr_state_class", SensorStateClass.MEASUREMENT)

    return True
