import asyncio
import base64
import hashlib
import logging
import re
import socket
from asyncio import StreamReader, StreamWriter
from typing import Union

_LOGGER = logging.getLogger(__name__)

# We should use HTTP-link because wget don't support HTTPS and curl removed in
# lastest fw. But it's not a problem because we check md5

# original link http://pkg.musl.cc/socat/mipsel-linux-musln32/bin/socat
# original link https://busybox.net/downloads/binaries/1.21.1/busybox-mipsel
WGET = "(wget http://master.dl.sourceforge.net/project/mgl03/{0}?viasf=1 -O /data/{1} && chmod +x /data/{1})"

CHECK_FIRMWARE = "/data/busybox lsattr /data/firmware/firmware_ota.bin"
LOCK_FIRMWARE = "mkdir -p /data/firmware && touch /data/firmware/firmware_ota.bin && /data/busybox chattr +i /data/firmware/firmware_ota.bin"
UNLOCK_FIRMWARE = "/data/busybox chattr -i /data/firmware/firmware_ota.bin"

RUN_FTP = "/data/busybox tcpsvd -E 0.0.0.0 21 /data/busybox ftpd -w &"
# flash on another ports because running ZHA or z2m can breake process
RUN_ZIGBEE_FLASH = "/data/ser2net -C '8115:raw:60:/dev/ttyS2:115200 8DATABITS NONE 1STOPBIT' -C '8038:raw:60:/dev/ttyS2:38400 8DATABITS NONE 1STOPBIT'"

TAR_DATA = b"tar -czOC /data basic_app basic_gw conf factory miio " \
           b"mijia_automation silicon_zigbee_host zigbee zigbee_gw " \
           b"ble_info miioconfig.db 2>/dev/null | base64\n"

MD5_BT = {
    # '1.4.6_0012': '367bf0045d00c28f6bff8d4132b883de',
    # '1.4.6_0043': 'c4fa99797438f21d0ae4a6c855b720d2',
    '1.4.7_0115': 'be4724fbc5223fcde60aff7f58ffea28',
    '1.4.7_0160': '9290241cd9f1892d2ba84074f07391d4',
    '1.5.0_0026': '9290241cd9f1892d2ba84074f07391d4',
    '1.5.0_0102': '9290241cd9f1892d2ba84074f07391d4',
    '1.5.1_0032': '9290241cd9f1892d2ba84074f07391d4',
}
MD5_BUSYBOX = '099137899ece96f311ac5ab554ea6fec'
# MD5_GW3 = 'c81b91816d4b9ad9bb271a5567e36ce9'  # alpha
MD5_SER2NET = 'f27a481e54f94ea7613b461bda090b0f'


def sed(app: str, pattern: str, repl: str):
    """sed with extended regex and edit file in-place"""
    repl = repl.replace('$', '\$').replace('&', '\&').replace('=', '\='). \
        replace('`', '\`').replace('"', '\\"').replace('\n', '\\n')
    return f'sed -r "s={pattern}={repl}=" -i /tmp/daemon_{app}.sh'


# grep output to cloud and send it to MQTT, use awk because buffer
PATCH_MIIO_MQTT = sed(
    "miio", "^ +miio_client .+$",
    "miio_client -l 0 -o FILE_STORE -d $MIIO_PATH -n 128 | awk '/ot_agent_recv_handler_one.+(ble_event|properties_changed|heartbeat)/{print $0;fflush()}' | mosquitto_pub -t log/miio -l &"
)
# use patched silabs_ncp_bt from sourceforge and send stderr to MQTT
PATCH_BLETOOTH_MQTT = sed(
    "miio", "^ +silabs_ncp_bt .+$",
    "/data/silabs_ncp_bt /dev/ttyS1 $RESTORE 2>&1 >/dev/null | mosquitto_pub -t log/ble -l &"
)

PATCH_ZIGBEE_PARENTS = sed(
    "app", "^ +(Lumi_Z3GatewayHost_MQTT [^>]+).+$",
    "\\1-l 0 | mosquitto_pub -t log/z3 -l &"
)

