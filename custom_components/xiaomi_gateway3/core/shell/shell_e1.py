import asyncio
import base64
import hashlib
import re

from .base import TelnetShell

WGET = "(wget http://master.dl.sourceforge.net/project/aqcn02/{0}?viasf=1 -O /data/{1} && chmod +x /data/{1})"

TAR_DATA = "tar -czOC /data mha_master miio storage zigbee devices.txt gatewayInfoJson.info 2>/dev/null | base64"

MD5_MOSQUITTO_PUB = '7c3883281750e00f717d35d6bdf2d913'


def sed(pattern: str, repl: str):
    """sed with extended regex and edit file in-place"""
    repl = repl.replace('$', '\$').replace('&', '\&').replace('=', '\='). \
        replace('`', '\`').replace('"', '\\"').replace('\n', '\\n')
    return f'sed -r "s={pattern}={repl}=" -i /tmp/app_monitor.sh'


PATCH_MIIO_MQTT = sed(
    "^ +miio_client -.+$",
    "pkill -f log/miio\nmiio_client -l0 -d /data/miio/ -n128 -o DISABLE_PSM -D | awk '/ot_agent_recv_handler_one.+(properties_changed|heartbeat)|record_offline/{print $0;fflush()}' | /data/mosquitto_pub -t log/miio -l &"
)

PATCH_ZIGBEE_PARENTS = sed(
    "^ +(mZ3GatewayHost_MQTT -[^>]+).+$",
    "pkill -f log/z3\n\\1-l 0 | /data/mosquitto_pub -t log/z3 -l &"
)


# noinspection PyAbstractClass
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

        self.apatches = []

    async def prevent_unpair(self):
        await self.exec("killall mha_master")

    async def tar_data(self):
        raw = await self.exec(TAR_DATA, as_bytes=True)
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

    async def check_bin(self, filename: str, md5: str, url=None) -> bool:
        """Check binary md5 and download it if needed."""
        if md5 in await self.exec("md5sum /data/" + filename):
            return True
        elif url:
            await self.exec(WGET.format(url, filename))
            return await self.check_bin(filename, md5)
        else:
            return False

    async def check_mosquitto_pub(self):
        return await self.check_bin('mosquitto_pub', MD5_MOSQUITTO_PUB, 'bin/mosquitto_pub')

    ############################################################################

    def patch_miio_mqtt(self):
        self.apatches.append(PATCH_MIIO_MQTT)

    def patch_zigbee_parents(self):
        self.apatches.append(PATCH_ZIGBEE_PARENTS)

    ############################################################################

    @property
    def app_ps(self):
        if self.apatches:
            return hashlib.md5('\n'.join(self.apatches).encode()).hexdigest()
        return '/bin/app_monitor.sh'

    async def update_app_monitor(self) -> int:
        await self.check_mosquitto_pub()
        await self.exec("killall app_monitor.sh")
        await self.exec(
            "killall miio_client mZ3GatewayHost_MQTT ser2net socat; pkill -f log/z3"
        )

        if not self.apatches:
            await self.exec(f"app_monitor.sh &")
            return 0

        await self.exec("cp /bin/app_monitor.sh /tmp")
        for patch in self.apatches:
            await self.exec(patch)

        await self.exec(f"/tmp/app_monitor.sh {self.app_ps} &")

        return len(self.apatches)

    async def apply_patches(self, ps: str) -> int:
        n = 0
        if self.app_ps not in ps:
            n += await self.update_app_monitor()
        return n
