import copy
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry, entity_registry
from .entity import XEntity
from .. import MultiGateway, XDevice
from ..core.const import BLE, DOMAIN, GATEWAY, MATTER, MESH, ZIGBEE
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
            fix_device_registry(hass, config_entry.entry_id, device.uid)

        # instant setup all entities, except lazy
        for entity in get_entities(device, gw.stats_domain):
            gw.debug("add_entity", device=device, entity=entity.entity_id)
            # Fix: Use .get() to prevent KeyError, and warn if missing
            add_key = config_entry.entry_id + entity.domain
            async_add_entities = XEntity.ADD.get(add_key)
            if async_add_entities:
                async_add_entities([entity], update_before_add=False)
            else:
                gw.warning("add_entity_skipped", device=device, entity=entity.entity_id, key=add_key)  # FIX: upgrade to warning

        # add listener for setup lazy entities (if device has them)
        if remove_listener := handle_lazy_entities(hass, config_entry, device):
            lazy_listeners[device.did] = remove_listener

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

    def add_lazy_entity(attr: str):
        # FIX: Safely find converter, avoid StopIteration
        conv = next((i for i in device.converters if i.attr == attr and i.domain), None)
        if conv is None:
            gw = CONFIG_ENTRIES.get(device.did)
            if gw:
                gw.warning("add_lazy_entity_failed", device=device, attr=attr, reason="No converter with domain")
            # Remove attr to prevent repeated warnings, but entity cannot be created
            lazy_attrs.discard(attr)
            return None
        
        # Remove attr only after successful creation
        lazy_attrs.remove(attr)
        entity = create_entity(device, conv)
        gw = CONFIG_ENTRIES.get(device.did)
        gw.debug("add_lazy_entity", device=device, entity=entity.entity_id)
        
        # Fix: Use .get() and warn if missing
        add_key = config_entry.entry_id + entity.domain
        async_add_entities = XEntity.ADD.get(add_key)
        if async_add_entities:
            async_add_entities([entity], update_before_add=False)
        else:
            gw.warning("add_lazy_entity_skipped", device=device, entity=entity.entity_id, key=add_key)
            # If the entity couldn't be added, we should not return it
            return None
            
        return entity

    # 3. Restore previous lazy entities from Hass entity registry
    prefix = device.uid + "_"
    reg = entity_registry.async_get(hass)
    for entry in reg.entities.values():
        if entry.platform != DOMAIN or not entry.unique_id.startswith(prefix):
            continue
        # FIX: Use rsplit to correctly handle underscores in device.uid
        _, attr = entry.unique_id.rsplit("_", 1)
        if attr in lazy_attrs:
            add_lazy_entity(attr)

    # 4. Exit if none left
    if not lazy_attrs:
        return None

    def on_device_update(data: dict):
        for attr in data.keys() & lazy_attrs.copy():  # copy to avoid mutation during iteration
            entity = add_lazy_entity(attr)
            if entity is not None:
                # FIX: Defer update to avoid race condition with async_add_entities
                # Use call_soon to ensure entity is fully registered before update
                hass.loop.call_soon(lambda e=entity, d=data: e.on_device_update(d))
                
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

def fix_device_registry(hass: HomeAssistant, config_entry_id: str, device_uid: str):
    """
    Fixing the consequences of the 2026.8 update.
    https://developers.home-assistant.io/blog/2026/07/21/device-registry-single-config-entry/
    """
    dr = device_registry.async_get(hass)
    # check all device entries
    entries = dr.devices.get_entries(identifiers={(DOMAIN, device_uid)})
    # first time start - just skip
    if len(entries) == 0:
        return
    # single device - check if it is from this config entry
    if len(entries) == 1:
        if entries[0].config_entry_id != config_entry_id:
            dr.async_update_device(entries[0].id, new_config_entry_id=config_entry_id)
        return
    
    # multiple devices - find the one with entities and remove all others
    er = entity_registry.async_get(hass)
    devices_ids = er.async_device_ids()
    main_device = None

    for entry in entries:
        if entry.id in devices_ids:
            # if device has entities
            if main_device is None:
                # set main device
                main_device = entry
                continue

            # if another device has entities (maybe old converter)
            for entity in er.entities.get_entries_for_device_id(entry.id, True):
                # move this entities to main device
                er.async_update_entity(entity.entity_id, device_id=main_device.id)

        # remove this device, because it is without entities (or entities were just moved)
        dr.async_remove_device(entry.id)

    if main_device and main_device.config_entry_id != config_entry_id:
        # move main device to current config entry
        dr.async_update_device(main_device.id, new_config_entry_id=config_entry_id)
