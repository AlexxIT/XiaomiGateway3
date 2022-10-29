import asyncio

from .base import ShellOpenMiio

URL_AGENT = "http://master.dl.sourceforge.net/project/mgl03/aqcn02/openmiio_agent/openmiio_agent?viasf=1"
MD5_AGENT = "3fea39f9610cbf8a37ffb53ba4fa0689"


# noinspection PyAbstractClass
class ShellARM(ShellOpenMiio):
    async def login(self):
        self.writer.write(b"root\n")
        await asyncio.sleep(.1)
        self.writer.write(b"\n")  # empty password

        coro = self.reader.readuntil(b"/ # ")
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
        raw = await self.exec(
            "agetprop persist.app.miio_dtoken", as_bytes=True
        )
        return raw.rstrip().hex()

    async def get_did(self):
        raw = await self.exec("agetprop persist.sys.miio_did")
        return raw.rstrip()

    async def get_wlan_mac(self):
        raw = await self.exec("agetprop persist.sys.miio_mac")
        return raw.rstrip().replace(":", "").lower()

    async def run_ftp(self):
        await self.exec("tcpsvd -E 0.0.0.0 21 ftpd -w &")

    async def prevent_unpair(self):
        await self.exec("killall mha_master")

    async def check_openmiio_agent(self) -> int:
        return await self.check_bin("openmiio_agent", MD5_AGENT, URL_AGENT)
