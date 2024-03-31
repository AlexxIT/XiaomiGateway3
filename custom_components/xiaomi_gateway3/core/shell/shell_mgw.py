import asyncio
import re

from .base import ShellBase
from .const import OPENMIIO_MD5_MIPS, OPENMIIO_URL_MIPS, OPENMIIO_CMD
from ..unqlite import SQLite

CHECK_FIRMWARE = "/data/busybox lsattr /data/firmware/firmware_ota.bin"
LOCK_FIRMWARE = "mkdir -p /data/firmware && touch /data/firmware/firmware_ota.bin && /data/busybox chattr +i /data/firmware/firmware_ota.bin"
UNLOCK_FIRMWARE = "/data/busybox chattr -i /data/firmware/firmware_ota.bin"

BUSYBOX_URL = "https://busybox.net/downloads/binaries/1.21.1/busybox-mipsel"
BUSYBOX_MD5 = "099137899ece96f311ac5ab554ea6fec"


class ShellMGW(ShellBase):
    async def login(self):
        self.writer.write(b"admin\n")
        raw = await asyncio.wait_for(self.reader.readuntil(b"\r\n# "), 3)
        # OK if gateway without password
        if b"Password:" not in raw:
            return
        # check if gateway has default password
        self.writer.write(b"admin\n")
        raw = await asyncio.wait_for(self.reader.readuntil(b"\r\n# "), 3)
        # can't continue without password
        if b"Password:" in raw:
            raise Exception("Telnet with password don't supported")

    async def prepare(self):
        await self.exec("stty -echo")

    async def get_version(self):
        raw = await self.read_file("/etc/rootfs_fw_info")
        m = re.search(r"version=([0-9._]+)", raw.decode())
        return m[1]

    async def get_token(self) -> str:
        raw = await self.read_file("/data/miio/device.token")
        return raw.rstrip().hex()

    async def get_miio_info(self) -> dict[str, str]:
        """
        did=123456789
        key=abcdefabcdefabcd
        mac=AA:BB:CC:DD:EE:FF
        vendor=lumi
        model=lumi.gateway.mgl03
        """
        raw = await self.read_file("/data/miio/device.conf")
        m = re.findall(r"(did|key|mac|model)=(\S+)", raw.decode())
        props: dict[str, str] = dict(m)
        props["token"] = await self.get_token()
        props["version"] = await self.get_version()
        return props

    db: SQLite = None

    async def read_db_bluetooth(self) -> SQLite:
        if not self.db:
            raw = await self.read_file("/data/miio/mible_local.db", as_base64=True)
            self.db = SQLite(raw)
        return self.db

    async def read_xiaomi_did(self) -> dict[str, str]:
        raw = await self.exec("cat /data/zigbee_gw/*.json|grep xiaomi_did")
        m = re.findall(r"(lumi.[a-f0-9]+).+(\d{9,})", raw)
        return dict(m)

    async def check_openmiio(self) -> bool:
        """Check binary exec flag and MD5."""
        cmd = f"[ -x /data/openmiio_agent ] && md5sum /data/openmiio_agent"
        return OPENMIIO_MD5_MIPS in await self.exec(cmd)

    async def download_openmiio(self):
        """Kill previous binary, download new one, upload it to gw and set exec flag"""
        await self.exec("killall openmiio_agent")

        raw = await self.download(OPENMIIO_URL_MIPS)
        await self.write_file("/data/openmiio_agent", raw)

        await self.exec("chmod +x /data/openmiio_agent")

    async def run_openmiio(self):
        await self.exec(OPENMIIO_CMD)

    async def prevent_unpair(self):
        await self.exec("killall zigbee_gw")

    async def check_busybox(self) -> bool:
        cmd = f"[ -x /data/busybox ] && md5sum /data/busybox"
        if BUSYBOX_MD5 in await self.exec(cmd):
            return True

        raw = await self.download(BUSYBOX_URL)
        await self.write_file("/data/busybox", raw)
        await self.exec("chmod +x /data/busybox")

        return BUSYBOX_MD5 in await self.exec(cmd)

    async def run_ftp(self):
        if await self.check_busybox():
            await self.exec("/data/busybox tcpsvd -E 0.0.0.0 21 /data/busybox ftpd -w&")

    async def check_firmware_lock(self) -> bool:
        """Check if firmware update locked. And create empty file if needed."""
        resp = await self.exec(CHECK_FIRMWARE)
        return "-i-" in resp

    async def lock_firmware(self, enable: bool):
        if await self.check_busybox():
            await self.exec(LOCK_FIRMWARE if enable else UNLOCK_FIRMWARE)

    async def read_silabs_devices(self) -> bytes:
        return await self.read_file("/data/silicon_zigbee_host/devices.txt")
