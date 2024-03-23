import asyncio
import base64

import aiohttp


class ShellBase:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer

    async def close(self):
        if not self.writer:
            return
        self.writer.close()
        await self.writer.wait_closed()

    async def write(self, data: bytes, until: bytes, timeout: float) -> bytes:
        self.writer.write(data)
        coro = self.reader.readuntil(until)
        return await asyncio.wait_for(coro, timeout)

    async def exec(self, command: str, as_bytes=False, timeout=10) -> str | bytes:
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
        except:
            return None

    async def write_file(self, filename: str, data: bytes):
        # start new file
        await self.exec(f"> {filename}")

        size = 700  # total exec cmd should be lower than 1024 symbols
        for i in range(0, len(data), size):
            b = base64.b64encode(data[i : i + size]).decode()
            await self.exec(f"echo -n {b} | base64 -d >> {filename}")

    async def only_one(self) -> bool:
        # run shell with dummy option, so we can check if second Hass connected
        # shell will close automatically when disconnected from telnet
        raw = await self.exec("(ps|grep -v grep|grep -q 'sh +o') || sh +o")
        return "set -o errexit" in raw

    async def get_running_ps(self) -> str:
        return await self.exec("ps")

    async def reboot(self):
        # should not wait for response
        self.writer.write(b"reboot\n")
        await self.writer.drain()
        # have to wait or the magic won't happen
        await asyncio.sleep(1)

    @staticmethod
    async def download(url_or_path: str) -> bytes:
        if not url_or_path.startswith("http"):
            with open(url_or_path, "rb") as f:
                return f.read()

        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url_or_path) as resp:
                return await resp.read()
