import json
import logging
import random
import re
import string
import uuid
from datetime import datetime
from typing import List, Optional

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.device_registry import DeviceRegistry
from homeassistant.helpers.entity_registry import EntityRegistry
from homeassistant.helpers.typing import HomeAssistantType

from .mini_miio import SyncmiIO
from .shell import TelnetShell
from .xiaomi_cloud import MiCloud

DOMAIN = 'xiaomi_gateway3'


def remove_device(hass: HomeAssistantType, did: str):
    """Remove device by did from Hass"""
    # lumi.1234567890 => 0x1234567890
    mac = '0x' + did[5:]
    registry: DeviceRegistry = hass.data['device_registry']
    device = registry.async_get_device({('xiaomi_gateway3', mac)}, None)
    if device:
        registry.async_remove_device(device.id)


def migrate_unique_id(hass: HomeAssistantType):
    """New unique_id format: `mac_attr`, no leading `0x`, spaces and uppercase.
    """
    old_id = re.compile('(^0x|[ A-F])')

    registry: EntityRegistry = hass.data['entity_registry']
    for entity in registry.entities.values():
        if entity.platform != DOMAIN or not old_id.search(entity.unique_id):
            continue

        uid = entity.unique_id.replace('0x', '').replace(' ', '_').lower()
        registry.async_update_entity(entity.entity_id, new_unique_id=uid)


# new miio adds colors to logs
RE_JSON1 = re.compile(b'msg:(.+) length:([0-9]+) bytes')
RE_JSON2 = re.compile(b'{.+}')


def extract_jsons(raw) -> List[bytes]:
    """There can be multiple concatenated json on one line. And sometimes the
    length does not match the message."""
    m = RE_JSON1.search(raw)
    if m:
        length = int(m[2])
        raw = m[1][:length]
    else:
        m = RE_JSON2.search(raw)
        raw = m[0]
    return raw.replace(b'}{', b'}\n{').split(b'\n')


def migrate_options(data):
    data = dict(data)
    options = {k: data.pop(k) for k in ('ble', 'zha') if k in data}
    return {'data': data, 'options': options}


TITLE = "Xiaomi Gateway 3 Debug"
NOTIFY_TEXT = '<a href="%s?r=10" target="_blank">Open Log<a>'
HTML = (f'<!DOCTYPE html><html><head><title>{TITLE}</title>'
        '<meta http-equiv="refresh" content="%s"></head>'
        '<body><pre>%s</pre></body></html>')


class XiaomiGateway3Debug(logging.Handler, HomeAssistantView):
    name = "xiaomi_debug"
    requires_auth = False

    # https://waymoot.org/home/python_string/
    text = []

    def __init__(self, hass: HomeAssistantType):
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
