import asyncio
import re
from typing import Dict

from . import base


# noinspection PyAbstractClass
class ShellARM(base.ShellOpenMiio):
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

    async def get_version(self):
        raw1 = await self.exec("agetprop ro.sys.mi_fw_ver")
        raw2 = await self.exec("agetprop ro.sys.mi_build_num")
        self.ver = f"{raw1.rstrip()}_{raw2.rstrip()}"

    async def get_token(self) -> str:
        raw = await self.exec("agetprop persist.app.miio_dtoken", as_bytes=True)
        return raw.rstrip().hex()

    async def get_did(self):
        raw = await self.exec("agetprop persist.sys.miio_did")
        return raw.rstrip()

    async def get_miio_info(self) -> dict:
        raw = await self.exec("agetprop | grep persist")

        m = re.findall(r"([a-z_]+)]: \[(.+?)]", raw)
        props: Dict[str, str] = dict(m)

        return {
            "did": props["miio_did"],
            "key": props["miio_key"],
            "mac": props["miio_mac"],
            "model": props["model"],
            "token": props["miio_dtoken"].encode().hex(),
        }

    async def get_wlan_mac(self):
        raw = await self.exec("agetprop persist.sys.miio_mac")
        return raw.rstrip().replace(":", "").lower()

    async def run_ftp(self):
        await self.exec("tcpsvd -E 0.0.0.0 21 ftpd -w &")

    async def prevent_unpair(self):
        await self.exec("killall mha_master")

    @property
    def openmiio_md5(self) -> str:
        return base.OPENMIIO_MD5_ARM

    @property
    def openmiio_url(self) -> str:
        return base.OPENMIIO_URL_ARM
