import asyncio
import base64
import logging
import re
from asyncio import StreamReader, StreamWriter
from socket import socket, AF_INET, SOCK_DGRAM
from typing import Union

_LOGGER = logging.getLogger(__name__)

# We should use HTTP-link because wget don't support HTTPS and curl removed in
# lastest fw. But it's not a problem because we check md5

# original link http://pkg.musl.cc/socat/mipsel-linux-musln32/bin/socat
# original link https://busybox.net/downloads/binaries/1.21.1/busybox-mipsel
WGET = "(wget http://master.dl.sourceforge.net/project/mgl03/{0}?viasf=1 " \
       "-O /data/{1} && chmod +x /data/{1})"

RUN_ZIGBEE_TCP = "/data/socat tcp-l:%d,reuseaddr,fork,keepalive,nodelay," \
                 "keepidle=1,keepintvl=1,keepcnt=5 /dev/ttyS2,raw,echo=0 &"

LOCK_FIRMWARE = "/data/busybox chattr +i "
UNLOCK_FIRMWARE = "/data/busybox chattr -i "
RUN_FTP = "/data/busybox tcpsvd -E 0.0.0.0 21 /data/busybox ftpd -w &"

# use awk because buffer
MIIO_147 = "miio_client -l 0 -o FILE_STORE -n 128 -d /data/miio"
MIIO_146 = "miio_client -l 4 -d /data/miio"
MIIO2MQTT = " | awk '/%s/{print $0;fflush()}' | mosquitto_pub -t log/miio -l &"

RE_VERSION = re.compile(r'version=([0-9._]+)')

FIRMWARE_PATHS = ('/data/firmware.bin', '/data/firmware/firmware_ota.bin')

TAR_DATA = b"tar -czOC /data basic_app basic_gw conf factory miio " \
           b"mijia_automation silicon_zigbee_host zigbee zigbee_gw " \
           b"ble_info miioconfig.db 2>/dev/null | base64\n"

MD5_BT = {
    '1.4.6_0012': '367bf0045d00c28f6bff8d4132b883de',
    '1.4.6_0043': 'c4fa99797438f21d0ae4a6c855b720d2',
    '1.4.7_0115': 'be4724fbc5223fcde60aff7f58ffea28',
    '1.4.7_0160': '9290241cd9f1892d2ba84074f07391d4',
    '1.5.0_0026': '9290241cd9f1892d2ba84074f07391d4',
    '1.5.0_0102': '9290241cd9f1892d2ba84074f07391d4',
}
MD5_BUSYBOX = '099137899ece96f311ac5ab554ea6fec'
# MD5_GW3 = 'c81b91816d4b9ad9bb271a5567e36ce9'  # alpha
MD5_SOCAT = '92b77e1a93c4f4377b4b751a5390d979'


