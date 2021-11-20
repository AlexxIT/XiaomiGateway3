import asyncio
import json
import logging
import random
import re
import string
import uuid
from datetime import datetime
from functools import lru_cache
from typing import List, Optional, TYPE_CHECKING

import requests
from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceRegistry
from homeassistant.helpers.entity_registry import EntityRegistry
from homeassistant.helpers.template import Template
from homeassistant.requirements import async_process_requirements

from . import shell
from .ezsp import EzspUtils
from .mini_miio import AsyncMiIO
from .xiaomi_cloud import MiCloud

if TYPE_CHECKING:
    from .device import XDevice
    from .gateway import XGateway

DOMAIN = 'xiaomi_gateway3'
TITLE = "Xiaomi Gateway 3"

SUPPORTED_MODELS = ('lumi.gateway.mgl03', 'lumi.gateway.aqcn02')

_LOGGER = logging.getLogger(__name__)


@callback
def remove_device(hass: HomeAssistant, did: str):
    """Remove device by did from Hass"""
    assert did.startswith("lumi.")
    mac = f"0x{did[5:]:>016s}"
    registry: DeviceRegistry = hass.data['device_registry']
    device = registry.async_get_device({(DOMAIN, mac)}, None)
    if device:
        registry.async_remove_device(device.id)


@callback
def update_device_info(hass: HomeAssistant, did: str, **kwargs):
    # lumi.1234567890 => 0x1234567890
    mac = '0x' + did[5:]
    registry: DeviceRegistry = hass.data['device_registry']
    device = registry.async_get_device({('xiaomi_gateway3', mac)}, None)
    if device:
        registry.async_update_device(device.id, **kwargs)


@callback
def async_migrate_unique_id(hass: HomeAssistant):
    """New unique_id format:
    - zigbee 18 symb mac with leading `0x`, lowercase
    - gateway, ble, mesh - 12 symb mac, lowercase
    - mesh groups - 14 symb hex numb, lowercase
    """
    replaces = {}

    dr: DeviceRegistry = hass.data["device_registry"]
    er: EntityRegistry = hass.data['entity_registry']
    for entity in list(er.entities.values()):
        if entity.platform != DOMAIN:
            continue

        # split mac and attr in unique id
        mac, attr = entity.unique_id.split("_", 1)

        # save original mac
        mac0 = mac

        # remove unnecessary gateway entities
        if attr in ("firmware lock", "pair"):
            er.async_remove(entity.entity_id)
            continue

        # get real mac for gateway entities
        if attr in ("alarm", "gateway"):
            device = dr.async_get(entity.device_id)
            for conn in device.connections:
                _, mac = conn
            mac = mac.replace(":", "")

        if mac.startswith("0x"):
            # add leading zeroes to zigbee mac
            mac = f"0x{mac[2:]:>016s}"
        elif len(mac) > 12 and attr == "light":
            # change attr for mesh group
            attr = "group"
        elif len(mac) == 12:
            # make mac lowercase (old Mesh devices)
            mac = mac.lower()

        if " " in attr:
            # remove space from attr name (some attrs problem)
            attr = attr.replace(" ", "_")

        new_id = f"{mac}_{attr}"
        # skip if nothing changed
        if entity.unique_id == new_id:
            continue

        # save replaces to fix device item
        replaces[mac0] = mac

        er.async_update_entity(entity.entity_id, new_unique_id=new_id)

    for device in list(dr.devices.values()):
        i = next((i for i in device.identifiers if i[0] == DOMAIN), None)
        if not i:
            continue

        # separate domain and mac
        _, mac = i

        # skip if nothing changed
        if mac not in replaces:
            continue

        # update device identifiers to new format
        dr.async_update_device(device.id, new_identifiers={
            (DOMAIN, replaces[mac])
        })


# new miio adds colors to logs
RE_JSON1 = re.compile(b'msg:(.+) length:([0-9]+) bytes')
RE_JSON2 = re.compile(b'{.+}')
EMPTY_RESPONSE = []


def decode_miio_json(raw: bytes, search: bytes) -> List[dict]:
    """There can be multiple concatenated json on one line. And sometimes the
    length does not match the message."""
    if search not in raw:
        return EMPTY_RESPONSE
    m = RE_JSON1.search(raw)
    if m:
        length = int(m[2])
        raw = m[1][:length]
    else:
        m = RE_JSON2.search(raw)
        raw = m[0]
    items = raw.replace(b'}{', b'}\n{').split(b'\n')
    return [json.loads(raw) for raw in items if search in raw]


