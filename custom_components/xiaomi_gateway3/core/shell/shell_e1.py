import asyncio
import base64

from .base import TelnetShell

TAR_DATA = b"tar -czOC /data mha_master miio storage zigbee " \
           b"devices.txt gatewayInfoJson.info 2>/dev/null | base64\n"


class ShellE1(TelnetShell):
    model = "e1"

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

    async def prevent_unpair(self):
        await self.exec("killall mha_master")

    async def tar_data(self):
        self.writer.write(TAR_DATA)
        coro = self.reader.readuntil(b"\r\n# ")
        raw = await asyncio.wait_for(coro, timeout=10)
        return base64.b64decode(raw)

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

    async def get_wlan_mac(self):
        raw = await self.exec("agetprop persist.sys.miio_mac")
        return raw.rstrip().replace(":", "").lower()

    async def get_running_ps(self) -> str:
        return await self.exec("ps")

    async def run_public_mosquitto(self):
        await self.exec("killall mosquitto")
        await asyncio.sleep(.5)
        # mosquitto bind to local IP and local interface, need to fix this
        await self.exec(
            "cp /bin/mosquitto /tmp; sed 's=127.0.0.1=0000.0.0.0=;s=^lo$= =' -i /tmp/mosquitto; /tmp/mosquitto -d"
        )

    async def run_ntpd(self):
        await self.exec("ntpd -l")

    async def run_ftp(self):
        await self.exec("busybox tcpsvd -E 0.0.0.0 21 busybox ftpd -w &")

    async def apply_patches(self, ps: str) -> int:
        # n = 0
        # if self.app_ps not in ps:
        #     n += await self.update_daemon_app()
        # if self.miio_ps not in ps:
        #     n += await self.update_daemon_miio()
        # return n
        return 0
