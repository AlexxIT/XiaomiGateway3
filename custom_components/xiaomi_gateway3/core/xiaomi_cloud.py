"""
The base logic was taken from project https://github.com/squachen/micloud

I had to rewrite the code to work asynchronously and handle timeouts for
requests to the cloud.

MIT License

Copyright (c) 2020 Sammy Svensson

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import random
import string
import time

from aiohttp import ClientSession

_LOGGER = logging.getLogger(__name__)

SERVERS = ['cn', 'de', 'i2', 'ru', 'sg', 'us']
UA = "Android-7.1.1-1.0.0-ONEPLUS A3010-136-%s APP/xiaomi.smarthome APPV/62830"


class MiCloud:
    auth = None

    def __init__(self, session: ClientSession, servers: list = None):
        self.session = session
        self.servers = servers or ['cn']
        self.device_id = get_random_string(16)

    async def login(self, username: str, password: str):
        try:
            payload = await self._login_step1()
            data = await self._login_step2(username, password, payload)
            if not data['location']:
                return False

            token = await self._login_step3(data['location'])

            self.auth = {
                'user_id': data['userId'],
                'ssecurity': data['ssecurity'],
                'service_token': token
            }

            return True

        except Exception as e:
            _LOGGER.exception(f"Can't login to Mi Cloud: {e}")
            return False

    async def _login_step1(self):
        r = await self.session.get(
            'https://account.xiaomi.com/pass/serviceLogin',
            cookies={'sdkVersion': '3.8.6', 'deviceId': self.device_id},
            headers={'User-Agent': UA % self.device_id},
            params={'sid': 'xiaomiio', '_json': 'true'})
        raw = await r.read()
        _LOGGER.debug(f"MiCloud step1")
        resp: dict = json.loads(raw[11:])
        return {k: v for k, v in resp.items()
                if k in ('sid', 'qs', 'callback', '_sign')}

    async def _login_step2(self, username: str, password: str, payload: dict):
        payload['user'] = username
        payload['hash'] = hashlib.md5(password.encode()).hexdigest().upper()

        r = await self.session.post(
            'https://account.xiaomi.com/pass/serviceLoginAuth2',
            cookies={'sdkVersion': '3.8.6', 'deviceId': self.device_id},
            data=payload,
            headers={'User-Agent': UA % self.device_id},
            params={'_json': 'true'})
        raw = await r.read()
        _LOGGER.debug(f"MiCloud step2")
        resp = json.loads(raw[11:])
        return resp

    async def _login_step3(self, location):
        r = await self.session.get(location, headers={'User-Agent': UA})
        service_token = r.cookies['serviceToken'].value
        _LOGGER.debug(f"MiCloud step3")
        return service_token

    async def get_devices(self):
        payload = {'getVirtualModel': False, 'getHuamiDevices': 0}

        total = []
        for server in self.servers:
            resp = await self.request(server, '/home/device_list', payload)
            if resp is None:
                return None
            total += resp['list']
        return total

    async def get_rooms(self):
        payload = {'fg': True, 'fetch_share': True, 'limit': 300}

        total = []
        for server in self.servers:
            resp = await self.request(server, '/v2/homeroom/gethome', payload)
            if resp is None:
                return None
            for home in resp['homelist']:
                total += home['roomlist']
        return total

    async def get_bindkey(self, did: str):
        payload = {'did': did, 'pdid': 1}
        for server in self.servers:
            resp = await self.request(server, '/v2/device/blt_get_beaconkey',
                                      payload)
            if resp:
                return resp['beaconkey']
        return None

    async def request(self, server: str, url: str, payload: dict):
        assert server in SERVERS, "Wrong server: " + server
        baseurl = 'https://api.io.mi.com/app' if server == 'cn' \
            else f"https://{server}.api.io.mi.com/app"

        data = json.dumps(payload, separators=(',', ':'))

        nonce = gen_nonce()
        signed_nonce = gen_signed_nonce(self.auth['ssecurity'], nonce)
        signature = gen_signature(url, signed_nonce, nonce, data)

        try:
            r = await self.session.post(baseurl + url, cookies={
                'userId': self.auth['user_id'],
                'serviceToken': self.auth['service_token'],
                'locale': 'en_US'
            }, headers={
                'User-Agent': UA,
                'x-xiaomi-protocal-flag-cli': 'PROTOCAL-HTTP2'
            }, data={
                'signature': signature,
                '_nonce': nonce,
                'data': data
            }, timeout=10)

            resp = await r.json(content_type=None)
            # _LOGGER.debug(f"Response from MIoT API {url}: {resp}")
            assert resp['code'] == 0, resp
            return resp['result']

        except asyncio.TimeoutError:
            _LOGGER.error(f"Timeout while requesting MIoT api {url}")
        except:
            _LOGGER.exception(f"Can't request MIoT API {url}")

        return None


def get_random_string(length: int):
    seq = string.ascii_uppercase + string.digits
    return ''.join((random.choice(seq) for _ in range(length)))


def gen_nonce() -> str:
    """Time based nonce."""
    nonce = os.urandom(8) + int(time.time() / 60).to_bytes(4, 'big')
    return base64.b64encode(nonce).decode()


def gen_signed_nonce(ssecret: str, nonce: str) -> str:
    """Nonce signed with ssecret."""
    m = hashlib.sha256()
    m.update(base64.b64decode(ssecret))
    m.update(base64.b64decode(nonce))
    return base64.b64encode(m.digest()).decode()


def gen_signature(url: str, signed_nonce: str, nonce: str, data: str) -> str:
    """Request signature based on url, signed_nonce, nonce and data."""
    sign = '&'.join([url, signed_nonce, nonce, 'data=' + data])
    signature = hmac.new(key=base64.b64decode(signed_nonce),
                         msg=sign.encode(),
                         digestmod=hashlib.sha256).digest()
    return base64.b64encode(signature).decode()