class TelnetShell:
    reader: StreamReader = None
    writer: StreamWriter = None

    ver: str = None

    async def connect(self, host: str, port=23) -> bool:
        try:
            coro = asyncio.open_connection(host, port, limit=1_000_000)
            self.reader, self.writer = await asyncio.wait_for(coro, 5)
            return True
        except:
            return False

    async def close(self):
        self.writer.close()
        await self.writer.wait_closed()

    async def login(self) -> bool:
        try:
            coro = self.reader.readuntil(b"login: ")
            await asyncio.wait_for(coro, 3)

            self.writer.write(b"admin\n")

            coro = self.reader.readuntil(b"\r\n# ")
            raw = await asyncio.wait_for(coro, timeout=3)
            if b'Password:' in raw:
                raise Exception("Telnet with password don't supported")

            self.ver = await self.get_version()

            return True
        except:
            return False

    async def exec(self, command: str, as_bytes=False) -> Union[str, bytes]:
        """Run command and return it result."""
        self.writer.write(command.encode() + b"\n")
        coro = self.reader.readuntil(b"\r\n# ")
        raw = await asyncio.wait_for(coro, timeout=10)
        return raw if as_bytes else raw.decode()

    async def check_bin(self, filename: str, md5: str, url=None) -> bool:
        """Check binary md5 and download it if needed."""
        if md5 in await self.exec("md5sum /data/" + filename):
            return True
        elif url:
            await self.exec(WGET.format(url, filename))
            return await self.check_bin(filename, md5)
        else:
            return False

    # def check_gw3(self):
    #     return self.check_bin('gw3', MD5_GW3)

    # def run_gw3(self, params=''):
    #     if self.check_bin('gw3', MD5_GW3, 'gw3/' + MD5_GW3):
    #         self.exec(f"/data/gw3 {params}&")

    # def stop_gw3(self):
    #     self.exec(f"killall gw3")

    async def run_zigbee_tcp(self, port=8888):
        if await self.check_bin('socat', MD5_SOCAT, 'bin/socat'):
            await self.exec(RUN_ZIGBEE_TCP % port)

    async def stop_zigbee_tcp(self):
        # stop both 8888 and 8889
        await self.exec("pkill -f 'tcp-l:888'")

    async def run_lumi_zigbee(self):
        await self.exec("daemon_app.sh &")

    async def stop_lumi_zigbee(self):
        # Z3 starts with tail on old fw and without it on new fw from 1.4.7
        await self.exec("killall daemon_app.sh")
        await self.exec("killall tail Lumi_Z3GatewayHost_MQTT")

    async def check_firmware_lock(self) -> bool:
        """Check if firmware update locked. And create empty file if needed."""
        await self.exec("mkdir -p /data/firmware")
        locked = [
            "Permission denied" in await self.exec("touch " + path)
            for path in FIRMWARE_PATHS
        ]
        return all(locked)

    def lock_firmware(self, enable: bool):
        if self.check_bin('busybox', MD5_BUSYBOX, 'bin/busybox'):
            command = LOCK_FIRMWARE if enable else UNLOCK_FIRMWARE
            for path in FIRMWARE_PATHS:
                self.exec(command + path)

    def run_ftp(self):
        if self.check_bin('busybox', MD5_BUSYBOX, 'bin/busybox'):
            self.exec(RUN_FTP)

    async def check_bt(self) -> bool:
        md5 = MD5_BT.get(self.ver)
        if not md5:
            return False
        # we use same name for bt utis so gw can kill it in case of update etc.
        return await self.check_bin('silabs_ncp_bt', md5,
                                    md5 + '/silabs_ncp_bt')

    async def run_bt(self):
        await self.exec(
            "killall silabs_ncp_bt; pkill -f log/ble; "
            "/data/silabs_ncp_bt /dev/ttyS1 1 2>&1 >/dev/null | "
            "mosquitto_pub -t log/ble -l &"
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
        return await self.exec("ps -w")

    async def redirect_miio2mqtt(self, pattern: str):
        await self.exec("killall daemon_miio.sh")
        await self.exec("killall miio_client; pkill -f log/miio")
        await asyncio.sleep(.5)
        cmd = MIIO_147 if self.ver >= '1.4.7_0063' else MIIO_146
        await self.exec(cmd + MIIO2MQTT % pattern)
        await self.exec("daemon_miio.sh &")

    async def run_public_zb_console(self):
        await self.stop_lumi_zigbee()

        # add `-l 0` to disable all output, we'll enable it later with
        # `debugprint on 1` command
        if self.ver >= '1.4.7_0063':
            # nohub and tail fixed in latest fw
            await self.exec(
                "Lumi_Z3GatewayHost_MQTT -n 1 -b 115200 -l 0 -p '/dev/ttyS2' "
                "-d '/data/silicon_zigbee_host/' -r 'c' 2>&1 | "
                "mosquitto_pub -t log/z3 -l &"
            )
        else:
            # use `tail` because input for Z3 is required;
            await self.exec(
                "nohup tail -f /dev/null 2>&1 | "
                "nohup Lumi_Z3GatewayHost_MQTT -n 1 -b 115200 -l 0 "
                f"-p '/dev/ttyS2' -d '/data/silicon_zigbee_host/' 2>&1 | "
                "mosquitto_pub -t log/z3 -l &"
            )

        await self.run_lumi_zigbee()

    async def read_file(self, filename: str, as_base64=False):
        command = f"cat {filename} | base64\n" if as_base64 \
            else f"cat {filename}\r\n"

        self.writer.write(command.encode())

        coro = self.reader.readuntil(b"\r\n")
        await asyncio.wait_for(coro, timeout=3)  # skip command

        coro = self.reader.readuntil(b"# ")
        raw = await asyncio.wait_for(coro, timeout=10)

        try:
            # b"cat: can't open ..."
            return base64.b64decode(raw) if as_base64 else raw[:-2]
        except:
            return None

    async def tar_data(self):
        self.writer.write(TAR_DATA)
        coro = self.reader.readuntil(b"\r\n")
        await asyncio.wait_for(coro, timeout=3)  # skip command
        coro = self.reader.readuntil(b"# ")
        raw = await asyncio.wait_for(coro, timeout=10)
        return base64.b64decode(raw)

    async def run_buzzer(self):
        await self.exec("kill $(ps | grep dummy:basic_gw | awk '{print $1}')")

    async def stop_buzzer(self):
        await self.exec("killall daemon_miio.sh")
        await self.exec("killall -9 basic_gw")
        # run dummy process with same str in it
        await self.exec("sh -c 'sleep 999d' dummy:basic_gw &")
        await self.exec("daemon_miio.sh &")

    async def get_version(self):
        raw = await self.read_file('/etc/rootfs_fw_info')
        m = RE_VERSION.search(raw.decode())
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
        if self.ver >= '1.4.7_0160':
            return 'mesh_group_v3'
        elif self.ver >= '1.4.6_0043':
            return 'mesh_group_v1'
        else:
            return 'mesh_group'

    @property
    def mesh_device_table(self) -> str:
        if self.ver >= '1.4.7_0160':
            return 'mesh_device_v3'
        else:
            return 'mesh_device'

    @property
    def zigbee_db(self) -> str:
        # https://github.com/AlexxIT/XiaomiGateway3/issues/14
        # fw 1.4.6_0012 and below have one zigbee_gw.db file
        # fw 1.4.6_0030 have many json files in this folder
        return '/data/zigbee_gw/*.json' if self.ver >= '1.4.6_0030' \
            else '/data/zigbee_gw/zigbee_gw.db'


NTP_DELTA = 2208988800  # 1970-01-01 00:00:00
NTP_QUERY = b'\x1b' + 47 * b'\0'


def ntp_time(host: str) -> float:
    """Return server send time"""
    try:
        sock = socket(AF_INET, SOCK_DGRAM)
        sock.settimeout(2)

        sock.sendto(NTP_QUERY, (host, 123))
        raw = sock.recv(1024)

        integ = int.from_bytes(raw[-8:-4], 'big')
        fract = int.from_bytes(raw[-4:], 'big')
        return integ + float(fract) / 2 ** 32 - NTP_DELTA

    except:
        return 0
