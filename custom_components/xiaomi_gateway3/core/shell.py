import base64
import logging
import re
import time
from telnetlib import Telnet
from typing import Union

_LOGGER = logging.getLogger(__name__)

CHECK_SOCAT = "(md5sum /data/socat | grep 92b77e1a93c4f4377b4b751a5390d979)"
DOWNLOAD_SOCAT = "(curl -o /data/socat http://pkg.musl.cc/socat/mipsel-linux-musln32/bin/socat && chmod +x /data/socat)"
RUN_SOCAT = "/data/socat tcp-l:8888,reuseaddr,fork /dev/ttyS2"

CHECK_BUSYBOX = "(md5sum /data/busybox | grep 099137899ece96f311ac5ab554ea6fec)"
DOWNLOAD_BUSYBOX = "(curl -k -o /data/busybox https://busybox.net/downloads/binaries/1.21.1/busybox-mipsel && chmod +x /data/busybox)"
LOCK_FIRMWARE = "/data/busybox chattr +i /data/firmware.bin"
UNLOCK_FIRMWARE = "/data/busybox chattr -i /data/firmware.bin"
RUN_FTP = "(/data/busybox tcpsvd -vE 0.0.0.0 21 /data/busybox ftpd -w &)"

# use awk because buffer
MIIO_LESS = "-l 0 -o FILE_STORE -n 128"
MIIO_MORE = "-l 4"
MIIO2MQTT = "(miio_client %s -d /data/miio | awk '/%s/{print $0;fflush()}' | mosquitto_pub -t log/miio -l &)"

RE_VERSION = re.compile(r'version=([0-9._]+)')


class TelnetShell(Telnet):
    def __init__(self, host: str):
        super().__init__(host, timeout=5)
        self.read_until(b"login: ")
        self.exec('admin')

    def exec(self, command: str, as_bytes=False) -> Union[str, bytes]:
        """Run command and return it result."""
        self.write(command.encode() + b"\r\n")
        raw = self.read_until(b"\r\n# ")
        return raw if as_bytes else raw.decode()

    def check_or_download_socat(self):
        """Download socat if needed."""
        return self.exec(f"{CHECK_SOCAT} || {DOWNLOAD_SOCAT}")

    def run_socat(self):
        self.exec(f"{CHECK_SOCAT} && {RUN_SOCAT} &")

    def stop_socat(self):
        self.exec(f"killall socat")

    def run_lumi_zigbee(self):
        self.exec("daemon_app.sh &")

    def stop_lumi_zigbee(self):
        self.exec("killall daemon_app.sh; killall Lumi_Z3GatewayHost_MQTT")

    def check_or_download_busybox(self):
        return self.exec(f"{CHECK_BUSYBOX} || {DOWNLOAD_BUSYBOX}")

    def check_firmware_lock(self) -> bool:
        """Check if firmware update locked. And create empty file if needed."""
        raw = self.exec("touch /data/firmware.bin")
        return "Permission denied" in raw

    def lock_firmware(self, enable: bool):
        command = LOCK_FIRMWARE if enable else UNLOCK_FIRMWARE
        self.exec(f"{CHECK_BUSYBOX} && {command}")

    def run_ftp(self):
        self.exec(f"{CHECK_BUSYBOX} && {RUN_FTP}")

    def sniff_bluetooth(self):
        self.write(b"killall silabs_ncp_bt; silabs_ncp_bt /dev/ttyS1 1\r\n")

    def run_public_mosquitto(self):
        self.exec("killall mosquitto")
        time.sleep(.5)
        self.exec("mosquitto -d")
        time.sleep(.5)
        # fix CPU 90% full time bug
        self.exec("killall zigbee_gw")

    def get_running_ps(self) -> str:
        return self.exec("ps")

    def redirect_miio2mqtt(self, pattern: str, new_version=False):
        self.exec("killall daemon_miio.sh; killall miio_client")
        time.sleep(.5)
        args = MIIO_LESS if new_version else MIIO_MORE
        self.exec(MIIO2MQTT % (args, pattern))
        self.exec("daemon_miio.sh &")

    def run_public_zb_console(self):
        self.exec("killall daemon_app.sh; killall Lumi_Z3GatewayHost_MQTT")
        # run Gateway with open console port
        self.exec("Lumi_Z3GatewayHost_MQTT -n 1 -b 115200 -v -p '/dev/ttyS2' "
                  "-d '/data/silicon_zigbee_host/' > /dev/null &")

        # connect to console to start zigbee chip
        self.write(b"nc localhost 4901\r\n")
        time.sleep(2)
        # exit console (ctrl+c)
        self.write(b"\x03")
        self.read_until(b"\r\n# ")

        self.exec("daemon_app.sh &")

    def read_file(self, filename: str, as_base64=False):
        if as_base64:
            self.write(f"cat {filename} | base64\r\n".encode())
            self.read_until(b"\r\n")  # skip command
            raw = self.read_until(b"# ")
            return base64.b64decode(raw)
        else:
            self.write(f"cat {filename}\r\n".encode())
            self.read_until(b"\r\n")  # skip command
            return self.read_until(b"# ")[:-2]

    def run_buzzer(self):
        self.exec("killall basic_gw")

    def stop_buzzer(self):
        self.exec("killall daemon_miio.sh; killall -9 basic_gw")
        # run dummy process with same str in it
        self.exec("sh -c 'sleep 999d' dummy:basic_gw &")
        self.exec("daemon_miio.sh &")

    def get_version(self):
        raw = self.read_file('/etc/rootfs_fw_info')
        m = RE_VERSION.search(raw.decode())
        return m[1]
