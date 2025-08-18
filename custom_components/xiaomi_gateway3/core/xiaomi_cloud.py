import base64
import hashlib
import json
import os
import random
import string
import time
from typing import TypedDict

from Crypto.Cipher import ARC4
from aiohttp import ClientSession

COOKIES = ("userId", "cUserId", "serviceToken")
SDK_VERSION = "4.2.29"
SERVERS = ["cn", "de", "i2", "ru", "sg", "us"]
SID = "xiaomiio"

FLAG_PHONE = 4
FLAG_EMAIL = 8


class AuthResult(TypedDict, total=False):
    ok: bool
    captcha: bytes | None
    verify: str | None  # phone or email address
    token: str | None
    exception: Exception | None


class MiCloud:
    auth: dict = None  # for login_captcha and login_email
    cookies: dict = None  # for request auth
    ssecurity: bytes = None  # for request encryption

    devices: list[dict] = None

    def __init__(self, session: ClientSession, servers: list = None):
        self.session = session
        self.servers = servers or ["cn"]
        self.device_id = get_random_string(16)

    @property
    def ok(self):
        return self.cookies is not None and self.ssecurity is not None

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

            res2 = await self._get_location(res1["location"])

            self.ssecurity = base64.b64decode(res1["ssecurity"])
            self.cookies = {k: res2[k] for k in COOKIES}

            return {"ok": True, "token": f"{res1['userId']}:{res1['passToken']}"}

        except Exception as e:
            return {"ok": False, "exception": e}

    async def login_token(self, token: str) -> AuthResult:
        try:
            user_id, pass_token = token.split(":", 1)

            r = await self.session.get(
                "https://account.xiaomi.com/pass/serviceLogin",
                cookies={"userId": user_id, "passToken": pass_token},
                params={"_json": "true", "sid": SID},
            )
            res1 = parse_auth_response(await r.read())

            res2 = await self._get_location(res1["location"])

            self.ssecurity = base64.b64decode(res1["ssecurity"])
            self.cookies = {k: res2[k] for k in COOKIES}

            return {"ok": True}

        except Exception as e:
            return {"ok": False, "exception": e}

    async def login_captcha(self, code: str) -> AuthResult:
        if "flag" in self.auth and "identity_session" in self.auth:
            return await self._send_ticket(
                self.auth["flag"], self.auth["identity_session"], code
            )

        return await self.login(
            self.auth["username"], self.auth["password"], captcha_code=code
        )

    async def login_verify(self, ticket: str) -> AuthResult:
        flag = self.auth["flag"]
        key = "Phone" if flag == FLAG_PHONE else "Email"

        r = await self.session.post(
            f"https://account.xiaomi.com/identity/auth/verify{key}",
            cookies={"identity_session": self.auth["identity_session"]},
            params={"_flag": flag, "ticket": ticket, "trust": "false", "_json": "true"},
        )
        res1 = parse_auth_response(await r.read())
        assert res1["code"] == 0, res1

        res2 = await self._get_location(res1["location"])

        self.ssecurity = base64.b64decode(res2["ssecurity"])
        self.cookies = {k: res2[k] for k in COOKIES}

        return {"ok": True, "token": f"{res2['userId']}:{res2['passToken']}"}

    async def _service_login(
        self, username: str, password: str, captcha_code: str = None
    ) -> dict:
        r = await self.session.get(
            "https://account.xiaomi.com/pass/serviceLogin",
            cookies={"sdkVersion": SDK_VERSION, "deviceId": self.device_id},
            params={"_json": "true", "sid": SID},
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
            cookies["ick"] = self.auth["ick"]
            data["captCode"] = captcha_code

        r = await self.session.post(
            "https://account.xiaomi.com/pass/serviceLoginAuth2",
            cookies=cookies,
            data=data,
        )
        return parse_auth_response(await r.read())

    async def _get_location(self, location: str) -> dict:
        r1 = await self.session.get(location)
        assert await r1.read() == b"ok"

        # this is useful for all steps
        response = {k: v.value for k, v in r1.cookies.items()}

        # this is useful for verify_email step
        for r2 in r1.history:
            response.update({k: v.value for k, v in r2.cookies.items()})
            if ext := r2.headers.get("extension-pragma"):
                response.update(json.loads(ext))

        return response

    async def _get_captcha_url(self, captcha_url: str) -> dict:
        r = await self.session.get("https://account.xiaomi.com" + captcha_url)
        body = await r.read()
        return {"image": body, "ick": r.cookies["ick"]}

    async def _get_notification_url(self, notification_url: str) -> AuthResult:
        assert "/identity/authStart" in notification_url, notification_url
        notification_url = notification_url.replace("authStart", "list")

        r = await self.session.get(notification_url)
        res1 = parse_auth_response(await r.read())
        assert res1["code"] == 2, res1

        flag = res1["flag"]
        assert flag in (FLAG_EMAIL, FLAG_PHONE), res1

        return await self._send_ticket(flag, r.cookies["identity_session"])

    async def _send_ticket(
        self, flag: int, identity_session, captcha_code: str = None
    ) -> AuthResult:
        key = "Phone" if flag == FLAG_PHONE else "Email"

        r = await self.session.get(
            f"https://account.xiaomi.com/identity/auth/verify{key}",
            cookies={"identity_session": identity_session},
            params={"_flag": flag, "_json": "true"},
        )
        res1 = parse_auth_response(await r.read())
        assert res1["code"] == 0, res1

        if captcha_code:
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

        assert res2["code"] == 0, res2

        return {"ok": False, "verify": res1[f"masked{key}"]}

    async def request(self, server: str, path: str, params: dict) -> dict:
        form: dict[str, str] = {"data": json.dumps(params, separators=(",", ":"))}

        nonce: bytes = gen_nonce()
        signed_nonce: bytes = gen_signed_nonce(self.ssecurity, nonce)

        # 1. gen hash for data param
        form["rc4_hash__"] = gen_signature_base64(path, form, signed_nonce)

        # 2. encrypt data and hash params
        for k, v in form.items():
            ciphertext: bytes = crypt(signed_nonce, v.encode())
            form[k] = base64.b64encode(ciphertext).decode()

        # 3. add signature for encrypted data and hash params
        form["signature"] = gen_signature_base64(path, form, signed_nonce)

        # 4. add nonce
        form["_nonce"] = base64.b64encode(nonce).decode()

        dom = "" if server == "cn" else server + "."

        r = await self.session.post(
            f"https://{dom}api.io.mi.com/app{path}", cookies=self.cookies, data=form
        )
        assert r.ok, r.status

        ciphertext: bytes = base64.b64decode(await r.read())
        plaintext: bytes = crypt(signed_nonce, ciphertext)

        res = json.loads(plaintext)
        assert res["code"] == 0, res

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
            resp = await self.request(server, "/v2/home/device_list_page", payload)
            if resp is None:
                return None
            total.extend(resp["list"])
        return total

    async def get_rooms(self) -> list[dict] | None:
        payload = {"fg": True, "fetch_share": True, "limit": 300}

        total = []
        for server in self.servers:
            resp = await self.request(server, "/v2/homeroom/gethome", payload)
            if resp is None:
                return None
            for home in resp["homelist"]:
                total += home["roomlist"]
        return total

    async def get_bindkey(self, did: str) -> str | None:
        payload = {"did": did, "pdid": 1}
        for server in self.servers:
            resp = await self.request(server, "/v2/device/blt_get_beaconkey", payload)
            if resp:
                return resp["beaconkey"]
        return None


def parse_auth_response(body: bytes) -> dict:
    assert body.startswith(b"&&&START&&&")
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
    params.append(base64.b64encode(signed_nonce).decode())  # use b64 signed nonce
    signature = "&".join(params)
    signature = hashlib.sha1(signature.encode()).digest()
    return base64.b64encode(signature).decode()


def crypt(key: bytes, data: bytes) -> bytes:
    cipher = ARC4.new(key)
    cipher.encrypt(bytes(1024))
    return cipher.encrypt(data)
