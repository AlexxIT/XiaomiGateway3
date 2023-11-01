import asyncio
import base64
import hashlib
import hmac
import logging
import random
import socket
import string
from typing import Optional

from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from . import shell
from .const import DOMAIN
from .converters import STAT_GLOBALS
from .device import XDevice
from .gateway import XGateway
from .gateway.lumi import LumiGateway
from .mini_miio import AsyncMiIO
from .xiaomi_cloud import MiCloud

SUPPORTED_MODELS = (
    "lumi.gateway.mgl03",
    "lumi.gateway.aqcn02",
    "lumi.gateway.aqcn03",
    "lumi.gateway.mcn001",
    "lumi.gateway.mgl001",
)

_LOGGER = logging.getLogger(__name__)


@callback
def remove_device(hass: HomeAssistant, device: XDevice):
    """Remove device by did from Hass"""
    registry = dr.async_get(hass)
    device = registry.async_get_device({(DOMAIN, device.unique_id)}, None)
    if device:
        registry.async_remove_device(device.id)


@callback
def remove_stats(hass: HomeAssistant, entry_id: str):
    suffix = tuple(STAT_GLOBALS.keys())
    registry = er.async_get(hass)
    remove = [
        entity.entity_id
        for entity in list(registry.entities.values())
        if (entity.config_entry_id == entry_id and entity.unique_id.endswith(suffix))
    ]
    for entity_id in remove:
        registry.async_remove(entity_id)


async def remove_zigbee(unique_id: str):
    try:
        device: XDevice = next(
            d for d in XGateway.devices.values() if d.unique_id == unique_id
        )
    except StopIteration:
        return
    # delete device from all gateways
    for gw in device.gateways:
        payload = gw.device.encode({"remove_did": device.did})
        if isinstance(gw, LumiGateway):
            await gw.lumi_send(gw.device, payload)


@callback
def update_device_info(hass: HomeAssistant, did: str, **kwargs):
    # lumi.1234567890 => 0x1234567890
    mac = "0x" + did[5:]
    registry = dr.async_get(hass)
    device = registry.async_get_device({("xiaomi_gateway3", mac)}, None)
    if device:
        registry.async_update_device(device.id, **kwargs)


async def load_devices(hass: HomeAssistant, yaml_devices: dict):
    # 1. Load devices settings from YAML
    if yaml_devices:
        for k, v in yaml_devices.items():
            # AA:BB:CC:DD:EE:FF => aabbccddeeff
            k = k.replace(":", "").lower()
            XGateway.defaults[k] = v

    # 2. Load unique_id from entity registry (backward support old format)
    registry = er.async_get(hass)
    for entity in list(registry.entities.values()):
        if entity.platform != DOMAIN:
            continue

        # split mac and attr in unique id
        legacy_id, attr = entity.unique_id.split("_", 1)
        if legacy_id.startswith("0x"):
            # add leading zeroes to zigbee mac
            mac = f"0x{legacy_id[2:]:>016s}"
        elif len(legacy_id) == 12:
            # make mac lowercase (old Mesh devices)
            mac = legacy_id.lower()
        else:
            mac = legacy_id

        device = XGateway.defaults.setdefault(mac, {})
        device.setdefault("unique_id", legacy_id)
        device.setdefault("restore_entities", []).append(attr)

    # 3. Load devices data from .storage
    store = Store(hass, 1, f"{DOMAIN}/devices.json")
    devices = await store.async_load()
    if devices:
        for k, v in devices.items():
            XGateway.defaults.setdefault(k, {}).update(v)

    # noinspection PyUnusedLocal
    async def stop(*args):
        # save devices data to .storage
        data = {
            d.mac: {"decode_ts": d.decode_ts}
            for d in XGateway.devices.values()
            if d.decode_ts
        }
        await store.async_save(data)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop)


def migrate_options(data):
    data = dict(data)
    options = {k: data.pop(k) for k in ("ble", "zha") if k in data}
    return {"data": data, "options": options}


