import base64
import hashlib
import json
import logging
import os
import random
import string
import time
from typing import TypedDict

import aiohttp
from aiohttp import ClientSession
from cryptography.hazmat.primitives import ciphers
from cryptography.hazmat.decrepit.ciphers import algorithms

_LOGGER = logging.getLogger(__name__)

SDK_VERSION = "4.2.29"
BASE = {
    "cn": "https://api.io.mi.com/app",
    "de": "https://de.api.io.mi.com/app",
    "i2": "https://i2.api.io.mi.com/app",
    "ru": "https://ru.api.io.mi.com/app",
    "sg": "https://sg.api.io.mi.com/app",
    "us": "https://us.api.io.mi.com/app",
}

FLAG_PHONE = 4
FLAG_EMAIL = 8


class AuthResult(TypedDict, total=False):
    ok: bool
    captcha: bytes | None
    verify: str | None  # phone or email address
    token: str | None
    exception: Exception | None


class MiCloud:
    # All instance variables are initialized in __init__ to completely avoid
    # multi-account cross-contamination caused by shared class variables.
    def __init__(
        self, session: ClientSession = None, servers: list = None, sid: str = None,
        timeout: int = 30
    ):
        self.session = session or ClientSession(timeout=aiohttp.ClientTimeout(total=timeout))
        self.servers = servers or ["cn"]
        self.sid = sid or "xiaomiio"
        self.device_id = get_random_string(16)

        self.auth = None          # dict or None
        self.cookies = None       # dict or None
        self.ssecurity = None     # bytes or None
        self.devices = None       # list or None

    @property
    def ok(self):
        return self.cookies is not None and self.ssecurity is not None

    async def close(self):
        return await self.session.close()

    async def login(self, username: str, password: str, **kwargs) -> AuthResult:
        try:
            res1 = await self._service_login(username, password, **kwargs)
            if captcha_url := res1.get("captchaUrl"):
                data = await self._get_captcha_url(captcha_url)
                self.auth = {
                    "username": username,
                    "password": password,
                    "ick": data["ick"],
                }
                return {"ok": False, "captcha": data["image"]}
            if notification_url := res1.get("notificationUrl"):
                return await self._get_notification_url(notification_url)
            return await self._get_credentials(res1)
        except Exception as e:
            return {"ok": False, "exception": e}

    async def login_password(self, username: str, password: str) -> AuthResult:
        try:
            res1 = await self._service_login(username, password)
            if res1.get("code") != 0:
                raise Exception(f"Service login failed: {res1}")
            return await self._get_credentials(res1)
        except Exception as e:
            return {"ok": False, "exception": e}

    async def login_token(self, token: str) -> AuthResult:
        try:
            user_id, pass_token = token.split(":", 1)
            r = await self.session.get(
                "https://account.xiaomi.com/pass/serviceLogin",
                cookies={"userId": user_id, "passToken": pass_token},
                params={"_json": "true", "sid": self.sid},
            )
            res1 = parse_auth_response(await r.read())
            if res1.get("code") != 0:
                raise Exception(f"Token login failed: {res1}")
            return await self._get_credentials(res1)
        except Exception as e:
            return {"ok": False, "exception": e}

    async def login_captcha(self, code: str) -> AuthResult:
        if self.auth is None:
            return {"ok": False, "exception": Exception("Auth info missing, please call login() first")}

        # Case 1: Secondary verification captcha (has flag and identity_session)
        if "flag" in self.auth and "identity_session" in self.auth:
            return await self._send_ticket(
                self.auth["flag"], self.auth["identity_session"], code
            )

        # Case 2: Initial login graphical captcha (has username and password)
        if "username" in self.auth and "password" in self.auth:
            return await self.login(
                self.auth["username"], self.auth["password"], captcha_code=code
            )

        return {"ok": False, "exception": Exception("Invalid auth state for captcha")}

    async def login_verify(self, ticket: str) -> AuthResult:
        try:
            if self.auth is None or "flag" not in self.auth or "identity_session" not in self.auth:
                raise Exception("Auth info missing, please call login() first")
            
            flag = self.auth["flag"]
            key = "Phone" if flag == FLAG_PHONE else "Email"
            r = await self.session.post(
                f"https://account.xiaomi.com/identity/auth/verify{key}",
                cookies={"identity_session": self.auth["identity_session"]},
                params={"_flag": flag, "ticket": ticket, "trust": "false", "_json": "true"},
            )
            res1 = parse_auth_response(await r.read())
            if res1.get("code") != 0:
                raise Exception(f"Verify failed: {res1}")
            return await self._get_credentials(res1)
        except Exception as e:
            return {"ok": False, "exception": e}

    async def _service_login(
        self, username: str, password: str, captcha_code: str = None
    ) -> dict:
        r = await self.session.get(
            "https://account.xiaomi.com/pass/serviceLogin",
            cookies={"sdkVersion": SDK_VERSION, "deviceId": self.device_id},
            params={"_json": "true", "sid": self.sid},
        )
        res1 = parse_auth_response(await r.read())
        cookies = {"sdkVersion": SDK_VERSION, "deviceId": self.device_id}
        data = {
            "_json": "true",
            "sid": res1["sid"],
            "callback": res1["callback"],
            "_sign": res1["_sign"],
            "qs": res1["qs"],
            "user": username,
            "hash": hashlib.md5(password.encode()).hexdigest().upper(),
        }
        if captcha_code:
            if self.auth is None or "ick" not in self.auth:
                raise Exception("Missing ick for captcha")
            cookies["ick"] = self.auth["ick"]
            data["captCode"] = captcha_code

        r = await self.session.post(
            "https://account.xiaomi.com/pass/serviceLoginAuth2",
            cookies=cookies,
            data=data,
        )
        return parse_auth_response(await r.read())

    async def _get_captcha_url(self, captcha_url: str) -> dict:
        r = await self.session.get("https://account.xiaomi.com" + captcha_url)
        body = await r.read()
        return {"image": body, "ick": r.cookies["ick"]}

    async def _get_credentials(self, data: dict) -> AuthResult:
        if not data.get("location"):
            raise Exception(f"Missing location in credentials: {data}")

        r1 = await self.session.get(data["location"])
        if await r1.read() != b"ok":
            raise Exception("Location request did not return 'ok'")

        self.cookies = {k: v.value for k, v in r1.cookies.items()}
        for r2 in r1.history:
            data.update({k: v.value for k, v in r2.cookies.items()})
            if ext := r2.headers.get("extension-pragma"):
                data.update(json.loads(ext))

        if "ssecurity" not in data:
            raise Exception(f"Missing ssecurity in credentials: {data}")
        self.ssecurity = base64.b64decode(data["ssecurity"])

        # 修复了原 PR 中 `or` 可能导致的逻辑漏洞（当 userId 为 0 或空字符串时）
        user_id = data.get("userId", data.get("cUserId"))
        pass_token = data.get("passToken")
        
        if not user_id or not pass_token:
            raise Exception(f"Missing userId or passToken in credentials: {data}")

        return {"ok": True, "token": f"{user_id}:{pass_token}"}

    async def _get_notification_url(self, notification_url: str) -> AuthResult:
        if "/fe/service/identity/authStart" not in notification_url:
            raise Exception(f"Invalid notification URL: {notification_url}")

        notification_url = notification_url.replace(
            "/fe/service/identity/authStart", "/identity/list"
        )
        r = await self.session.get(notification_url)
        res1 = parse_auth_response(await r.read())
        if res1.get("code") != 2:
            raise Exception(f"Get notification failed: {res1}")

        flag = res1["flag"]
        if flag not in (FLAG_EMAIL, FLAG_PHONE):
            raise Exception(f"Invalid flag: {res1}")

        return await self._send_ticket(flag, r.cookies["identity_session"])

    async def _send_ticket(
        self, flag: int, identity_session, captcha_code: str = None
    ) -> AuthResult:
        try:
            key = "Phone" if flag == FLAG_PHONE else "Email"
            r = await self.session.get(
                f"https://account.xiaomi.com/identity/auth/verify{key}",
                cookies={"identity_session": identity_session},
                params={"_flag": flag, "_json": "true"},
            )
            res1 = parse_auth_response(await r.read())
            if res1.get("code") != 0:
                raise Exception(f"Verify ticket failed: {res1}")

            if captcha_code:
                if self.auth is None or "ick" not in self.auth:
                    raise Exception("Missing ick for captcha")
                cookies = {"identity_session": identity_session, "ick": self.auth["ick"]}
                data = {"retry": 0, "icode": captcha_code, "_json": "true"}
            else:
                cookies = {"identity_session": identity_session}
                data = {"retry": 0, "icode": "", "_json": "true"}

            r = await self.session.post(
                f"https://account.xiaomi.com/identity/auth/send{key}Ticket",
                cookies=cookies,
                data=data,
            )
            res2 = parse_auth_response(await r.read())
            self.auth = {"flag": flag, "identity_session": identity_session}

            if captcha_url := res2.get("captchaUrl"):
                data = await self._get_captcha_url(captcha_url)
                self.auth["ick"] = data["ick"]
                return {"ok": False, "captcha": data["image"]}

            if res2.get("code") != 0:
                raise Exception(f"Send ticket failed: {res2}")

            return {"ok": False, "verify": res1[f"masked{key}"]}
        except Exception as e:
            return {"ok": False, "exception": e}

    async def request(self, server: str, path: str, params: dict) -> dict:
        if not self.ok:
            raise RuntimeError("Cannot request: MiCloud is not logged in or ssecurity is missing.")

        form: dict[str, str] = {"data": json.dumps(params, separators=(",", ":"))}
        nonce: bytes = gen_nonce()
        signed_nonce: bytes = gen_signed_nonce(self.ssecurity, nonce)
        form["rc4_hash__"] = gen_signature_base64(path, form, signed_nonce)

        for k, v in form.items():
            ciphertext: bytes = crypt(signed_nonce, v.encode())
            form[k] = base64.b64encode(ciphertext).decode()

        form["signature"] = gen_signature_base64(path, form, signed_nonce)
        form["_nonce"] = base64.b64encode(nonce).decode()

        url = BASE.get(server, server) + path
        r = await self.session.post(url, cookies=self.cookies, data=form)
        if not r.ok:
            raise Exception(f"Request failed with status {r.status}")

        ciphertext: bytes = base64.b64decode(await r.read())
        plaintext: bytes = crypt(signed_nonce, ciphertext)
        res = json.loads(plaintext)
        if res.get("code") != 0:
            raise Exception(f"API error: {res}")

        return res["result"]

    async def get_devices(self) -> list[dict] | None:
        payload = {
            "getVirtualModel": True,
            "getHuamiDevices": 1,
            "get_split_device": False,
            "support_smart_home": True,
        }
        total = []
        for server in self.servers:
            try:
                resp = await self.request(server, "/v2/home/device_list_page", payload)
                if resp:
                    total.extend(resp["list"])
            except Exception as e:
                _LOGGER.warning("Failed to get devices from server %s: %s", server, e)
                continue
        return total if total else None

    async def get_rooms(self) -> list[dict] | None:
        payload = {"fg": True, "fetch_share": True, "limit": 300}
        total = []
        for server in self.servers:
            try:
                resp = await self.request(server, "/v2/homeroom/gethome", payload)
                if resp:
                    for home in resp.get("homelist", []):
                        total += home.get("roomlist", [])
            except Exception as e:
                _LOGGER.warning("Failed to get rooms from server %s: %s", server, e)
                continue
        return total if total else None

    async def get_bindkey(self, did: str) -> str | None:
        payload = {"did": did, "pdid": 1}
        for server in self.servers:
            try:
                resp = await self.request(server, "/v2/device/blt_get_beaconkey", payload)
                if resp:
                    beaconkey = resp.get("beaconkey")
                    if beaconkey:
                        return beaconkey
            except Exception as e:
                _LOGGER.warning("Failed to get bindkey from server %s: %s", server, e)
                continue
        return None


def parse_auth_response(body: bytes) -> dict:
    if not body.startswith(b"&&&START&&&"):
        raise Exception(f"Invalid auth response body: {body[:50]}")
    return json.loads(body[11:])


def get_random_string(length: int) -> str:
    seq = string.ascii_uppercase + string.digits
    return "".join(random.choice(seq) for _ in range(length))


def gen_nonce() -> bytes:
    return os.urandom(8) + int(time.time() / 60).to_bytes(4, "big")


def gen_signed_nonce(ssecurity: bytes, nonce: bytes) -> bytes:
    return hashlib.sha256(ssecurity + nonce).digest()


def gen_signature_base64(path: str, data: dict, signed_nonce: bytes) -> str:
    params = ["POST", path]
    for k, v in data.items():
        params.append(f"{k}={v}")
    params.append(base64.b64encode(signed_nonce).decode())
    signature = "&".join(params)
    signature = hashlib.sha1(signature.encode()).digest()
    return base64.b64encode(signature).decode()


def crypt(key: bytes, data: bytes) -> bytes:
    cipher = ciphers.Cipher(algorithms.ARC4(key), None)
    encryptor = cipher.encryptor()
    encryptor.update(bytes(1024))
    return encryptor.update(data)
