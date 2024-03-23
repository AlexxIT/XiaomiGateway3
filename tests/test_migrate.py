from homeassistant.helpers.entity_registry import RegistryEntry

from custom_components.xiaomi_gateway3.hass.hass_utils import check_entity_unique_id


def test_migrate_entity_unique_id():
    eid = "sensor.dummy"

    entry = RegistryEntry(
        entity_id=eid,
        unique_id="0x158d000fffffff_gas density",
        platform="",
    )
    assert check_entity_unique_id(entry) == "0x00158d000fffffff_gas_density"

    entry = RegistryEntry(
        entity_id=eid,
        unique_id="0x158d000fffffff_smoke density",
        platform="",
    )
    assert check_entity_unique_id(entry) == "0x00158d000fffffff_smoke_density"

    entry = RegistryEntry(
        entity_id=eid,
        unique_id="50EC50FFFFFF_light",
        platform="",
    )
    assert check_entity_unique_id(entry) == "50ec50ffffff_light"

    entry = RegistryEntry(
        entity_id=eid,
        unique_id="0x158d000fffffff_switch",
        platform="",
        original_device_class="plug",
        original_icon="mdi:power-plug",
    )
    assert check_entity_unique_id(entry) == "0x00158d000fffffff_plug"

    entry = RegistryEntry(
        entity_id=eid,
        unique_id="13e81ad1f34ab000_light",
        platform="",
        original_device_class=None,
        original_icon="mdi:lightbulb-group",
    )

    assert check_entity_unique_id(entry) == "group1434425970349748224_light"