# replace default Z3 to ser2net
PATCH_ZIGBEE_TCP1 = sed(
    "app", "grep Lumi_Z3GatewayHost_MQTT", "grep ser2net"
)
PATCH_ZIGBEE_TCP2 = sed(
    "app", "^ +Lumi_Z3GatewayHost_MQTT .+$",
    "/data/ser2net -C '8888:raw:60:/dev/ttyS2:38400 8DATABITS NONE 1STOPBIT XONXOFF'"
)

# patch silabs_ncp_bt for storing data in tmp (memory)
PATCH_MEMORY_BLUETOOTH1 = "[ -d /tmp/miio ] || (cp -R /data/miio /tmp && cp /data/silabs_ncp_bt /tmp && sed -r 's=/data/=/tmp//=g' -i /tmp/silabs_ncp_bt)"
PATCH_MEMORY_BLUETOOTH2 = sed(
    "miio", "^/data/silabs_ncp_bt", "/tmp/silabs_ncp_bt"
)
# every 5 min sync sqlite DB from memory to NAND if changed
PATCH_MEMORY_BLUETOOTH3 = sed(
    "miio", "^\tdo$", """\tdo
if [ ${#N} -eq 60 ]; then
  if [ "`md5sum /tmp/miio/mible_local.db|cut -d' ' -f1`" != "`md5sum /data/miio/mible_local.db|cut -d' ' -f1`" ]; then
    cp /tmp/miio/mible_local.db /data/miio
    echo "`date` bluetooth" >> /var/log/storage_sync.log
  fi; N=
fi; N=$N.
"""
)

# move zigbee DB to tmp (memory)
PATCH_MEMORY_ZIGBEE1 = "[ -d /tmp/zigbee_gw ] || cp -R /data/zigbee_gw /tmp"
PATCH_MEMORY_ZIGBEE2 = sed(
    "app", "^ +zigbee_gw", "zigbee_gw -s /tmp/zigbee_gw/"
)
# every 5 min sync zigbee DB if device list changed
PATCH_MEMORY_ZIGBEE3 = sed(
    "app", "^\tdo$", """\tdo
if [ ${#N} -eq 60 ]; then
  if [ "`md5sum /tmp/zigbee_gw/device_properties.json|cut -d' ' -f1`" != "`md5sum /data/zigbee_gw/device_properties.json|cut -d' ' -f1`" ]; then
    cp /tmp/zigbee_gw/device_properties.json /data/zigbee_gw
    false | cp -i /tmp/zigbee_gw/*.json /data/zigbee_gw/ 2>/dev/null
    echo "`date` zigbee" >> /var/log/storage_sync.log
  fi; N=
fi; N=$N.
"""
)

# just for statistics
SAVE_SERIAL_STATS = "[ -f /tmp/serial ] || cp /proc/tty/driver/serial /tmp"

# if [ ! -e /tmp/bt_dont_need_startup ]; then
PATCH_DISABLE_BLUETOOTH = sed(
    "miio", "^ +if.+bt_dont_need_startup.+$", "if false; then"
)
PATCH_DISABLE_BUZZER1 = "[ -f /tmp/basic_gw ] || (cp /bin/basic_gw /tmp && sed -r 's=dev_query=xxx_query=' -i /tmp/basic_gw)"
PATCH_DISABLE_BUZZER2 = sed("miio", "^ +basic_gw", "/tmp/basic_gw")

SYNC_MEMORY_FILE = """[ "`md5sum /tmp/{0}|cut -d' ' -f1`" != "`md5sum /data/{0}|cut -d' ' -f1`" ] && cp /tmp/{0} /data/{0}"""

DB_BLUETOOTH = "`ls -1t /data/miio/mible_local.db /tmp/miio/mible_local.db 2>/dev/null | sed q`"
DB_ZIGBEE = "`ls -1t /data/zigbee_gw/* /tmp/zigbee_gw/* 2>/dev/null | sed -r 's/[^/]+$/*.json/;q'`"

# limited partial support on old firmwares
MIIO2MQTT_FW146 = "miio_client -l 4 -d /data/miio | awk '/ot_agent_recv_handler_one.+(ble_event|properties_changed|heartbeat)/{print $0;fflush()}' | mosquitto_pub -t log/miio -l &"


