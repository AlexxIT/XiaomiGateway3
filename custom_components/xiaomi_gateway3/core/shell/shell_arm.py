import asyncio

from .base import ShellOpenMiio

URL_AGENT = "http://master.dl.sourceforge.net/project/mgl03/openmiio_agent/arm/openmiio_agent?viasf=1"
MD5_AGENT = "c792de99d17ef735b4a344b9b17639fe"


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

    async def run_public_mosquitto(self):
        await self.exec("killall mosquitto")
        await asyncio.sleep(.5)
        # mosquitto bind to local IP and local interface, need to fix this
        await self.exec(
            "cp /bin/mosquitto /tmp; sed 's=127.0.0.1=0000.0.0.0=;s=^lo$= =' -i /tmp/mosquitto; /tmp/mosquitto -d"
        )

    async def run_ftp(self):
        await self.exec("tcpsvd -E 0.0.0.0 21 ftpd -w &")

    async def prevent_unpair(self):
        await self.exec("killall mha_master")

    async def check_openmiio_agent(self) -> int:
        return await self.check_bin("openmiio_agent", MD5_AGENT, URL_AGENT)