def miio_password(did: str, mac: str, key: str) -> str:
    secret = hashlib.sha256(f"{did}{mac}{key}".encode()).hexdigest()
    dig = hmac.new(secret.encode(), msg=key.encode(), digestmod=hashlib.sha256).digest()
    return base64.b64encode(dig)[-16:].decode()


async def check_port(host: str, port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        ok = await asyncio.get_event_loop().run_in_executor(
            None, s.connect_ex, (host, port)
        )
        return ok == 0
    finally:
        s.close()


# universal command for open telnet on all models
TELNET_CMD = "passwd -d $USER; riu_w 101e 53 3012 || echo enable > /sys/class/tty/tty/enable; telnetd"
# firmware with support telnet ONLY with key
TELNET_KEY = {
    "lumi.gateway.mgl03": "1.5.5",
    "lumi.gateway.aqcn02": "4.0.4",
    "lumi.gateway.aqcn03": "4.0.4",
    "lumi.gateway.mcn001": "1.0.7",
    "lumi.gateway.mgl001": "1.0.7",
}


async def enable_telnet(miio: AsyncMiIO, key: str = None) -> dict:
    # Strategy:
    # 1. Get miio info
    # 2. Send common open telnet cmd if we can't get miio info
    # 3. Send different telnet cmd based on gateway model and firmware
    # 4. Return miio info and response on open telnet cmd
    method = None
    miio_info = await miio.info()

    if miio_info and "model" in miio_info and "fw_ver" in miio_info:
        if miio_info["model"] == "lumi.gateway.mgl03" and miio_info["fw_ver"] < "1.4.7":
            method = "enable_telnet_service"
        elif miio_info["fw_ver"] < TELNET_KEY.get(miio_info["model"], "999"):
            method = "set_ip_info"
        elif key:
            method = "system_command"
    else:
        # some universal cmd for all gateways
        method = "set_ip_info"

    if method == "set_ip_info":
        params = {"ssid": '""', "pswd": "1; " + TELNET_CMD}
    elif method == "system_command":
        params = {
            "password": miio_password(miio.device_id, miio_info["mac"], key),
            "command": TELNET_CMD,
        }
    else:
        params = None

    if method:
        res = await miio.send(method, params, tries=1)
        if miio_info and res:
            miio_info["result"] = res.get("result")

    return miio_info


async def gateway_info(host: str, token: str = None, key: str = None) -> Optional[dict]:
    # Strategy:
    # 1. Check open telnet and return host, did, token, key
    # 2. Try to enable telnet using host, token and (optionaly) key
    # 3. Check open telnet again
    # 4. Return error
    try:
        async with shell.Session(host) as sh:
            if sh.model:
                info = await sh.get_miio_info()
                return {"host": host, **info}
    except Exception:
        pass

    if not token:
        return None

    # try to enable telnet and return miio info
    miio = AsyncMiIO(host, token)
    miio_info = await enable_telnet(miio, key)

    # waiting for telnet to start
    await asyncio.sleep(1)

    # call with empty token so only telnet will check
    if info := await gateway_info(host):
        return info

    # if info is None - devise doesn't answer on pings
    if miio_info is None:
        return {"error": "cant_connect"}

    # if empty info - device works but not answer on commands
    if not miio_info:
        return {"error": "wrong_token"}

    # check if right model
    if miio_info["model"] not in SUPPORTED_MODELS:
        return {"error": "wrong_model"}

    return {"error": "wrong_telnet"}


async def store_gateway_key(hass: HomeAssistant, info: dict):
    did = info.get("did")
    if not did or not info.get("key"):
        _LOGGER.error(f"can't store gateway key: {info}")
        return

    store = Store(hass, 1, f"{DOMAIN}/keys.json")
    data = await store.async_load() or {}

    if data.get(did) == info:
        _LOGGER.debug(f"gateway key already in storage: {info}")
        return

    data[did] = info

    await store.async_save(data)


async def get_lan_key(host: str, token: str):
    device = AsyncMiIO(host, token)
    resp = await device.send("get_lumi_dpf_aes_key")
    if not resp:
        return "Can't connect to gateway"
    if "result" not in resp:
        return f"Wrong response: {resp}"
    resp = resp["result"]
    if len(resp[0]) == 16:
        return resp[0]
    key = "".join(
        random.choice(string.ascii_lowercase + string.digits) for _ in range(16)
    )
    resp = await device.send("set_lumi_dpf_aes_key", [key])
    if resp.get("result") == ["ok"]:
        return key
    return "Can't update gateway key"


async def get_room_mapping(cloud: MiCloud, host: str, token: str):
    try:
        device = AsyncMiIO(host, token)
        local_rooms = await device.send("get_room_mapping")
        cloud_rooms = await cloud.get_rooms()
        result = ""
        for local_id, cloud_id in local_rooms["result"]:
            cloud_name = next(
                (p["name"] for p in cloud_rooms if p["id"] == cloud_id), "-"
            )
            result += f"\n- {local_id}: {cloud_name}"
        return result

    except Exception:
        return "Can't get from cloud"


async def get_bindkey(cloud: MiCloud, did: str):
    bindkey = await cloud.get_bindkey(did)
    if bindkey is None:
        return "Can't get from cloud"
    # if bindkey.endswith('FFFFFFFF'):
    #     return "Not needed"
    return bindkey


async def enable_bslamp2_lan(host: str, token: str):
    device = AsyncMiIO(host, token)
    resp = await device.send("get_prop", ["lan_ctrl"])
    if not resp:
        return "Can't connect to lamp"
    if resp.get("result") == ["1"]:
        return "Already enabled"
    resp = await device.send("set_ps", ["cfg_lan_ctrl", "1"])
    if resp.get("result") == ["ok"]:
        return "Enabled"
    return "Can't enable LAN"


async def get_ble_remotes(host: str, token: str):
    device = AsyncMiIO(host, token)
    resp = await device.send("ble_dbg_tbl_dump", {"table": "evtRuleTbl"})
    if not resp:
        return "Can't connect to lamp"
    if "result" not in resp:
        return f"Wrong response"
    return "\n".join(
        [f"{p['beaconkey']} ({format_mac(p['mac'])})" for p in resp["result"]]
    )


def format_mac(s: str) -> str:
    return f"{s[10:]}:{s[8:10]}:{s[6:8]}:{s[4:6]}:{s[2:4]}:{s[:2]}".upper()


async def get_ota_link(hass: HomeAssistant, device: "XDevice"):
    url = "https://raw.githubusercontent.com/Koenkk/zigbee-OTA/master/"

    # Xiaomi Plug should be updated to fw 30 before updating to latest fw
    if device.model == "lumi.plug" and 0 < device.fw_ver < 30:
        # waiting pull request https://github.com/Koenkk/zigbee-OTA/pull/49
        return (
            url.replace("Koenkk", "AlexxIT")
            + "images/Xiaomi/LM15_SP_mi_V1.3.30_20170929_v30_withCRC.20180514181348.ota"
        )

    r = await async_get_clientsession(hass).get(url + "index.json")
    items = await r.json(content_type=None)
    for item in items:
        if item.get("modelId") == device.model:
            return url + item["path"]

    return None


async def run_zigbee_ota(
    hass: HomeAssistant, gateway: "XGateway", device: "XDevice"
) -> Optional[bool]:
    url = await get_ota_link(hass, device)
    if url:
        gateway.debug_device(device, "update", url)
        resp = await gateway.miio_send(
            "miIO.subdev_ota", {"did": device.did, "subdev_url": url}
        )
        if not resp or resp.get("result") != ["ok"]:
            _LOGGER.error(f"Can't run update process: {resp}")
            return None
        return True
    else:
        return False
