import asyncio
import hashlib
import re
from typing import List

from . import base

CHECK_FIRMWARE = "/data/busybox lsattr /data/firmware/firmware_ota.bin"
LOCK_FIRMWARE = "mkdir -p /data/firmware && touch /data/firmware/firmware_ota.bin && /data/busybox chattr +i /data/firmware/firmware_ota.bin"
UNLOCK_FIRMWARE = "/data/busybox chattr -i /data/firmware/firmware_ota.bin"

RUN_FTP = "/data/busybox tcpsvd -E 0.0.0.0 21 /data/busybox ftpd -w &"

# c create, z gzip, O stdout, C change DIR
TAR_DATA = "tar -czO /data/miio/mible_local.db* /data/silicon_zigbee_host/*.txt /data/zigbee /data/zigbee_gw 2>/dev/null | base64"

URL_BUSYBOX = "https://busybox.net/downloads/binaries/1.21.1/busybox-mipsel"
MD5_BUSYBOX = "099137899ece96f311ac5ab554ea6fec"


def sed(app: str, pattern: str, repl: str):
    """sed with extended regex and edit file in-place"""
    repl = (
        repl.replace("$", r"\$")
        .replace("&", r"\&")
        .replace("=", r"\=")
        .replace("`", r"\`")
        .replace('"', '\\"')
        .replace("\n", "\\n")
    )
    return f'sed -r "s={pattern}={repl}=" -i /tmp/{app}'


# patch silabs_ncp_bt for storing data in tmp (memory)
PATCH_MEMORY_BLUETOOTH1 = "[ -d /tmp/miio ] || (cp -R /data/miio /tmp && cp /bin/silabs_ncp_bt /tmp && sed -r 's=/data/=/tmp//=g' -i /tmp/silabs_ncp_bt)"
PATCH_MEMORY_BLUETOOTH2 = sed(
    "daemon_miio.sh", "^/bin/silabs_ncp_bt", "/tmp/silabs_ncp_bt"
)
# every 5 min sync sqlite DB from memory to NAND if changed
PATCH_MEMORY_BLUETOOTH3 = sed(
    "daemon_miio.sh",
    "^\tdo$",
    """\tdo
if [ ${#N} -eq 60 ]; then
  if [ "`md5sum /tmp/miio/mible_local.db|cut -d' ' -f1`" != "`md5sum /data/miio/mible_local.db|cut -d' ' -f1`" ]; then
    cp /tmp/miio/mible_local.db /data/miio
    echo "`date` bluetooth" >> /var/log/storage_sync.log
  fi; N=
fi; N=$N.
""",
)

# move zigbee DB to tmp (memory)
PATCH_MEMORY_ZIGBEE1 = "[ -d /tmp/zigbee_gw ] || cp -R /data/zigbee_gw /tmp"
PATCH_MEMORY_ZIGBEE2 = sed(
    "daemon_app.sh", "^ +zigbee_gw", "zigbee_gw -s /tmp/zigbee_gw/"
)
# every 5 min sync zigbee DB if device list changed
PATCH_MEMORY_ZIGBEE3 = sed(
    "daemon_app.sh",
    "^\tdo$",
    """\tdo
if [ ${#N} -eq 60 ]; then
  if [ "`md5sum /tmp/zigbee_gw/device_properties.json|cut -d' ' -f1`" != "`md5sum /data/zigbee_gw/device_properties.json|cut -d' ' -f1`" ]; then
    cp /tmp/zigbee_gw/device_properties.json /data/zigbee_gw
    false | cp -i /tmp/zigbee_gw/*.json /data/zigbee_gw/ 2>/dev/null
    echo "`date` zigbee" >> /var/log/storage_sync.log
  fi; N=
fi; N=$N.
""",
)

# patch basic_gw file to not beeps with 5 sec Motion Sensors
PATCH_DISABLE_BUZZER1 = "[ -f /tmp/basic_gw ] || (cp /bin/basic_gw /tmp && sed -r 's=dev_query=xxx_query=' -i /tmp/basic_gw)"
# use patched binary instead of original
PATCH_DISABLE_BUZZER2 = sed("daemon_miio.sh", "^ +basic_gw", "/tmp/basic_gw")

# compare md5sum of two files and copy if not equal
SYNC_MEMORY_FILE = """[ "`md5sum /tmp/{0}|cut -d' ' -f1`" != "`md5sum /data/{0}|cut -d' ' -f1`" ] && cp /tmp/{0} /data/{0}"""

# `ls -1t` - sort files by change time, `sed q` - leave only first row
DB_BLUETOOTH = (
    "`ls -1t /data/miio/mible_local.db /tmp/miio/mible_local.db 2>/dev/null | sed q`"
)
# `sed...` - remove filename and adds "*.json" on its place
DB_ZIGBEE = "`ls -1t /data/zigbee_gw/* /tmp/zigbee_gw/* 2>/dev/null | sed -r 's/[^/]+$/*.json/;q'`"


