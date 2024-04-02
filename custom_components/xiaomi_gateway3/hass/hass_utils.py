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
from homeassistant.helpers.storage import Store

from .. import XDevice
from ..core import core_utils
from ..core.const import DOMAIN, ZIGBEE, SUPPORTED_MODELS
from ..core.gate.base import XGateway
from ..core.xiaomi_cloud import MiCloud

_LOGGER = logging.getLogger(__package__)


def fix_yaml_devices_config(value: dict):
    for uid, config in list(value.items()):
        if isinstance(uid, int) and uid > 100_000:  # fix uid as int
            value[f"0x{uid:016x}"] = value.pop(uid)
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
            store_device = XDevice.restore.setdefault(device.cloud_did, {})
            store_device["uid"] = device.uid
            if device.last_report_ts:
                store_device["last_report_ts"] = device.last_report_ts
            if device.last_seen:
                store_device["last_seen"] = {
                    gw.uid: last_seen for gw, last_seen in device.last_seen.items()
                }
        # save store if not empty
        if XDevice.restore:
            await store.async_save(XDevice.restore)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop)


def get_cloud_gateways(hass: HomeAssistant) -> list[dict]:
    gateways = []
    for item in hass.data.get(DOMAIN, {}).values():
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
    options = config_entry.options

    # key probably OK, skip
    if (key := options.get("key")) and len(key) == 16:
        return

    info = await core_utils.gateway_info(options["host"], options["token"])
    if not info.get("key"):
        return

    options = {**options, "key": info["key"]}
    hass.config_entries.async_update_entry(config_entry, data={}, options=options)

    store = Store(hass, 1, f"{DOMAIN}/keys.json")
    data = await store.async_load() or {}
    data[info["did"]] = info
    await store.async_save(data)


async def restore_gateway_key(hass: HomeAssistant, token: str) -> str | None:
    store = Store(hass, 1, f"{DOMAIN}/keys.json")
    if data := await store.async_load():
        for device in data.values():
            if device["token"] == token:
                return device["key"]
    return None


class InfoDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


async def show_device_info(
    hass: HomeAssistant, device: XDevice, title: str, notification_id: str
):
    info = device.as_dict()
    msg = f"```{yaml.dump(info, Dumper=InfoDumper, allow_unicode=True)}```\n"

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
        and entity.unique_id.endswith(("_ble", "_matter", "_mesh", "_zigbee"))
        and entity.domain != domain
    ]

    for entity_id in remove:
        registry.async_remove(entity_id)


def migrate_legacy_devices_unique_id(hass: HomeAssistant):
    registry = device_registry.async_get(hass)
    for device in registry.devices.values():
        try:
            if not any(
                i[1] != migrate_uid(i[1]) for i in device.identifiers if i[0] == DOMAIN
            ):
                continue

            new_identifiers = {
                (DOMAIN, migrate_uid(i[1])) if i[0] == DOMAIN else i
                for i in device.identifiers
            }
            _LOGGER.info(f"Migrate device {device.identifiers} to {new_identifiers}")
            registry.async_update_device(device.id, new_identifiers=new_identifiers)
        except Exception as e:
            _LOGGER.warning(f"Migration error for {device}: {repr(e)}")


def migrate_legacy_entitites_unique_id(hass: HomeAssistant):
    registry = entity_registry.async_get(hass)
    for entry in list(registry.entities.values()):
        if entry.platform != DOMAIN:
            continue

        try:
            # split mac and attr in unique id
            uid, attr = entry.unique_id.split("_", 1)

            new_uid = migrate_uid(uid)
            new_attr = migrate_attr(attr, entry.original_device_class)
            if uid == new_uid and attr == new_attr:
                continue

            new_unique_id = f"{new_uid}_{new_attr}"
            _LOGGER.info(f"Migrate entity '{entry.unique_id}' to '{new_unique_id}'")
            registry.async_update_entity(entry.entity_id, new_unique_id=new_unique_id)
        except Exception as e:
            _LOGGER.warning(f"Migration error for {entry}: {repr(e)}")


def migrate_devices_store():
    for k, v in list(XDevice.restore.items()):
        # check old storing format
        if "decode_ts" in v:
            # we can restore only zigbee uid to xiaomi did (not cloud did)
            if k.startswith("0x"):
                did = "lumi." + k.lstrip("0x")
                store_device = XDevice.restore.get(did, {})
                store_device.setdefault("last_report_ts", v["decode_ts"])

            XDevice.restore.pop(k)

        if "last_decode_ts" in v:
            v["last_report_ts"] = v.pop("last_decode_ts")


def migrate_uid(uid: str) -> str:
    if uid.startswith("0x"):
        # ZIGBEE format should be "0x" + 16 hex lowercase
        if len(uid) < 18:
            return f"0x{uid[2:]:>016s}"
    elif len(uid) == 12:
        # GATEWAY, BLE, MESH format should be 12 hex lowercase
        if uid.isupper():
            return uid.lower()
    elif len(uid) == 16:
        if uid.endswith("000"):
            # GROUP format should be just 19 numbers
            return str(int.from_bytes(bytes.fromhex(uid), "big"))
    elif uid.startswith("group"):
        return uid[5:]
    return uid


def migrate_attr(attr: str, device_class: str) -> str:
    if attr == "switch":
        # attr for "plug" and "outlet" should be not "switch"
        if device_class in ("plug", "outlet"):
            return device_class
    elif attr.startswith("channel ") or attr.endswith(" density"):
        # spaces in attr was by mistake
        return attr.replace(" ", "_")
    elif attr == "pressure_state":
        return "pressure"
    elif attr == "occupancy_distance":
        return "distance"
    return attr


def remove_device(hass: HomeAssistant, device: XDevice):
    """Remove hass DeviceEntry and XDevice from all XGateway(s)."""
    registry = device_registry.async_get(hass)
    if device_entry := registry.async_get_device({(DOMAIN, device.uid)}):
        registry.async_remove_device(device_entry.id)

    for gw in device.gateways:
        gw.remove_device(device)
