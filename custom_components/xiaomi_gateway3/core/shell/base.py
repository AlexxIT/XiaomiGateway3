import asyncio
import base64
from asyncio import StreamReader, StreamWriter
from dataclasses import dataclass
from typing import Union

import aiohttp

from ..unqlite import SQLite

ERROR = 0
OK = 1
DOWNLOAD = 2

# rewrite log every time to prevent memory overflow
OPENMIIO_CMD = "/data/openmiio_agent miio mqtt cache central z3 --zigbee.tcp=8888 > /var/log/openmiio.log 2>&1 &"
OPENMIIO_BASE = "https://github.com/AlexxIT/openmiio_agent/releases/download/v1.2.1/"
OPENMIIO_MD5_MIPS = "6c3f4dca62647b9d19a81e1ccaa5ccc0"
OPENMIIO_MD5_ARM = "bb0b33b8d71acbfb9668ae9a0600c2d8"
OPENMIIO_URL_MIPS = OPENMIIO_BASE + "openmiio_agent_mips"
OPENMIIO_URL_ARM = OPENMIIO_BASE + "openmiio_agent_arm"


@dataclass
class TelnetShell:
    reader: StreamReader
    writer: StreamWriter
    model = None
    ver = None

    async def close(self):
        if not self.writer:
            return
        self.writer.close()
        await self.writer.wait_closed()

    async def exec(self, command: str, as_bytes=False, timeout=10) -> Union[str, bytes]:
        """Run command and return it result."""
        self.writer.write(command.encode() + b"\n")
        coro = self.reader.readuntil(b"# ")
        raw = await asyncio.wait_for(coro, timeout=timeout)
        return raw[:-2] if as_bytes else raw[:-2].decode()

    async def read_file(self, filename: str, as_base64=False, tail=None):
        command = f"tail -c {tail} {filename}" if tail else f"cat {filename}"
        if as_base64:
            command += " | base64"
        try:
            raw = await self.exec(command, as_bytes=True, timeout=60)
            # b"cat: can't open ..."
            return base64.b64decode(raw) if as_base64 else raw
        except Exception:
            return None

    async def write_file(self, filename: str, data: bytes):
        # start new file
        await self.exec(f"> {filename}")

        size = 700  # total exec cmd should be lower than 1024 symbols
        for i in range(0, len(data), size):
            b = base64.b64encode(data[i : i + size]).decode()
            await self.exec(f"echo -n {b} | base64 -d >> {filename}")

    async def reboot(self):
        # should not wait for response
        self.writer.write(b"reboot\n")
        await self.writer.drain()
        # have to wait or the magic won't happen
        await asyncio.sleep(1)

    async def only_one(self) -> bool:
        # run shell with dummy option, so we can check if second Hass connected
        # shell will close automatically when disconnected from telnet
        raw = await self.exec("(ps|grep -v grep|grep -q 'sh +o') || sh +o")
        return "set -o errexit" in raw

    async def run_ntpd(self):
        await self.exec("ntpd -l")

    async def check_bin(self, filename: str, md5: str, url: str) -> int:
        """
        Check binary md5 and download it if needed. We should use HTTP-link
        because wget don't support HTTPS and curl removed in lastest fw. But
        it's not a problem because we check md5.
        """
        filepath = "/data/" + filename
        cmd = f"[ -x {filepath} ] && md5sum {filepath}"

        if md5 in await self.exec(cmd):
            return OK

        # better not to kill busybox :)
        if filename != "busybox":
            # if there is an old version of the file
            await self.exec("killall " + filename)

        raw = await download(url)
        await self.write_file(filepath, raw)

        await self.exec("chmod +x " + filepath)

        return DOWNLOAD if md5 in await self.exec(cmd) else ERROR

    async def get_running_ps(self) -> str:
        return await self.exec("ps")

    async def get_version(self) -> str:
        raise NotImplementedError

    async def get_token(self) -> str:
        raise NotImplementedError

    async def get_miio_info(self) -> str:
        raise NotImplementedError

    async def prevent_unpair(self):
        raise NotImplementedError

    async def run_ftp(self):
        raise NotImplementedError

    async def tar_data(self):
        raise NotImplementedError


# noinspection PyAbstractClass
class ShellOpenMiio(TelnetShell):
    @property
    def openmiio_md5(self) -> str:
        raise NotImplementedError

    @property
    def openmiio_url(self) -> str:
        raise NotImplementedError

    async def check_openmiio(self) -> bool:
        """Check binary exec flag and MD5."""
        cmd = f"[ -x /data/openmiio_agent ] && md5sum /data/openmiio_agent"
        return self.openmiio_md5 in await self.exec(cmd)

    async def download_openmiio(self):
        """Kill previous binary, download new one, upload it to gw and set exec flag"""
        await self.exec("killall openmiio_agent")

        raw = await download(self.openmiio_url)
        await self.write_file("/data/openmiio_agent", raw)

        await self.exec("chmod +x /data/openmiio_agent")

    async def run_openmiio(self):
        await self.exec(OPENMIIO_CMD)


# noinspection PyAbstractClass
class ShellMultimode(ShellOpenMiio):
    db: SQLite = None

    async def read_db_bluetooth(self) -> SQLite:
        if not self.db:
            raw = await self.read_file(self.mesh_db, as_base64=True)
            self.db = SQLite(raw)
        return self.db

    @property
    def mesh_db(self) -> str:
        raise NotImplementedError

    @property
    def mesh_group_table(self) -> str:
        raise NotImplementedError

    @property
    def mesh_device_table(self) -> str:
        raise NotImplementedError


async def download(url_or_path: str) -> bytes:
    if not url_or_path.startswith("http"):
        with open(url_or_path, "rb") as f:
            return f.read()

    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url_or_path) as resp:
            return await resp.read()
