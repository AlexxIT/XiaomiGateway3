import asyncio
import socket
from typing import Union

from . import base
from .base import TelnetShell, ShellMultimode
from .shell_e1 import ShellE1
from .shell_mgw import ShellMGW
from .shell_mgw2 import ShellMGW2


class Session:
    """Support automatic closing session in case of trouble. Example of usage:

    try:
        async with shell.Session(host) as session:
            sh = await session.login()
            return True
    except Exception:
        return False
    """

    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter

    def __init__(self, host: str, port=23):
        self.coro = asyncio.open_connection(host, port, limit=1_000_000)

    async def __aenter__(self):
        await self.connect()
        return await self.login()

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def connect(self):
        self.reader, self.writer = await asyncio.wait_for(self.coro, 5)

    async def close(self):
        self.writer.close()
        await self.writer.wait_closed()

    async def login(self) -> Union[TelnetShell, ShellMGW, ShellE1, ShellMGW2]:
        coro = self.reader.readuntil(b"login: ")
        resp: bytes = await asyncio.wait_for(coro, 3)

        if b"rlxlinux" in resp:
            shell = ShellMGW(self.reader, self.writer)
        elif b"Aqara-Hub-E1" in resp:
            shell = ShellE1(self.reader, self.writer)
        elif b"Mijia_Hub_V2" in resp:
            shell = ShellMGW2(self.reader, self.writer)
        else:
            raise Exception(f"Unknown response: {resp}")

        await shell.login()
        await shell.prepare()

        return shell


NTP_DELTA = 2208988800  # 1970-01-01 00:00:00
NTP_QUERY = b"\x1b" + 47 * b"\0"


def ntp_time(host: str) -> float:
    """Return server send time"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2)
    try:
        sock.sendto(NTP_QUERY, (host, 123))
        raw = sock.recv(1024)

        integ = int.from_bytes(raw[-8:-4], "big")
        fract = int.from_bytes(raw[-4:], "big")
        return integ + float(fract) / 2**32 - NTP_DELTA
    except Exception:
        return 0
    finally:
        sock.close()


def check_port(host: str, port: int):
    """Check if gateway port open."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        return s.connect_ex((host, port)) == 0
    finally:
        s.close()


def openmiio_setup(config: dict):
    """Custom config for OPENMIIO_CMD, OPENMIIO_VER, OPENMIIO_MIPS..."""
    for k, v in config.items():
        setattr(base, "OPENMIIO_" + k.upper(), v)
