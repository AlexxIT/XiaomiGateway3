import asyncio

from .shell_e1 import ShellE1
from .shell_mgw import ShellMGW
from .shell_mgw2 import ShellMGW2
from .shell_m2 import ShellM2
from .shell_m2poe import ShellM2PoE


class Session:
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

    async def login(self) -> ShellMGW | ShellE1 | ShellMGW2 | ShellM2 | ShellM2PoE:
        coro = self.reader.readuntil(b"login: ")
        resp: bytes = await asyncio.wait_for(coro, 3)

        if b"rlxlinux" in resp:
            shell = ShellMGW(self.reader, self.writer)
        elif b"Aqara-Hub-E1" in resp or b"Aqara_Hub_E1" in resp:
            shell = ShellE1(self.reader, self.writer)
        elif b"Mijia_Hub_V2" in resp:
            shell = ShellMGW2(self.reader, self.writer)
        elif (b"Aqara-Hub-M2" in resp or b"Aqara-Hub-M3" in resp
                or b"Aqara-Hub-M1S" in resp or b"Outlet-Hub-V1" in resp
                or b"Camera-Hub-G3" in resp or b"Camera-Hub-G2HPro" in resp
                or b"Aqara-Hub-M100" in resp or b"Doorbell-Repeater-G410" in resp
                or b"Aqara-Hub-M200" in resp or b"Camera-Hub-G5Pro" in resp):
            shell = ShellM2PoE(self.reader, self.writer)
        else:
            raise Exception(f"Unknown response: {resp}")

        await shell.login()
        await shell.prepare()

        return shell
