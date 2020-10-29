import base64
import logging
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

MIIO_PTRN = "ble_event|properties_changed"
# use awk because buffer
MIIO2MQTT = f"(miio_client -l 4 -d /data/miio | awk '/{MIIO_PTRN}/{{print $0;fflush()}}' | mosquitto_pub -t log/miio -l &)"


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
        self.exec(f"{CHECK_SOCAT} && {RUN_SOCAT}")

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

    def sniff_bluetooth(self):
        self.write(b"killall silabs_ncp_bt; silabs_ncp_bt /dev/ttyS1 1\r\n")

    def run_public_mosquitto(self):
        self.exec("killall mosquitto; sleep .5; mosquitto -d")
        time.sleep(.5)
        self.exec("mosquitto -d")
        time.sleep(.5)
        # fix CPU 90% full time bug
        self.exec("killall zigbee_gw")

    def get_running_ps(self) -> str:
        return self.exec("ps")

    def redirect_miio2mqtt(self):
        self.exec("killall daemon_miio.sh; killall miio_client")
        time.sleep(.5)
        self.exec(MIIO2MQTT)
        self.exec("daemon_miio.sh &")

    def run_public_zb_console(self):
        self.exec("killall daemon_app.sh; killall Lumi_Z3GatewayHost_MQTT")
        self.exec("Lumi_Z3GatewayHost_MQTT -n 1 -b 115200 -v -p '/dev/ttyS2' "
                  "-d '/data/silicon_zigbee_host/' &")
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
