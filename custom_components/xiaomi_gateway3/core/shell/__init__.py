import asyncio
from typing import Union

from . import base
from .base import TelnetShell, ShellOpenMiio, ShellMultimode
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
        elif b"Aqara-Hub-E1" in resp or b"Aqara_Hub_E1" in resp:
            shell = ShellE1(self.reader, self.writer)
        elif b"Mijia_Hub_V2" in resp:
            shell = ShellMGW2(self.reader, self.writer)
        else:
            raise Exception(f"Unknown response: {resp}")

        await shell.login()
        await shell.prepare()

        return shell


def openmiio_setup(config: dict):
    """Custom config for OPENMIIO_CMD, OPENMIIO_VER, OPENMIIO_MIPS..."""
    for k, v in config.items():
        setattr(base, "OPENMIIO_" + k.upper(), v)
