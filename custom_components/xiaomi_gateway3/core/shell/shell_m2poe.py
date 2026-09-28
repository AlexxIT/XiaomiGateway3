import asyncio
import re

from .shell_e1 import ShellE1
from ..unqlite import SQLite
from .const import (
    OPENMIIO_CMD,
    OPENMIIO_MD5_ARM,
    OPENMIIO_URL_ARM,
    AGENT2MQTT_CMD,
    AGENT2MQTT_MD5,
    AGENT2MQTT_URL
)
OPENMIIO_CMD = "/data/openmiio_agent cache > /var/log/openmiio.log 2>&1 &"


class ShellM2PoE(ShellE1):
    db: SQLite = None

    async def get_version(self) -> str:
        raw1 = await self.exec("agetprop ro.sys.fw_ver")
        raw2 = await self.exec("agetprop ro.sys.build_num")
        raw3 = await self.exec("agetprop persist.sys.zb_ver")
        return f"{raw1.rstrip()}_{raw2.rstrip()}_{raw3.rstrip()}"

    async def get_miio_info(self) -> dict:
        raw = await self.exec("agetprop | grep persist")

        m = re.findall(r"([a-z_]+)]: \[(.+?)]", raw)
        props: dict[str, str] = dict(m)

        return {
            "did": props.get("miio_did", ""),
            "key": props.get("miio_key", ""),
            "mac": props["miio_mac"],
            "model": props["model"],
            "token": props["sys_token"],
            "lan_mac": props.get("lan_mac"),
            "version": await self.get_version(),
            "uid": props.get("did", ""),
            "cloud": props.get("cloud", "aiot"),
            "sn": props.get("sn", ""),
        }

    async def read_db_bluetooth(self) -> SQLite:
        return None

    async def read_silabs_devices(self) -> bytes:
        return await self.read_file("/data/zigbee_host/devices.txt")

    async def check_openmiio(self) -> bool:
        """Check binary exec flag and MD5."""
        cmd = f"[ -x /data/openmiio_agent ] && md5sum /data/openmiio_agent"
        await self.exec(cmd)
        acmd = f"[ -x /data/agent2mqtt ] && md5sum /data/agent2mqtt"
        if AGENT2MQTT_MD5 in await self.exec(acmd) and OPENMIIO_MD5_ARM in await self.exec(cmd):
            return True
        return False

    async def download_openmiio(self):
        """Kill previous binary, download new one, upload it to gw and set exec flag"""
        await self.exec("killall openmiio_agent")

        raw = await self.download(OPENMIIO_URL_ARM)
        await self.write_file("/data/openmiio_agent", raw)

        await self.exec("chmod +x /data/openmiio_agent")
        await self.exec("killall agent2mqtt")

        raw = await self.download(AGENT2MQTT_URL)
        await self.write_file("/data/agent2mqtt", raw)

        await self.exec("chmod +x /data/agent2mqtt")

    async def run_openmiio(self):
        await self.exec("mkdir -p /var/log")
        await self.exec(OPENMIIO_CMD)
        await self.exec("killall agent2mqtt")
        await asyncio.sleep(0.5)
        await self.exec(AGENT2MQTT_CMD)
