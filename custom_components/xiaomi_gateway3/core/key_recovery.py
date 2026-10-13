"""Bounded gateway-key recovery through a stock diagnostic uploader.

Recovery reads one file; it does not enable Telnet or alter account passwords.
Firmware may remove an existing /tmp/log.tar.gz after an upload.
"""

import asyncio
import base64
import io
import ipaddress
import re
import secrets
import socket
import tarfile
from dataclasses import dataclass, field

from aiohttp import web
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .mini_miio import AsyncMiIO

MAX_UPLOAD = 1024 * 1024
MAX_CONFIG = 64 * 1024
CONFIRMED_BUILDS = frozenset({("lumi.gateway.mgl001", "1.0.8_0013")})
# Only complete handler analysis can add an experimental profile here.
STATIC_BUILDS = frozenset()
PRIVATE_NETWORKS = tuple(
    ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)


class RecoveryError(Exception):
    """An error code safe for UI and logs, without upload or credential data."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class GatewayIdentity:
    model: str
    firmware: str
    mac: str = field(repr=False)


def private_ipv4(value):
    try:
        address = ipaddress.IPv4Address(value)
    except (ValueError, TypeError):
        raise RecoveryError("invalid_input") from None
    if not any(address in network for network in PRIVATE_NETWORKS):
        raise RecoveryError("invalid_input")
    return str(address)


def normalise_mac(value):
    if not isinstance(value, str):
        raise RecoveryError("invalid_identity")
    value = value.lower().replace("-", ":")
    if re.fullmatch("[0-9a-f]{12}", value):
        value = ":".join(value[i : i + 2] for i in range(0, 12, 2))
    if not re.fullmatch(r"[0-9a-f]{2}(?::[0-9a-f]{2}){5}", value):
        raise RecoveryError("invalid_identity")
    return value


def supports_recovery(identity, experimental=False):
    build = (identity.model, identity.firmware)
    return build in CONFIRMED_BUILDS or experimental and build in STATIC_BUILDS


def callback_ipv4(host):
    host = private_ipv4(host)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            # UDP connect chooses a route without sending a datagram.
            sock.connect((host, 54321))
            return private_ipv4(sock.getsockname()[0])
    except (OSError, RecoveryError):
        raise RecoveryError("callback_unavailable") from None


async def async_probe_gateway(host, token):
    private_ipv4(host)
    if not isinstance(token, str) or not re.fullmatch("[0-9a-fA-F]{32}", token):
        raise RecoveryError("invalid_input")
    client = AsyncMiIO(host, token)
    try:
        info = await client.info()
    except (ValueError, OSError):
        raise RecoveryError("cannot_connect") from None
    if not isinstance(info, dict) or not info:
        code = "invalid_token" if client.device_id is not None else "cannot_connect"
        raise RecoveryError(code)
    model, firmware = info.get("model"), info.get("fw_ver")
    if not isinstance(model, str) or not isinstance(firmware, str):
        raise RecoveryError("invalid_identity")
    return GatewayIdentity(model, firmware, normalise_mac(info.get("mac")))


def read_gateway_key(encrypted, key, iv, identity):
    """Validate a single in-memory device.conf; never extract archive paths."""
    try:
        if not encrypted or len(encrypted) > MAX_UPLOAD or len(encrypted) % 16:
            raise ValueError()
        decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
        padded = decryptor.update(encrypted) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded) + unpadder.finalize()
        with tarfile.open(fileobj=io.BytesIO(plaintext), mode="r:") as archive:
            members = archive.getmembers()
            if len(members) != 1:
                raise ValueError()
            member = members[0]
            if (
                member.name != "device.conf"
                or not member.isfile()
                or not 0 < member.size <= MAX_CONFIG
            ):
                raise ValueError()
            content = archive.extractfile(member).read(MAX_CONFIG + 1).decode("utf-8")
        values = {}
        for line in content.splitlines():
            name, separator, value = line.partition("=")
            if separator and name in ("model", "mac", "key"):
                if name in values:
                    raise ValueError()
                values[name] = value
        if (
            values.get("model") != identity.model
            or normalise_mac(values.get("mac")) != identity.mac
        ):
            raise ValueError()
        result = values.get("key", "")
        if len(result) != 16 or any(not 33 <= ord(c) <= 126 for c in result):
            raise ValueError()
        return result
    except (ValueError, UnicodeError, tarfile.TarError, OSError, RecoveryError):
        raise RecoveryError("invalid_upload") from None


class KeyReceiver:
    """One short-lived upload endpoint, with no access log or archive persistence."""

    def __init__(self, host, address, port, identity):
        self.host, self.address, self.port = host, address, port
        self.identity = identity
        self.key, self.iv = secrets.token_bytes(16), secrets.token_bytes(16)
        self.path = "/" + secrets.token_urlsafe(24)
        self.future = asyncio.get_running_loop().create_future()
        self.runner = None
        self.started = False
        self.url = None

    async def start(self):
        app = web.Application(client_max_size=MAX_UPLOAD)
        app.router.add_put(self.path, self.receive)
        self.runner = web.AppRunner(app, access_log=None, shutdown_timeout=1)
        await self.runner.setup()
        site = web.TCPSite(self.runner, self.address, self.port)
        try:
            await site.start()
        except OSError:
            raise RecoveryError("callback_unavailable") from None
        port = self.runner.addresses[0][1]
        self.url = f"http://{self.address}:{port}{self.path}"

    @property
    def params(self):
        return {
            "encryptKey": base64.urlsafe_b64encode(self.key).decode(),
            "iv": base64.urlsafe_b64encode(self.iv).decode(),
            "url": self.url,
            "fileList": ["/data/miio/device.conf"],
            "filelist": ["/data/miio/device.conf"],
        }

    async def receive(self, request):
        if request.remote != self.host:
            return web.Response(status=403)
        if self.started or self.future.done():
            return web.Response(status=409)
        length = request.content_length
        if length is None or not 0 < length <= MAX_UPLOAD:
            return web.Response(status=413)
        self.started = True
        try:
            encrypted = await asyncio.wait_for(request.read(), 15)
            if len(encrypted) != length:
                raise RecoveryError("invalid_upload")
            result = read_gateway_key(encrypted, self.key, self.iv, self.identity)
            if not self.future.done():
                self.future.set_result(result)
            return web.Response(status=200)
        except (asyncio.TimeoutError, RecoveryError, OSError, web.HTTPException):
            if not self.future.done():
                self.future.set_exception(RecoveryError("invalid_upload"))
            return web.Response(status=400)

    async def close(self):
        if self.runner:
            await self.runner.cleanup()
        if not self.future.done():
            self.future.cancel()
        elif not self.future.cancelled():
            self.future.exception()  # Consume an error even if the RPC was rejected.


async def async_recover_gateway_key(
    host,
    token,
    callback_address=None,
    *,
    identity=None,
    timeout=90,
    port=0,
    experimental=False,
):
    """Export once after fresh token/identity checks, with guaranteed cleanup."""
    if not 1 <= timeout <= 300 or not isinstance(port, int) or not 0 <= port <= 65535:
        raise RecoveryError("invalid_input")
    observed = await async_probe_gateway(host, token)
    if identity is not None and identity != observed:
        raise RecoveryError("invalid_identity")
    if not supports_recovery(observed, experimental):
        raise RecoveryError("unsupported_firmware")
    address = (
        private_ipv4(callback_address) if callback_address else callback_ipv4(host)
    )
    receiver = KeyReceiver(host, address, port, observed)
    try:
        await receiver.start()
        client = AsyncMiIO(host, token)
        response = await client.send(
            "async_device_feedback_log", receiver.params, tries=1
        )
        # A missing acknowledgement can still accompany a valid asynchronous upload.
        if isinstance(response, dict) and response.get("error"):
            raise RecoveryError("method_rejected")
        result = response.get("result") if isinstance(response, dict) else None
        if (
            isinstance(result, dict)
            and isinstance(result.get("code"), int)
            and result["code"] < 0
        ):
            raise RecoveryError("method_rejected")
        try:
            return await asyncio.wait_for(receiver.future, timeout)
        except asyncio.TimeoutError:
            raise RecoveryError("upload_timeout") from None
    finally:
        await receiver.close()
