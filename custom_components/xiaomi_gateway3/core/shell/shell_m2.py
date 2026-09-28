import asyncio
import re

from .shell_mgw import ShellMGW

OPENMIIO_CMD = "/data/openmiio_agent cache > /var/log/openmiio.log 2>&1 &"


class ShellM2(ShellMGW):
    async def get_version(self):
        raw = await self.read_file("/etc/build.prop")
        m = re.search(r"ro.sys.fw_ver=([0-9._]+)", raw.decode())
        return m[1]

    async def get_miio_info(self) -> dict:
        raw = await self.exec("getprop | grep persist")

        m = re.findall(r"([a-z_]+)]: \[(.+?)]", raw)
        props: dict[str, str] = dict(m)

        return {
            "did": props.get("miio_did"),
            "key": props.get("miio_key"),
            "mac": props["miio_mac"],
            "model": props["model"],
            "token": props.get("sys_token", ""),
            "lan_mac": props.get("lan_mac"),
            "version": await self.get_version(),
            "uid": props.get("did", ""),
            "cloud": props.get("cloud", "aiot"),
            "sn": props.get("sn", ""),
        }

    async def run_openmiio(self):
        await self.exec(OPENMIIO_CMD)