def decode_miio_offline(raw: bytes) -> Optional[dict]:
    if b"_internal.record_offline" not in raw:
        return None
    _, raw = raw.split(b":, ", 1)
    return json.loads(raw)


def migrate_options(data):
    data = dict(data)
    options = {k: data.pop(k) for k in ('ble', 'zha') if k in data}
    return {'data': data, 'options': options}


async def check_gateway(host: str, token: str, telnet_cmd: Optional[str]) \
        -> Optional[str]:
    # 1. try connect with telnet (custom firmware)?
    sh: shell.TelnetShell = await shell.connect(host)
    try:
        if sh.model:
            # 1.1. check token with telnet
            return None if await sh.get_token() == token else 'wrong_token'

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

        sh = await shell.connect(host)
        if not sh.model:
            return 'wrong_telnet'

        return None

    finally:
        await sh.close()


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

    except:
        return "Can't get from cloud"


async def get_bindkey(cloud: MiCloud, did: str):
    bindkey = await cloud.get_bindkey(did)
    if bindkey is None:
        return "Can't get from cloud"
    if bindkey.endswith('FFFFFFFF'):
        return "Not needed"
    return bindkey


def reverse_mac(s: str):
    return f"{s[10:]}{s[8:10]}{s[6:8]}{s[4:6]}{s[2:4]}{s[:2]}"


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

    sh: shell.ShellGw3 = await shell.connect(host)
    try:
        assert await sh.run_zigbee_flash()
    except:
        return False
    finally:
        await sh.close()

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


@lru_cache(maxsize=0)
def attributes_template(hass: HomeAssistant) -> Template:
    template = hass.data[DOMAIN]['attributes_template']
    template.hass = hass
    return template


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

    # z2m project desided to remove Aqara Relay OTA, but gw3 users have no
    # problem with this firmware
    # https://github.com/Koenkk/zigbee2mqtt/issues/7112
    if device.model == 'lumi.relay.c2acn01':
        return url + 'images/Xiaomi/20201218113852_lumi.relay.c2acn01_0.0.0_0046_20201216_6BB0FD.ota'

    return None


async def run_zigbee_ota(
        hass: HomeAssistant, gateway: "XGateway", device: "XDevice"
):
    url = await get_ota_link(hass, device)
    if url:
        gateway.debug_device(device, "update", url)
        resp = await gateway.miio.send('miIO.subdev_ota', {
            'did': device.did,
            'subdev_url': url
        })
        if not resp or resp.get('result') != ['ok']:
            _LOGGER.error(f"Can't run update process: {resp}")
            return "Can't run update"
        return "Update started"
    else:
        return "No firmware"


NOTIFY_TEXT = '<a href="%s?r=10" target="_blank">Open Log<a>'
HTML = (f'<!DOCTYPE html><html><head><title>{TITLE}</title>'
        '<meta http-equiv="refresh" content="%s"></head>'
        '<body><pre>%s</pre></body></html>')


class XiaomiGateway3Debug(logging.Handler, HomeAssistantView):
    name = "xiaomi_debug"
    requires_auth = False

    # https://waymoot.org/home/python_string/
    text = []

    def __init__(self, hass: HomeAssistant):
        super().__init__()

        # random url because without authorization!!!
        self.url = f"/{uuid.uuid4()}"

        hass.http.register_view(self)
        hass.components.persistent_notification.async_create(
            NOTIFY_TEXT % self.url, title=TITLE)

    def handle(self, rec: logging.LogRecord) -> None:
        dt = datetime.fromtimestamp(rec.created).strftime("%Y-%m-%d %H:%M:%S")
        module = 'main' if rec.module == '__init__' else rec.module
        self.text.append(f"{dt}  {rec.levelname:7}  {module:12}  {rec.msg}")

    async def get(self, request: web.Request):
        try:
            if 'c' in request.query:
                self.text.clear()

            if 'q' in request.query or 't' in request.query:
                lines = self.text

                if 'q' in request.query:
                    reg = re.compile(fr"({request.query['q']})", re.IGNORECASE)
                    lines = [p for p in self.text if reg.search(p)]

                if 't' in request.query:
                    tail = int(request.query['t'])
                    lines = lines[-tail:]

                body = '\n'.join(lines)
            else:
                body = '\n'.join(self.text[:10000])

            reload = request.query.get('r', '')
            return web.Response(text=HTML % (reload, body),
                                content_type="text/html")

        except:
            return web.Response(status=500)