class ShellMGW(base.ShellMultimode):
    model = "mgw"

    app_patches: List[str] = None
    miio_patches: List[str] = None

    async def login(self):
        self.writer.write(b"admin\n")

        coro = self.reader.readuntil(b"\r\n# ")
        raw = await asyncio.wait_for(coro, timeout=3)
        if b"Password:" in raw:
            raise Exception("Telnet with password don't supported")

    async def prepare(self):
        await self.exec("stty -echo")

        self.app_patches = []
        self.miio_patches = []

    async def get_running_ps(self) -> str:
        return await self.exec("ps -ww | grep -v ' 0 SW'")

    async def check_openmiio_agent(self) -> int:
        return await self.check_bin(
            "openmiio_agent", base.OPENMIIO_MD5_MIPS, base.OPENMIIO_URL_MIPS
        )

    async def run_ftp(self):
        if await self.check_bin("busybox", MD5_BUSYBOX, URL_BUSYBOX):
            await self.exec(RUN_FTP)

    async def check_firmware_lock(self) -> bool:
        """Check if firmware update locked. And create empty file if needed."""
        resp = await self.exec(CHECK_FIRMWARE)
        return "-i-" in resp

    async def lock_firmware(self, enable: bool):
        if await self.check_bin("busybox", MD5_BUSYBOX, URL_BUSYBOX):
            command = LOCK_FIRMWARE if enable else UNLOCK_FIRMWARE
            await self.exec(command)

    async def memory_sync(self):
        # get exists file list from /tmp
        resp = await self.exec(
            "ls -1 /tmp/miio/mible_local.db /tmp/zigbee_gw/* 2>/dev/null"
        )
        for file in resp.split("\r\n"):
            # sync file if md5sum not equal
            command = SYNC_MEMORY_FILE.format(file[5:])
            await self.exec(command)

    async def prevent_unpair(self):
        await self.exec("killall zigbee_gw")

    async def tar_data(self) -> str:
        raw = await self.exec(TAR_DATA)
        return raw.replace("\r\n", "")

    async def get_version(self):
        raw = await self.read_file("/etc/rootfs_fw_info")
        m = re.search(r"version=([0-9._]+)", raw.decode())
        self.ver = m[1]

    async def get_token(self) -> str:
        raw = await self.read_file("/data/miio/device.token")
        return raw.rstrip().hex()

    async def get_did(self):
        raw = await self.read_file("/data/miio/device.conf")
        m = re.search(r"did=(\d+)", raw.decode())
        return m[1]

    async def get_wlan_mac(self) -> str:
        raw = await self.read_file("/sys/class/net/wlan0/address")
        return raw.decode().rstrip().replace(":", "")

    @property
    def mesh_db(self) -> str:
        return DB_BLUETOOTH

    @property
    def mesh_group_table(self) -> str:
        if self.ver >= "1.4.7_0160":
            return "mesh_group_v3"
        elif self.ver >= "1.4.6_0043":
            return "mesh_group_v1"
        else:
            return "mesh_group"

    @property
    def mesh_device_table(self) -> str:
        return "mesh_device_v3" if self.ver >= "1.4.7_0160" else "mesh_device"

    ###########################################################################

    def patch_memory_zigbee(self):
        self.app_patches += [
            PATCH_MEMORY_ZIGBEE1,
            PATCH_MEMORY_ZIGBEE2,
            PATCH_MEMORY_ZIGBEE3,
        ]

    def patch_memory_bluetooth(self):
        self.miio_patches += [PATCH_MEMORY_BLUETOOTH1, PATCH_MEMORY_BLUETOOTH2]

    ###########################################################################

    @property
    def app_ps(self):
        if self.app_patches:
            return hashlib.md5("\n".join(self.app_patches).encode()).hexdigest()
        return "/bin/daemon_app.sh"

    async def update_daemon_app(self) -> int:
        await self.exec("killall daemon_app.sh")
        await self.exec(
            "killall Lumi_Z3GatewayHost_MQTT ser2net socat zigbee_gw; pkill -f log/z3"
        )

        if not self.app_patches:
            await self.exec(f"daemon_app.sh &")
            return 0

        await self.exec("cp /bin/daemon_app.sh /tmp")
        for patch in self.app_patches:
            await self.exec(patch)

        await self.exec(f"/tmp/daemon_app.sh {self.app_ps} &")

        return len(self.app_patches)

    @property
    def miio_ps(self):
        if self.miio_patches:
            return hashlib.md5("\n".join(self.miio_patches).encode()).hexdigest()
        return "/bin/daemon_miio.sh"

    async def update_daemon_miio(self) -> int:
        """Run default daemon_miio if no patches. Or run patched daemon_miio
        with patches hash in process list.
        """
        await self.exec("killall daemon_miio.sh")
        await self.exec("killall silabs_ncp_bt; killall -9 basic_gw")

        if not self.miio_patches:
            await self.exec(f"daemon_miio.sh &")
            return 0

        await self.exec("cp /bin/daemon_miio.sh /tmp")
        for patch in self.miio_patches:
            await self.exec(patch)

        await self.exec(f"/tmp/daemon_miio.sh {self.miio_ps} &")

        return len(self.miio_patches)

    @property
    def mon_ps(self):
        return self.app_ps.replace("daemon_app", "app_monitor")

    async def update_app_monitor(self) -> int:
        """Run default daemon_miio if no patches. Or run patched daemon_miio
        with patches hash in process list.
        """
        await self.exec("killall app_monitor.sh")
        await self.exec(
            "killall Lumi_Z3GatewayHost_MQTT ser2net socat; pkill -f log/z3"
        )

        if not self.app_patches:
            await self.exec(f"app_monitor.sh &")
            return 0

        await self.exec("cp /bin/app_monitor.sh /tmp")
        for patch in self.app_patches:
            await self.exec(patch.replace("daemon_app", "app_monitor"))

        await self.exec(f"/tmp/app_monitor.sh {self.mon_ps} &")

        return len(self.app_patches)

    async def apply_patches(self, ps: str) -> int:
        # stop old version
        if "log/miio" in ps:
            await self.exec("pkill -f log/miio")

        n = 0

        if self.ver >= "1.5.4_0036":
            if self.mon_ps not in ps:
                n += await self.update_app_monitor()
        elif self.ver >= "1.4.7_0000":
            if self.app_ps not in ps:
                n += await self.update_daemon_app()
            if self.miio_ps not in ps:
                n += await self.update_daemon_miio()
        else:
            n = -1

        return n
