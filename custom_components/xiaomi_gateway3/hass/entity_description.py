"""Set entity attributes based on converter settings."""
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.cover import CoverDeviceClass
from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import (
    CONCENTRATION_MILLIGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_BILLION,
    CONDUCTIVITY,
    LIGHT_LUX,
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
    "sensor.power": {"class": SENSOR.POWER, "units": UnitOfPower.WATT},
    "sensor.pressure": {"class": SENSOR.PRESSURE, "units": UnitOfPressure.HPA},
    "sensor.temperature": {"class": SENSOR.TEMPERATURE, "units": CELSIUS},
    "sensor.voltage": {"class": SENSOR.VOLTAGE, "units": UnitOfElectricPotential.VOLT},
    ##
    # binary sensors with device class
    "binary_sensor.contact": {"class": BinarySensorDeviceClass.DOOR},
    "binary_sensor.latch": {"class": BinarySensorDeviceClass.LOCK},
    "binary_sensor.moisture": {"class": BinarySensorDeviceClass.MOISTURE},
    "binary_sensor.plug_detection": {"class": BinarySensorDeviceClass.PLUG},
    "binary_sensor.pressure": {"class": BinarySensorDeviceClass.VIBRATION},
    "binary_sensor.reverse": {"class": BinarySensorDeviceClass.LOCK},
    "binary_sensor.square": {"class": BinarySensorDeviceClass.LOCK},
    "binary_sensor.water_leak": {"class": BinarySensorDeviceClass.MOISTURE},
    ##
    # sensors without device class
    "action": {"icon": "mdi:bell"},
    "conductivity": {"icon": "mdi:flower", "units": CONDUCTIVITY},
    "formaldehyde": {"units": CONCENTRATION_MILLIGRAMS_PER_CUBIC_METER},
    "gas_density": {"icon": "mdi:google-circles-communities", "units": "% LEL"},
    "rssi": {"units": SIGNAL_STRENGTH_DECIBELS_MILLIWATT},
    "smoke_density": {"icon": "mdi:google-circles-communities", "units": "% obs/ft"},
    "supply": {"icon": "mdi:gauge", "units": PERCENTAGE},
    "tvoc": {"icon": "mdi:cloud", "units": CONCENTRATION_PARTS_PER_BILLION},
    ##
    # stats sensors
    "binary_sensor.gateway": {
        "class": BinarySensorDeviceClass.CONNECTIVITY,
        "icon": "mdi:router-wireless",
    },
    "binary_sensor.ble": {
        "class": BinarySensorDeviceClass.CONNECTIVITY,
        "category": DIAGNOSTIC,
        "icon": "mdi:bluetooth",
    },
    "binary_sensor.mesh": {
        "class": BinarySensorDeviceClass.CONNECTIVITY,
        "category": DIAGNOSTIC,
        "icon": "mdi:bluetooth",
    },
    "binary_sensor.zigbee": {
        "class": BinarySensorDeviceClass.CONNECTIVITY,
        "category": DIAGNOSTIC,
        "icon": "mdi:zigbee",
    },
    "sensor.ble": {
        "class": SENSOR.TIMESTAMP,
        "category": DIAGNOSTIC,
        "icon": "mdi:bluetooth",
    },
    "sensor.mesh": {
        "class": SENSOR.TIMESTAMP,
        "category": DIAGNOSTIC,
        "icon": "mdi:bluetooth",
    },
    "sensor.zigbee": {
        "class": SENSOR.TIMESTAMP,
        "category": DIAGNOSTIC,
        "icon": "mdi:zigbee",
    },
    ##
    # main controls
    "alarm_trigger": {"icon": "mdi:alarm-bell"},
    "fan": {"icon": "mdi:fan"},
    "outlet": {"icon": "mdi:power-socket-us"},
    "plug": {"icon": "mdi:power-plug"},
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
    },
    "sensor.battery_voltage": {
        "class": SENSOR.VOLTAGE,
        "units": UnitOfElectricPotential.MILLIVOLT,
        "category": DIAGNOSTIC,
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
    },
    ##
    # CONFIG controls
    "backlight": {"category": CONFIG, "enabled": False},
    "blind_time": {"category": CONFIG, "enabled": False},
    "charge_protect": {"category": CONFIG, "enabled": False},
    "child_lock": {"category": CONFIG, "enabled": False, "icon": "mdi:baby-carriage"},
    "display_unit": {"category": CONFIG, "enabled": False},
    "flex_switch": {"category": CONFIG, "enabled": False},
    "led": {"category": CONFIG, "enabled": False, "icon": "mdi:led-off"},
    "led_reverse": {"category": CONFIG, "enabled": False, "icon": "mdi:led-off"},
    "mode": {"category": CONFIG, "enabled": False, "icon": "mdi:cog"},
    "motor_reverse": {"category": CONFIG, "enabled": False},
    "motor_speed": {"category": CONFIG, "enabled": False},
    "power_off_memory": {"category": CONFIG, "enabled": False},
    "power_on_state": {"category": CONFIG, "enabled": False},
    "sensitivity": {"category": CONFIG, "enabled": False},
    "wireless": {"category": CONFIG, "enabled": False},
    ##
    # DIAGNOSTIC controls
    "command": {"category": DIAGNOSTIC, "icon": "mdi:apple-keyboard-command"},
    "data": {"category": DIAGNOSTIC, "icon": "mdi:information-box"},
    ##
    # CONFIG and DIAGNOSTIC sensors
    "sensor.chip_temperature": {
        "class": SENSOR.TEMPERATURE,
        "units": UnitOfTemperature.CELSIUS,
        "category": DIAGNOSTIC,
        "enabled": False,
    },
    "fault": {"category": DIAGNOSTIC},
    "sensor.idle_time": {
        "class": SENSOR.DURATION,
        "icon": "mdi:timer",
        "units": UnitOfTime.SECONDS,
        "category": DIAGNOSTIC,
        "enabled": False,
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
    domain_key = f"{conv.domain}.{key}"
    desc = ENTITY_DESCRIPTIONS.get(domain_key) or ENTITY_DESCRIPTIONS.get(key)

    # 2. overwrite desc via custom conv entity description
    if conv.entity:
        desc = desc | conv.entity if desc else conv.entity

    # 3. auto match only device_class based on converter domain
    if not desc:
        if domain_class := DOMAIN_CLASSES.get(conv.domain):
            if key in iter(domain_class):
                entity._attr_device_class = domain_class(key)
                return True
        return False

    for k, v in desc.items():
        if k == "lazy" or v is None:
            continue
        if k == "category" and type(v) is str:
            v = EntityCategory(v)
        elif k == "class" and type(v) is str:
            if domain_class := DOMAIN_CLASSES.get(conv.domain):
                v = domain_class(v)
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
