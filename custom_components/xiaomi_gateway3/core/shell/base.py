import asyncio
import base64
from asyncio import StreamReader, StreamWriter
from dataclasses import dataclass
from typing import Union


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

    async def exec(self, command: str, as_bytes=False, timeout=10) \
            -> Union[str, bytes]:
        """Run command and return it result."""
        self.writer.write(command.encode() + b"\n")
        coro = self.reader.readuntil(b"# ")
        raw = await asyncio.wait_for(coro, timeout=timeout)
        return raw[:-2] if as_bytes else raw[:-2].decode()

    async def read_file(self, filename: str, as_base64=False):
        command = f"cat {filename}|base64" if as_base64 else f"cat {filename}"
        try:
            raw = await self.exec(command, as_bytes=True, timeout=60)
            # b"cat: can't open ..."
            return base64.b64decode(raw) if as_base64 else raw
        except:
            return None

    async def reboot(self):
        # should not wait for response
        self.writer.write(b"reboot\n")
        await self.writer.drain()
        # have to wait or the magic won't happen
        await asyncio.sleep(1)

    async def get_version(self) -> str:
        raise NotImplementedError

    async def get_token(self) -> str:
        raise NotImplementedError

    async def prevent_unpair(self):
        raise NotImplementedError

    async def run_ftp(self):
        raise NotImplementedError

    async def tar_data(self):
        raise NotImplementedError

    def patch_zigbee_parents(self):
        raise NotImplementedError
