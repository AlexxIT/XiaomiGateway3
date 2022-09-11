import asyncio
import json
import logging
import random
import string
from typing import Optional

import requests
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers import (
    device_registry as dr, entity_registry as er
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.requirements import async_process_requirements

from . import shell
from .const import DOMAIN
from .converters import STAT_GLOBALS
from .device import XDevice
from .ezsp import EzspUtils
from .gateway import XGateway
from .gateway.lumi import LumiGateway
from .mini_miio import AsyncMiIO
from .xiaomi_cloud import MiCloud

SUPPORTED_MODELS = (
    'lumi.gateway.mgl03', 'lumi.gateway.aqcn02', 'lumi.gateway.aqcn03', 'lumi.gateway.mcn001'
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
        if (entity.config_entry_id == entry_id and
            entity.unique_id.endswith(suffix))
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
    mac = '0x' + did[5:]
    registry = dr.async_get(hass)
    device = registry.async_get_device({('xiaomi_gateway3', mac)}, None)
    if device:
        registry.async_update_device(device.id, **kwargs)


async def load_devices(hass: HomeAssistant, yaml_devices: dict):
    # 1. Load devices settings from YAML
    if yaml_devices:
        for k, v in yaml_devices.items():
            # AA:BB:CC:DD:EE:FF => aabbccddeeff
            k = k.replace(':', '').lower()
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
    options = {k: data.pop(k) for k in ('ble', 'zha') if k in data}
    return {'data': data, 'options': options}


async def check_gateway(host: str, token: str, telnet_cmd: Optional[str]) \
        -> Optional[str]:
    # 1. try connect with telnet (custom firmware)?
    try:
        async with shell.Session(host) as session:
            sh = await session.login()
            if sh.model:
                # 1.1. check token with telnet
                return None if await sh.get_token() == token else 'wrong_token'
    except Exception:
        pass

    if not telnet_cmd:
        return 'cant_connect'

    # 2. try connect with miio
    miio = AsyncMiIO(host, token)
    info = await miio.info()

    # if info is None - devise doesn't answer on pings
    if info is None:
        return 'cant_connect'

    # if empty info - device works but not answer on commands
    if not info:
        return 'wrong_token'

    # 3. check if right model
    if info['model'] not in SUPPORTED_MODELS:
        return 'wrong_model'

    raw = json.loads(telnet_cmd)
    # fw 1.4.6_0043+ won't answer on cmd without cloud, don't check answer
    await miio.send(raw['method'], raw.get('params'))

    # waiting for telnet to start
    await asyncio.sleep(1)

    try:
        async with shell.Session(host) as session:
            sh = await session.login()
            if not sh.model:
                return 'wrong_telnet'
    except Exception:
        return None


async def get_lan_key(host: str, token: str):
    device = AsyncMiIO(host, token)
    resp = await device.send('get_lumi_dpf_aes_key')
    if not resp:
        return "Can't connect to gateway"
    if 'result' not in resp:
        return f"Wrong response: {resp}"
    resp = resp['result']
    if len(resp[0]) == 16:
        return resp[0]
    key = ''.join(random.choice(string.ascii_lowercase + string.digits)
                  for _ in range(16))
    resp = await device.send('set_lumi_dpf_aes_key', [key])
    if resp.get('result') == ['ok']:
        return key
    return "Can't update gateway key"


async def get_room_mapping(cloud: MiCloud, host: str, token: str):
    try:
        device = AsyncMiIO(host, token)
        local_rooms = await device.send('get_room_mapping')
        cloud_rooms = await cloud.get_rooms()
        result = ''
        for local_id, cloud_id in local_rooms['result']:
            cloud_name = next(
                (p['name'] for p in cloud_rooms if p['id'] == cloud_id), '-'
            )
            result += f"\n- {local_id}: {cloud_name}"
        return result

    except Exception:
        return "Can't get from cloud"


async def get_bindkey(cloud: MiCloud, did: str):
    bindkey = await cloud.get_bindkey(did)
    if bindkey is None:
        return "Can't get from cloud"
    if bindkey.endswith('FFFFFFFF'):
        return "Not needed"
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


NCP_URL = "https://master.dl.sourceforge.net/project/mgl03/zigbee/%s?viasf=1"


def flash_zigbee_firmware(host: str, ports: list, fw_url: str, fw_ver: str,
                          fw_port=0, force=False):
    """
    param host: gateway host
    param ports: one or multiple ports with different speeds, first port
        should be 115200
    param fw_url: url to firmware file
    param fw_ver: firmware version, checks before and after flash
    param fw_port: optional, port with firmware speed if it is not 115200
    param second_port: optional, second port if current firmware may have
        different speed
    param force: skip check firmware version before flash
    return: True if NCP firmware version equal to fw_ver
    """

    # we can flash NCP only in boot mode on speed 115200
    # but NCP can work on another speed, so we need to try both of them
    # work with 115200 on port 8115, and with 38400 on port 8038
    _LOGGER.debug(f"Try to update Zigbee NCP to version {fw_ver}")

    if isinstance(ports, int):
        ports = [ports]

    utils = EzspUtils()

    try:
        # try to find right speed from the list
        for port in ports:
            utils.connect(host, port)
            state = utils.state()
            if state:
                break
            utils.close()
        else:
            raise RuntimeError

        if state == "normal":
            if fw_ver in utils.version and not force:
                _LOGGER.debug("No need to flash")
                return True
            _LOGGER.debug(f"NCP state: {state}, version: {utils.version}")
            utils.launch_boot()
            state = utils.state()

        _LOGGER.debug(f"NCP state: {state}, version: {utils.version}")

        # should be in boot
        if state != "boot":
            return False

        r = requests.get(fw_url)
        assert r.status_code == 200, r.status_code

        assert utils.flash_and_close(r.content)

        utils.connect(host, ports[0])
        utils.reboot_and_close()

        utils.connect(host, fw_port or ports[0])
        state = utils.state()
        _LOGGER.debug(f"NCP state: {state}, version: {utils.version}")
        return fw_ver in utils.version

    except Exception as e:
        _LOGGER.debug(f"NCP flash error", exc_info=e)
        return False

    finally:
        utils.close()


async def update_zigbee_firmware(hass: HomeAssistant, host: str, custom: bool):
    """Update zigbee firmware for both ZHA and zigbee2mqtt modes"""
    await async_process_requirements(hass, DOMAIN, ['xmodem==0.4.6'])

    try:
        async with shell.Session(host) as session:
            sh = await session.login()
            assert await sh.run_zigbee_flash()
    except Exception as e:
        _LOGGER.error("Can't update zigbee firmware", exc_info=e)
        return False

    await asyncio.sleep(.5)

    args = [
        host, [8115, 8038], NCP_URL % 'mgl03_ncp_6_7_10_b38400_sw.gbl',
        'v6.7.10', 8038
    ] if custom else [
        host, [8115, 8038], NCP_URL % 'ncp-uart-sw_mgl03_6_6_2_stock.gbl',
        'v6.6.2', 8115
    ]

    for _ in range(3):
        if await hass.async_add_executor_job(flash_zigbee_firmware, *args):
            return True
    return False


async def get_ota_link(hass: HomeAssistant, device: "XDevice"):
    url = "https://raw.githubusercontent.com/Koenkk/zigbee-OTA/master/"

    # Xiaomi Plug should be updated to fw 30 before updating to latest fw
    if device.model == 'lumi.plug' and 0 < device.fw_ver < 30:
        # waiting pull request https://github.com/Koenkk/zigbee-OTA/pull/49
        return url.replace('Koenkk', 'AlexxIT') + \
               'images/Xiaomi/LM15_SP_mi_V1.3.30_20170929_v30_withCRC.20180514181348.ota'

    r = await async_get_clientsession(hass).get(url + "index.json")
    items = await r.json(content_type=None)
    for item in items:
        if item.get('modelId') == device.model:
            return url + item['path']

    return None


async def run_zigbee_ota(
        hass: HomeAssistant, gateway: "XGateway", device: "XDevice"
) -> Optional[bool]:
    url = await get_ota_link(hass, device)
    if url:
        gateway.debug_device(device, "update", url)
        resp = await gateway.miio.send('miIO.subdev_ota', {
            'did': device.did,
            'subdev_url': url
        })
        if not resp or resp.get('result') != ['ok']:
            _LOGGER.error(f"Can't run update process: {resp}")
            return None
        return True
    else:
        return False
