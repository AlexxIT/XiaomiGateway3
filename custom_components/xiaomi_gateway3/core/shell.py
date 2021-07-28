import base64
import logging
import re
import time
from socket import socket, AF_INET, SOCK_DGRAM
from telnetlib import Telnet
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
}
MD5_BUSYBOX = '099137899ece96f311ac5ab554ea6fec'
# MD5_GW3 = 'c81b91816d4b9ad9bb271a5567e36ce9'  # alpha
MD5_SOCAT = '92b77e1a93c4f4377b4b751a5390d979'


class TelnetShell(Telnet):
    def __init__(self, host: str):
        super().__init__(host, timeout=3)

        self.read_until(b"login: ", timeout=3)
        # some users have problems with \r\n symbols in login
        self.write(b"admin\n")

        raw = self.read_until(b"\r\n# ", timeout=3)
        if b'Password:' in raw:
            raise Exception("Telnet with password don't supported")

        self.ver = self.get_version()

    def exec(self, command: str, as_bytes=False) -> Union[str, bytes]:
        """Run command and return it result."""
        self.write(command.encode() + b"\n")
        raw = self.read_until(b"\r\n# ", timeout=10)
        return raw if as_bytes else raw.decode()

    def check_bin(self, filename: str, md5: str, url=None) -> bool:
        """Check binary md5 and download it if needed."""
        if md5 in self.exec("md5sum /data/" + filename):
            return True
        elif url:
            self.exec(WGET.format(url, filename))
            return self.check_bin(filename, md5)
        else:
            return False

    # def check_gw3(self):
    #     return self.check_bin('gw3', MD5_GW3)

    # def run_gw3(self, params=''):
    #     if self.check_bin('gw3', MD5_GW3, 'gw3/' + MD5_GW3):
    #         self.exec(f"/data/gw3 {params}&")

    # def stop_gw3(self):
    #     self.exec(f"killall gw3")

    def run_zigbee_tcp(self, port=8888):
        if self.check_bin('socat', MD5_SOCAT, 'bin/socat'):
            self.exec(RUN_ZIGBEE_TCP % port)

    def stop_zigbee_tcp(self):
        # stop both 8888 and 8889
        self.exec("pkill -f 'tcp-l:888'")

    def run_lumi_zigbee(self):
        self.exec("daemon_app.sh &")

    def stop_lumi_zigbee(self):
        self.exec("killall daemon_app.sh")
        self.exec("killall Lumi_Z3GatewayHost_MQTT")

    def check_firmware_lock(self) -> bool:
        """Check if firmware update locked. And create empty file if needed."""
        self.exec("mkdir -p /data/firmware")
        locked = [
            "Permission denied" in self.exec("touch " + path)
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

    def check_bt(self) -> bool:
        md5 = MD5_BT.get(self.ver)
        if not md5:
            return False
        # we use same name for bt utis so gw can kill it in case of update etc.
        return self.check_bin('silabs_ncp_bt', md5, md5 + '/silabs_ncp_bt')

    def run_bt(self):
        self.exec(
            "killall silabs_ncp_bt; pkill -f log/ble; "
            "/data/silabs_ncp_bt /dev/ttyS1 1 2>&1 >/dev/null | "
            "mosquitto_pub -t log/ble -l &"
        )

    def sniff_bluetooth(self):
        """Deprecated"""
        self.write(b"killall silabs_ncp_bt; silabs_ncp_bt /dev/ttyS1 1\n")

    def run_public_mosquitto(self):
        self.exec("killall mosquitto")
        time.sleep(.5)
        self.exec("mosquitto -d")
        time.sleep(.5)
        # fix CPU 90% full time bug
        self.exec("killall zigbee_gw")

    def run_ntpd(self):
        self.exec("ntpd -l")

    def get_running_ps(self) -> str:
        return self.exec("ps -w")

    def redirect_miio2mqtt(self, pattern: str):
        self.exec("killall daemon_miio.sh")
        self.exec("miio_client; pkill -f log/miio")
        time.sleep(.5)
        cmd = MIIO_147 if self.ver >= '1.4.7_0063' else MIIO_146
        self.exec(cmd + MIIO2MQTT % pattern)
        self.exec("daemon_miio.sh &")

    def run_public_zb_console(self):
        # Z3 starts with tail on old fw and without it on new fw from 1.4.7
        self.exec("killall daemon_app.sh")
        self.exec("tail Lumi_Z3GatewayHost_MQTT")

        # run Gateway with open console port (`-v` param)
        arg = " -r 'c'" if self.ver >= '1.4.7_0063' else ''

        # use `tail` because input for Z3 is required;
        # add `-l 0` to disable all output, we'll enable it later with
        # `debugprint on 1` command
        self.exec(
            "nohup tail -f /dev/null 2>&1 | "
            "nohup Lumi_Z3GatewayHost_MQTT -n 1 -b 115200 -l 0 "
            f"-p '/dev/ttyS2' -d '/data/silicon_zigbee_host/'{arg} 2>&1 | "
            "mosquitto_pub -t log/z3 -l &"
        )

        self.exec("daemon_app.sh &")

    def read_file(self, filename: str, as_base64=False):
        if as_base64:
            self.write(f"cat {filename} | base64\n".encode())
            self.read_until(b"\r\n", timeout=3)  # skip command
            raw = self.read_until(b"# ", timeout=10)
            # b"cat: can't open ..."
            return base64.b64decode(raw)
        else:
            self.write(f"cat {filename}\n".encode())
            self.read_until(b"\r\n", timeout=3)  # skip command
            return self.read_until(b"# ", timeout=10)[:-2]

    def tar_data(self):
        self.write(TAR_DATA)
        self.read_until(b"base64\r\n", timeout=3)  # skip command
        raw = self.read_until(b"# ", timeout=30)
        return base64.b64decode(raw)

    def run_buzzer(self):
        self.exec("kill $(ps | grep dummy:basic_gw | awk '{print $1}')")

    def stop_buzzer(self):
        self.exec("killall daemon_miio.sh; killall -9 basic_gw")
        # run dummy process with same str in it
        self.exec("sh -c 'sleep 999d' dummy:basic_gw &")
        self.exec("daemon_miio.sh &")

    def get_version(self):
        raw = self.read_file('/etc/rootfs_fw_info')
        m = RE_VERSION.search(raw.decode())
        return m[1]

    def get_token(self):
        return self.read_file('/data/miio/device.token').rstrip().hex()

    def get_did(self):
        raw = self.read_file('/data/miio/device.conf').decode()
        m = re.search(r'did=(\d+)', raw)
        return m[1]

    def get_wlan_mac(self) -> str:
        raw = self.read_file('/sys/class/net/wlan0/address')

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
