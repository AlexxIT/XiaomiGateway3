import copy

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry, entity_registry

from .entity import XEntity
from .. import XDevice, MultiGateway
from ..core.const import DOMAIN, GATEWAY, BLE, MATTER, MESH, ZIGBEE
from ..core.converters.base import BaseConv
from ..core.gate.base import EVENT_ADD_DEVICE, EVENT_REMOVE_DEVICE

CONFIG_ENTRIES: dict[str, MultiGateway] = {}  # key is device did


def handle_add_entities(
    hass: HomeAssistant, config_entry: ConfigEntry, gw: MultiGateway
):
    """Add entities when gateway calls the add_device event."""
    lazy_listeners: dict = {}

    def add_device(device: XDevice):
        if device.extra.get("entities") is False:
            return

        if device.did not in CONFIG_ENTRIES:
            # connect all device entities to this gateway
            CONFIG_ENTRIES[device.did] = gw

            # instant setup all entities, except lazy
            for entity in get_entities(device, gw.stats_domain):
                gw.debug("add_entity", device=device, entity=entity.entity_id)
                add_entity(hass, config_entry, entity)

            # add listener for setup lazy entities (if device has them)
            if remove_listener := handle_lazy_entities(hass, config_entry, device):
                lazy_listeners[device.did] = remove_listener
        else:
            # device already added to another config entry (gateway)
            # so we add device to the current config entry
            device_registry.async_get(hass).async_get_or_create(
                config_entry_id=config_entry.entry_id,
                identifiers={(DOMAIN, device.uid)},
            )

    def remove_device(device: XDevice):
        # remove device entities connection to this gateway
        if CONFIG_ENTRIES.get(device.did) == gw:
            # remove lazy entities listener if device has them
            if remove_listener := lazy_listeners.get(device.did):
                remove_listener()

            CONFIG_ENTRIES.pop(device.did)

    gw.add_event_listener(EVENT_ADD_DEVICE, add_device)
    gw.add_event_listener(EVENT_REMOVE_DEVICE, remove_device)


def get_entities(device: XDevice, stats_domain: str = None) -> list[XEntity]:
    converters = [i for i in device.converters if i.domain]

    # TODO: fixme
    if device.type == GATEWAY:
        converters.append(BaseConv(device.type, "binary_sensor"))
    if device.type != GATEWAY:
        converters.append(BaseConv("command", "select"))

    # custom stats sensors
    if stats_domain and device.type in (BLE, MATTER, MESH, ZIGBEE):
        converters.append(BaseConv(device.type, stats_domain))

    # custom entities settings from YAML
    if entities := device.extra.get("entities"):
        get_extra_entities(converters, entities)

    return [
        create_entity(device, conv)
        for conv in converters
        if not (conv.entity and conv.entity.get("lazy"))
    ]


def create_entity(device: XDevice, conv: BaseConv) -> XEntity:
    """Create entity, based on device model/type and conv domain."""
    cls = (
        XEntity.NEW.get(f"{conv.domain}.model.{device.model}")
        or XEntity.NEW.get(f"{conv.domain}.type.{device.type}")
        or XEntity.NEW.get(f"{conv.domain}.attr.{conv.attr}")
        or XEntity.NEW.get(conv.domain)
    )
    return cls(device, conv)


def add_entity(hass: HomeAssistant, config_entry: ConfigEntry, entity: XEntity):
    # if device belong to multiple config entries - disabling one of config entry will
    # block any other config entry for creation device entities
    reg = entity_registry.async_get(hass)
    entity_id = reg.async_get_entity_id(entity.domain, DOMAIN, entity.unique_id)
    if registry_entry := reg.async_get(entity_id):
        # remove disabled_by flag for entity
        if registry_entry.disabled_by == "config_entry":
            reg.async_update_entity(entity_id=entity_id, disabled_by=None)

    async_add_entities = XEntity.ADD[config_entry.entry_id + entity.domain]
    async_add_entities([entity], update_before_add=False)


def handle_lazy_entities(
    hass: HomeAssistant, config_entry: ConfigEntry, device: XDevice
):
    """Create entities only when first data arrived."""
    # 1. Check if device has lazy entities
    lazy_attrs = {
        i.attr for i in device.converters if i.entity and i.entity.get("lazy")
    }
    # 2. Exit if none
    if not lazy_attrs:
        return None

    def add_lazy_entity(attr: str) -> XEntity:
        lazy_attrs.remove(attr)

        conv = next(i for i in device.converters if i.attr == attr)
        entity = create_entity(device, conv)

        gw = CONFIG_ENTRIES.get(device.did)
        gw.debug("add_lazy_entity", device=device, entity=entity.entity_id)
        add_entity(hass, config_entry, entity)
        return entity

    # 3. Restore previous lazy entities from Hass entity registry
    prefix = device.uid + "_"
    reg = entity_registry.async_get(hass)
    for entry in reg.entities.values():
        if entry.platform != DOMAIN or not entry.unique_id.startswith(prefix):
            continue
        _, attr = entry.unique_id.split("_", 1)
        if attr in lazy_attrs:
            add_lazy_entity(attr)

    # 4. Exit if none left
    if not lazy_attrs:
        return None

    def on_device_update(data: dict):
        for attr in data.keys() & lazy_attrs:
            entity = add_lazy_entity(attr)
            entity.on_device_update(data)

            if not lazy_attrs:
                device.remove_listener(on_device_update)

    # 5. Wait for rest lazy entities in every message from the device
    device.add_listener(on_device_update)
    return lambda: device.remove_listener(on_device_update)


def get_extra_entities(converters: list[BaseConv], entities: dict[str, str]):
    for attr, new_domain in entities.items():
        for i, conv in enumerate(converters):
            if conv.attr == attr:
                if new_domain:
                    new_conv = copy.copy(conv)
                    new_conv.domain = new_domain
                    converters[i] = new_conv
                else:
                    converters.pop(i)
                break
        else:
            converters.append(BaseConv(attr, new_domain))
