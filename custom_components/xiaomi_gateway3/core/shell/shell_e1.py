import asyncio
import re

from .base import ShellBase
from .const import OPENMIIO_MD5_ARM, OPENMIIO_URL_ARM, OPENMIIO_CMD


class ShellE1(ShellBase):
    async def login(self):
        self.writer.write(b"root\n")
        await asyncio.sleep(0.1)
        self.writer.write(b"\n")  # empty password

        coro = self.reader.readuntil(b" # ")
        await asyncio.wait_for(coro, timeout=3)

    async def prepare(self):
        # change bash end symbol to gw3 style
        self.writer.write(b"export PS1='# '\n")
        coro = self.reader.readuntil(b"\r\n# ")
        await asyncio.wait_for(coro, timeout=3)

        await self.exec("stty -echo")

    async def get_version(self) -> str:
        raw1 = await self.exec("agetprop ro.sys.mi_fw_ver")
        raw2 = await self.exec("agetprop ro.sys.mi_build_num")
        return f"{raw1.rstrip()}_{raw2.rstrip()}"

    async def get_miio_info(self) -> dict:
        raw = await self.exec("agetprop | grep persist")

        m = re.findall(r"([a-z_]+)]: \[(.+?)]", raw)
        props: dict[str, str] = dict(m)

        return {
            "did": props["miio_did"],
            "key": props["miio_key"],
            "mac": props["miio_mac"],
            "model": props["model"],
            "token": props["miio_dtoken"].encode().hex(),
            "lan_mac": props.get("lan_mac"),
            "version": await self.get_version()
        }

    async def read_xiaomi_did(self) -> dict[str, str]:
        raw = await self.exec("cat /data/mha_master/*.json|grep xiaomi_did")
        m = re.findall(r"(lumi.[a-f0-9]+).+(\d{9,})", raw)
        return dict(m)

    async def check_openmiio(self) -> bool:
        """Check binary exec flag and MD5."""
        cmd = f"[ -x /data/openmiio_agent ] && md5sum /data/openmiio_agent"
        return OPENMIIO_MD5_ARM in await self.exec(cmd)

    async def download_openmiio(self):
        """Kill previous binary, download new one, upload it to gw and set exec flag"""
        await self.exec("killall openmiio_agent")

        raw = await self.download(OPENMIIO_URL_ARM)
        await self.write_file("/data/openmiio_agent", raw)

        await self.exec("chmod +x /data/openmiio_agent")

    async def run_openmiio(self):
        await self.exec(OPENMIIO_CMD)

    async def prevent_unpair(self):
        await self.exec("killall mha_master")

    async def run_ftp(self):
        await self.exec("tcpsvd -E 0.0.0.0 21 ftpd -w &")

    async def read_silabs_devices(self) -> bytes:
        return await self.read_file("/data/devices.txt")
