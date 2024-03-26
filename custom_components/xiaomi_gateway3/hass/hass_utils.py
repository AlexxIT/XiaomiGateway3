import logging
from urllib.parse import urlencode

import yaml
from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry, device_registry
from homeassistant.helpers.aiohttp_client import (
    async_create_clientsession,
    async_get_clientsession,
)
from homeassistant.helpers.entity_registry import RegistryEntry
from homeassistant.helpers.storage import Store

from .. import XDevice
from ..core import core_utils
from ..core.const import DOMAIN, ZIGBEE, SUPPORTED_MODELS
from ..core.gate.base import XGateway
from ..core.xiaomi_cloud import MiCloud

_LOGGER = logging.getLogger(__package__)


def fix_yaml_devices_config(value: dict):
    for uid, config in list(value.items()):
        new_uid = f"0x{uid:016x}" if isinstance(uid, int) else uid.lower()
        if uid != new_uid:
            value[new_uid] = value.pop(uid)
        for k, v in config.items():
            if isinstance(v, dict):
                config[k] = dict(v)  # fix NodeDictClass
    return value


async def store_devices(hass: HomeAssistant):
    store = Store(hass, 1, f"{DOMAIN}/devices.json")
    # load devices from the store
    if data := await store.async_load():
        XDevice.restore = data

    # noinspection PyUnusedLocal
    async def stop(*args):
        # update last_decode_ts for all devices in the store
        for device in XGateway.devices.values():
            if device.last_decode_ts:
                store_device = XDevice.restore.setdefault(device.cloud_did, {})
                store_device["last_decode_ts"] = device.last_decode_ts
        # save store if not empty
        if XDevice.restore:
            await store.async_save(XDevice.restore)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop)


def get_cloud_gateways(hass: HomeAssistant) -> list[dict]:
    gateways = []
    for item in hass.data[DOMAIN].values():
        if isinstance(item, MiCloud) and item.devices:
            gateways += [i for i in item.devices if i["model"] in SUPPORTED_MODELS]
    return gateways


async def setup_cloud(hass: HomeAssistant, config_entry: ConfigEntry):
    data: dict = config_entry.data.copy()

    session = async_create_clientsession(hass)
    cloud = MiCloud(session, data["servers"])
    if await cloud.login(data["username"], data["password"]):
        cloud.devices = await cloud.get_devices()  # load devices from cloud

    hass.data[DOMAIN][config_entry.entry_id] = cloud

    store = Store(hass, 1, f"{DOMAIN}/{data['username']}.json")
    if cloud.devices:
        await store.async_save(cloud.devices)  # cache cloud devices
    else:
        cloud.devices = await store.async_load()  # restore cloud devices from cache

    for cloud_device in cloud.devices or []:
        # "blt.", "lumi.", "group.", "123"
        store_device = XDevice.restore.setdefault(cloud_device["did"], {})
        store_device["cloud_name"] = cloud_device["name"]
        if fw := cloud_device["extra"].get("fw_version"):
            store_device["cloud_fw"] = fw

        await update_device_name(hass, cloud_device)

    return bool(cloud.auth)


async def update_device_name(hass: HomeAssistant, cloud_device: dict):
    for device in XGateway.devices.values():
        # search device
        if device.cloud_did != cloud_device["did"]:
            continue

        # check if cloud name changed
        if device.extra.get("cloud_name") == cloud_device["name"]:
            return

        # update cloud_name
        device.extra["cloud_name"] = cloud_device["name"]

        registry = device_registry.async_get(hass)
        device_entry = registry.async_get_device({(DOMAIN, device.uid)})

        # check if device_entry.name changed
        if device_entry and device_entry.name != device.human_name:
            registry.async_update_device(device_entry.id, name=device.human_name)
        return


async def store_gateway_key(hass: HomeAssistant, config_entry: ConfigEntry):
    if len(config_entry.options.get("key", "")) == 16:
        return

    options = config_entry.options
    info = await core_utils.gateway_info(options["host"], options["token"])
    if not info.get("key"):
        return

    options = {**options, "key": info["key"]}
    hass.config_entries.async_update_entry(config_entry, data={}, options=options)

    store = Store(hass, 1, f"{DOMAIN}/keys.json")
    data = await store.async_load() or {}
    data[info["did"]] = info
    await store.async_save(data)