class TelnetShell:
    reader: StreamReader = None
    writer: StreamWriter = None

    ver: str = None

    async def connect(self, host: str, port=23) -> bool:
        try:
            coro = asyncio.open_connection(host, port, limit=1_000_000)
            self.reader, self.writer = await asyncio.wait_for(coro, 5)

            coro = self.reader.readuntil(b"login: ")
            await asyncio.wait_for(coro, 3)

            self.writer.write(b"admin\n")

            coro = self.reader.readuntil(b"\r\n# ")
            raw = await asyncio.wait_for(coro, timeout=3)
            if b'Password:' in raw:
                raise Exception("Telnet with password don't supported")

            self.writer.write(b"stty -echo\n")
            coro = self.reader.readuntil(b"# ")
            await asyncio.wait_for(coro, timeout=3)

            self.ver = await self.get_version()

            return True
        except:
            return False

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

    async def exec(self, command: str, as_bytes=False) -> Union[str, bytes]:
        """Run command and return it result."""
        self.writer.write(command.encode() + b"\n")
        coro = self.reader.readuntil(b"# ")
        raw = await asyncio.wait_for(coro, timeout=10)
        return raw[:-2] if as_bytes else raw[:-2].decode()

    async def read_file(self, filename: str, as_base64=False):
        command = f"cat {filename}|base64" if as_base64 else f"cat {filename}"
        try:
            raw = await self.exec(command, as_bytes=True)
            # b"cat: can't open ..."
            return base64.b64decode(raw) if as_base64 else raw
        except:
            return None

    async def check_bin(self, filename: str, md5: str, url=None) -> bool:
        """Check binary md5 and download it if needed."""
        if md5 in await self.exec("md5sum /data/" + filename):
            return True
        elif url:
            await self.exec(WGET.format(url, filename))
            return await self.check_bin(filename, md5)
        else:
            return False

    async def check_zigbee_tcp(self):
        return await self.check_bin('ser2net', MD5_SER2NET, 'bin/ser2net')

    async def run_zigbee_flash(self) -> bool:
        if not await self.check_zigbee_tcp():
            return False
        await self.exec("killall daemon_app.sh")
        await self.exec("killall Lumi_Z3GatewayHost_MQTT ser2net socat")
        await self.exec(RUN_ZIGBEE_FLASH)
        return True

    async def update_daemon_app(self, patches: list):
        await self.exec("killall daemon_app.sh")
        await self.exec(
            "killall Lumi_Z3GatewayHost_MQTT ser2net socat zigbee_gw; pkill -f log/z3"
        )

        if not patches:
            await self.exec(f"daemon_app.sh &")
            return

        await self.exec("cp /bin/daemon_app.sh /tmp")
        for patch in patches:
            await self.exec(patch)

        await self.exec(f"/tmp/daemon_app.sh {self.app_ps(patches)} &")

    async def update_daemon_miio(self, patches: list):
        """Run default daemon_miio if no patches. Or run patched daemon_miio
        with patches hash in process list.
        """
        await self.exec("killall daemon_miio.sh")
        await self.exec(
            "killall miio_client silabs_ncp_bt; killall -9 basic_gw; pkill -f 'log/ble|log/miio'"
        )

        if not patches:
            await self.exec(f"daemon_miio.sh &")
            return

        await self.exec("cp /bin/daemon_miio.sh /tmp")
        for patch in patches:
            await self.exec(patch)

        await self.exec(f"/tmp/daemon_miio.sh {self.miio_ps(patches)} &")

    async def memory_sync(self):
        resp = await self.exec(
            "ls --color=never /tmp/miio/mible_local.db /tmp/zigbee_gw/*"
        )
        for file in resp.split('\r\n'):
            if not file.startswith('/tmp/'):
                continue
            command = SYNC_MEMORY_FILE.format(file[5:])
            await self.exec(command)

    async def patch_miio_mqtt_fw146(self, ps: str):
        assert self.ver < "1.4.7_0000", self.ver
        if "-t log/miio" in ps:
            return
        await self.exec("killall daemon_miio.sh")
        await self.exec("killall miio_client; pkill -f log/miio")
        await asyncio.sleep(.5)
        await self.exec(MIIO2MQTT_FW146)
        await self.exec("daemon_miio.sh &")

    @staticmethod
    def app_ps(patches: list):
        if patches:
            return hashlib.md5('\n'.join(patches).encode()).hexdigest()
        return '/bin/daemon_app.sh'

    @staticmethod
    def miio_ps(patches: list):
        if patches:
            return hashlib.md5('\n'.join(patches).encode()).hexdigest()
        return '/bin/daemon_miio.sh'

    async def check_firmware_lock(self) -> bool:
        """Check if firmware update locked. And create empty file if needed."""
        resp = await self.exec(CHECK_FIRMWARE)
        return '-i-' in resp

    async def lock_firmware(self, enable: bool):
        if await self.check_bin('busybox', MD5_BUSYBOX, 'bin/busybox'):
            command = LOCK_FIRMWARE if enable else UNLOCK_FIRMWARE
            await self.exec(command)

    async def run_ftp(self):
        if await self.check_bin('busybox', MD5_BUSYBOX, 'bin/busybox'):
            await self.exec(RUN_FTP)

    async def reboot(self):
        # should not wait for response
        self.writer.write(b"reboot\n")
        await self.writer.drain()
        await asyncio.sleep(1)

    async def check_bt(self) -> bool:
        md5 = MD5_BT.get(self.ver)
        if not md5:
            return False
        # we use same name for bt utis so gw can kill it in case of update etc.
        return await self.check_bin(
            'silabs_ncp_bt', md5, md5 + '/silabs_ncp_bt'
        )

    async def run_public_mosquitto(self):
        await self.exec("killall mosquitto")
        await asyncio.sleep(.5)
        await self.exec("mosquitto -d")
        await asyncio.sleep(.5)
        # fix CPU 90% full time bug
        await self.exec("killall zigbee_gw")

    async def run_ntpd(self):
        await self.exec("ntpd -l")

    async def get_running_ps(self) -> str:
        return await self.exec("ps -ww | grep -v ' 0 SW'")

    async def tar_data(self):
        self.writer.write(TAR_DATA)
        coro = self.reader.readuntil(b"\r\n")
        await asyncio.wait_for(coro, timeout=3)  # skip command
        coro = self.reader.readuntil(b"# ")
        raw = await asyncio.wait_for(coro, timeout=10)
        return base64.b64decode(raw)

    async def get_version(self):
        raw = await self.read_file('/etc/rootfs_fw_info')
        m = re.search(r'version=([0-9._]+)', raw.decode())
        return m[1]

    async def get_token(self):
        raw = await self.read_file('/data/miio/device.token')
        return raw.rstrip().hex()

    async def get_did(self):
        raw = await self.read_file('/data/miio/device.conf')
        m = re.search(r'did=(\d+)', raw.decode())
        return m[1]

    async def get_wlan_mac(self) -> str:
        raw = await self.read_file('/sys/class/net/wlan0/address')
        return raw.decode().rstrip().upper()

    @property
    def mesh_group_table(self) -> str:
        return 'mesh_group_v3' if self.ver >= '1.4.7_0160' else 'mesh_group_v1'

    @property
    def mesh_device_table(self) -> str:
        return 'mesh_device_v3' if self.ver >= '1.4.7_0160' else 'mesh_device'


NTP_DELTA = 2208988800  # 1970-01-01 00:00:00
NTP_QUERY = b'\x1b' + 47 * b'\0'


def ntp_time(host: str) -> float:
    """Return server send time"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2)
    try:
        sock.sendto(NTP_QUERY, (host, 123))
        raw = sock.recv(1024)

        integ = int.from_bytes(raw[-8:-4], 'big')
        fract = int.from_bytes(raw[-4:], 'big')
        return integ + float(fract) / 2 ** 32 - NTP_DELTA
    except:
        return 0
    finally:
        sock.close()


def check_port(host: str, port: int):
    """Check if gateway port open."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        return s.connect_ex((host, port)) == 0
    finally:
        s.close()
