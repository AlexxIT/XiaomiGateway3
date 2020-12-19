import asyncio
import hashlib
import json
import logging
import random
import socket
import time
from asyncio.protocols import BaseProtocol
from asyncio.transports import DatagramTransport
from typing import Union, Optional

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

_LOGGER = logging.getLogger(__name__)

HELLO = bytes.fromhex(
    "21310020ffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
)


class BasemiIO:
    """A simple class that implements the miIO protocol."""
    device_id = None
    delta_ts = None

    def __init__(self, host: str, token: str):
        self.addr = (host, 54321)
        self.token = bytes.fromhex(token)

        key = hashlib.md5(self.token).digest()
        iv = hashlib.md5(key + self.token).digest()
        self.cipher = Cipher(algorithms.AES(key), modes.CBC(iv),
                             backend=default_backend())

    def _encrypt(self, plaintext: bytes):
        padder = padding.PKCS7(128).padder()
        padded_plaintext = padder.update(plaintext) + padder.finalize()

        encryptor = self.cipher.encryptor()
        return encryptor.update(padded_plaintext) + encryptor.finalize()

    def _decrypt(self, ciphertext: bytes):
        decryptor = self.cipher.decryptor()
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        unpadder = padding.PKCS7(128).unpadder()
        return unpadder.update(padded_plaintext) + unpadder.finalize()

    def _pack_raw(self, method: str, params: Union[dict, list] = None):
        # latest zero unnecessary
        payload = json.dumps({
            'id': random.randint(100000000, 999999999),
            'method': method, 'params': params or []
        }, separators=(',', ':')).encode() + b'\x00'

        data = self._encrypt(payload)

        raw = b'\x21\x31'
        raw += (32 + len(data)).to_bytes(2, 'big')  # total length
        raw += b'\x00\x00\x00\x00'  # unknow
        raw += self.device_id.to_bytes(4, 'big')
        raw += int(time.time() - self.delta_ts).to_bytes(4, 'big')

        raw += hashlib.md5(raw + self.token + data).digest()
        raw += data

        assert len(raw) < 1024, "Exceeded message size"

        return raw

    def _unpack_raw(self, raw: bytes):
        assert raw[:2] == b'\x21\x31'
        # length = int.from_bytes(raw[2:4], 'big')
        # unknown = raw[4:8]
        # device_id = int.from_bytes(raw[8:12], 'big')
        # ts = int.from_bytes(raw[12:16], 'big')
        # checksum = raw[16:32]
        return self._decrypt(raw[32:])


class SyncmiIO(BasemiIO):
    """Synchronous miIO protocol."""

    def __init__(self, host: str, token: str, timeout: float = 2):
        super().__init__(host, token)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(timeout)

    def ping(self) -> bool:
        """Returns `true` if the connection to the miio device is working. The
        token is not verified at this stage.
        """
        try:
            self.sock.sendto(HELLO, self.addr)
            raw = self.sock.recv(1024)
            if raw[:2] == b'\x21\x31':
                self.device_id = int.from_bytes(raw[8:12], 'big')
                self.delta_ts = time.time() - int.from_bytes(raw[12:16], 'big')
                return True
        except:
            pass
        return False

    def send(self, method: str, params: Union[dict, list] = None):
        """Send command to miIO device and get result from it. Params can be
        dict or list depend on command.
        """
        if not self.device_id and not self.ping():
            return None

        try:
            raw = self._pack_raw(method, params)
            self.sock.sendto(raw, self.addr)

            # can receive more than 1024 bytes
            raw = self.sock.recv(10240)
            data = self._unpack_raw(raw)

            return json.loads(data.rstrip(b'\x00'))['result']
        except Exception as e:
            _LOGGER.debug(f"Can't send: {e}")
            return None

    def send_bulk(self, method: str, params: list):
        """Sends a command with a large number of parameters. Splits into
        multiple requests when the size of one request is exceeded.
        """
        result = []
        pack = []
        total_len = 0

        try:
            for item in params:
                item_len = len(str(item))
                # approximate number, it seems to work
                if total_len + item_len > 900:
                    result += self.send(method, pack)
                    pack = []
                    total_len = 0

                pack.append(item)
                total_len += item_len

            return result + self.send(method, pack)

        except:
            return None

    def info(self):
        """Get info about miIO device."""
        return self.send('miIO.info')


class AsyncmiIO(BasemiIO, BaseProtocol):
    response = None
    sock: Optional[DatagramTransport] = None

    def datagram_received(self, data: bytes, addr):
        # hello message
        if len(data) == 32:
            if data[:2] == b'\x21\x31':
                self.device_id = int.from_bytes(data[8:12], 'big')
                ts = int.from_bytes(data[12:16], 'big')
                self.delta_ts = time.time() - ts
                result = True
            else:
                result = False
        else:
            result = self._unpack_raw(data)

        self.response.set_result(result)

    def error_received(self, exc):
        print('Error received:', exc)

    def connection_lost(self, exc):
        print("Connection closed")
        self.sock = None

    async def send_raw(self, data: bytes):
        loop = asyncio.get_running_loop()
        if not self.sock:
            self.sock, _ = await loop.create_datagram_endpoint(
                lambda: self, remote_addr=self.addr)

        self.response = loop.create_future()
        # this method does not block
        self.sock.sendto(data)
        return await self.response

    async def ping(self):
        return await self.send_raw(HELLO)

    async def send(self, method: str, params: Union[dict, list] = None):
        """Send command to miIO device and get result from it. Params can be
        dict or list depend on command.
        """
        if not self.device_id and not await self.ping():
            return None

        try:
            raw = self._pack_raw(method, params)
            data = await self.send_raw(raw)
            return json.loads(data.rstrip(b'\x00'))['result']
        except Exception as e:
            _LOGGER.warning(f"Can't send: {e}")
            return None

    async def send_bulk(self, method: str, params: list):
        """Sends a command with a large number of parameters. Splits into
        multiple requests when the size of one request is exceeded.
        """
        result = []
        pack = []
        total_len = 0

        for item in params:
            item_len = len(str(item))
            # approximate number, it seems to work
            if total_len + item_len > 900:
                result += await self.send(method, pack)
                pack = []
                total_len = 0

            pack.append(item)
            total_len += item_len

        return result + await self.send(method, pack)

    async def info(self):
        """Get info about miIO device."""
        return await self.send('miIO.info')
