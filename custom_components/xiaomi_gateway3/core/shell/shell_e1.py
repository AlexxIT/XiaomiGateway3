import base64
import hashlib

from .shell_arm import ShellARM

TAR_DATA = "tar -czOC /data mha_master miio storage zigbee devices.txt gatewayInfoJson.info 2>/dev/null | base64"

URL_MOSQUITTO_PUB = "http://master.dl.sourceforge.net/project/aqcn02/bin/mosquitto_pub?viasf=1"
MD5_MOSQUITTO_PUB = "7c3883281750e00f717d35d6bdf2d913"


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
class ShellE1(ShellARM):
    model = "e1"

    apatches: list = None

    async def prepare(self):
        await ShellARM.prepare(self)

        self.apatches = []

    async def tar_data(self):
        raw = await self.exec(TAR_DATA, as_bytes=True)
        return base64.b64decode(raw)

    async def check_mosquitto_pub(self):
        return await self.check_bin(
            "mosquitto_pub", MD5_MOSQUITTO_PUB, URL_MOSQUITTO_PUB
        )

    ###########################################################################

    def patch_miio_mqtt(self):
        self.apatches.append(PATCH_MIIO_MQTT)

    def patch_zigbee_parents(self):
        self.apatches.append(PATCH_ZIGBEE_PARENTS)

    ###########################################################################

    @property
    def app_ps(self):
        if self.apatches:
            return hashlib.md5("\n".join(self.apatches).encode()).hexdigest()
        return "/bin/app_monitor.sh"

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