async def show_device_info(
    hass: HomeAssistant, device: XDevice, title: str, notification_id: str
):
    info = device.as_dict()
    msg = f"```{yaml.safe_dump(info, allow_unicode=True)}```\n"

    # 2. link to XiaomiGateway3
    query = {"q": f"repo:AlexxIT/XiaomiGateway3 {device.model}", "type": "code"}
    msg += f" [XiaomiGateway3](https://github.com/search?{urlencode(query)})"

    if device.type == ZIGBEE:
        # 3. link to Zigbee2MQTT
        query = {
            "q": f"repo:Koenkk/zigbee-herdsman-converters {device.model}",
            "type": "code",
        }
        msg += f" [Zigbee2MQTT](https://github.com/search?{urlencode(query)})"

    if model := device.miot_model:
        # 4. link to miot-spec.com
        msg += f" [miot-spec.com](https://home.miot-spec.com/s/{model})"

        # 5. link to miot-spec.org
        spec = await get_miot_spec(hass)
        for i in spec["instances"]:
            if i["model"] == model:
                msg += f" [miot-spec.org](https://miot-spec.org/miot-spec-v2/instance?type={i['type']})"
                break

    persistent_notification.async_create(hass, msg, title, notification_id)


async def get_miot_spec(hass: HomeAssistant) -> dict:
    if "miot-spec.org" not in hass.data:
        session = async_get_clientsession(hass)
        r = await session.get("https://miot-spec.org/miot-spec-v2/instances?status=all")
        hass.data["miot-spec.org"] = await r.json()
    return hass.data["miot-spec.org"]


def remove_stats_entities(hass: HomeAssistant, config_entry: ConfigEntry):
    """Search and remove all stats entities from this config entry with wrong domain."""
    domain = config_entry.options.get("stats")

    registry = entity_registry.async_get(hass)
    remove = [
        entity.entity_id
        for entity in list(registry.entities.values())
        if entity.config_entry_id == config_entry.entry_id
        and entity.unique_id.endswith(("_ble", "_mesh", "_zigbee"))
        and entity.domain != domain
    ]

    for entity_id in remove:
        registry.async_remove(entity_id)


def migrate_legacy_entitites_unique_id(hass: HomeAssistant):
    registry = entity_registry.async_get(hass)
    for entity in list(registry.entities.values()):
        if entity.platform != DOMAIN:
            continue

        if new_unique_id := check_entity_unique_id(entity):
            _LOGGER.info(f"Migrate entity: {entity.entity_id} new uid: {new_unique_id}")
            registry.async_update_entity(entity.entity_id, new_unique_id=new_unique_id)


def migrate_devices_store():
    for k, v in list(XDevice.restore.items()):
        # check old storing format
        if "decode_ts" not in v:
            continue

        # we can restore only zigbee uid to xiaomi did (not cloud did)
        if k.startswith("0x"):
            did = "lumi." + k.lstrip("0x")
            XDevice.restore[did] = {"last_decode_ts": v["decode_ts"]}

        XDevice.restore.pop(k)


def check_entity_unique_id(registry_entry: RegistryEntry) -> str | None:
    has_update = False

    # split mac and attr in unique id
    uid, attr = registry_entry.unique_id.split("_", 1)

    if uid.startswith("0x"):
        # ZIGBEE format should be "0x" + 16 hex lowercase
        if len(uid) < 18:
            uid = f"0x{uid[2:]:>016s}"
            has_update = True
    elif len(uid) == 12:
        # GATEWAY, BLE, MESH format should be 12 hex lowercase
        if uid.isupper():
            uid = uid.lower()
            has_update = True
    elif not uid.startswith("group"):
        # GROUP format should be "group" + big int
        if registry_entry.original_icon == "mdi:lightbulb-group":
            did = int.from_bytes(bytes.fromhex(uid), "big")
            uid = f"group{did}"
            has_update = True

    if attr == "switch":
        # attr for "plug" and "outlet" should be not "switch"
        if registry_entry.original_device_class in ("plug", "outlet"):
            attr = registry_entry.original_device_class
            has_update = True
    elif attr.startswith("channel ") or attr.endswith(" density"):
        # spaces in attr was by mistake
        attr = attr.replace(" ", "_")
        has_update = True
    elif attr == "pressure_state":
        attr = "pressure"
    elif attr == "occupancy_distance":
        attr = "distance"

    return f"{uid}_{attr}" if has_update else None


def remove_device(hass: HomeAssistant, device: XDevice):
    """Remove hass DeviceEntry and XDevice from all XGateway(s)."""
    registry = device_registry.async_get(hass)
    if device_entry := registry.async_get_device({(DOMAIN, device.uid)}):
        registry.async_remove_device(device_entry.id)

    for gw in device.gateways:
        gw.remove_device(device)
