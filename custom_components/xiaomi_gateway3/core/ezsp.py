import io
import logging
import socket
import time
from typing import Optional

from ..util.elelabs_ezsp_utility import EzspProtocolInterface

_LOGGER = logging.getLogger(__name__)


class EzspUtils:
    sock: socket = None
    version: str = None
    # used in EzspProtocolInterface, values: 'ASH' or 'EZSP'
    dlevel = None

    def __init__(self):
        self.ezsp = EzspProtocolInterface(self, self, _LOGGER)

    def connect(self, host: str, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5)
        self.sock.connect((host, port))

    def flushInput(self):
        pass

    def write(self, data: bytes):
        self.sock.send(data)

    def read(self, size: int = 1):
        try:
            return self.sock.recv(size)
        except:
            return b''

    def readline(self):
        ts = time.time() + self.sock.gettimeout()
        c = None
        raw = b''
        while c != b'\n' and c != b'' and time.time() < ts:
            c = self.read()
            raw += c
        return raw

    def close(self):
        self.sock.close()

    def state(self) -> Optional[str]:
        try:
            resp = self.ezsp.initEzspProtocol()
        except:
            _LOGGER.debug("NCP init error")
            return None

        if resp == 0:
            resp, _, v = \
                self.ezsp.getValue(self.ezsp.EZSP_VALUE_VERSION_INFO, "VER")
            if resp != 0:
                _LOGGER.debug("NCP get version error")
                return None

            self.version = f"NCP v{v[2]}.{v[3]}.{v[4]}-{v[0]}"
            return "normal"
        else:
            # check if allready in bootloader mode
            self.write(b'\x0A')
            first_line = self.readline()  # read blank line
            if first_line != b'\r\n':
                _LOGGER.debug(f"NCP first line error: {first_line}")
                return None

            # read b'Gecko Bootloader v1.8.0\r\n'
            self.version = self.readline().decode().strip()
            return "boot"

    def launch_boot(self):
        assert self.version.startswith("NCP"), self.version

        resp = self.ezsp.launchStandaloneBootloader(
            self.ezsp.STANDALONE_BOOTLOADER_NORMAL_MODE, "BOOT"
        )
        if resp != 0:
            _LOGGER.debug("NCP launch boot error")
            raise RuntimeError

        time.sleep(2)

    def reboot_and_close(self):
        # we should be in bootloader
        assert self.version.startswith("Gecko Bootloader"), self.version

        self.write(b'2')  # send reboot
        self.close()  # we need disconnect after reboot
        time.sleep(2)

    def flash_and_close(self, file: bytes) -> bool:
        assert self.version.startswith("Gecko Bootloader"), self.version

        # STATIC FUNCTIONS
        def getc(size, timeout=1):
            read_data = self.read(size)
            return read_data

        def putc(data, timeout=1):
            self.write(data)
            time.sleep(0.001)

        # Enter '1' to initialize X-MODEM mode
        self.write(b'\x0A')
        self.write(b'1')

        # Wait for char 'C'
        success = False
        start_time = time.time()
        while time.time() - start_time < 10:
            if self.read() == b'C':
                success = True
                if time.time() - start_time > 5:
                    break
        if not success:
            return False

        from xmodem import XMODEM
        modem = XMODEM(getc, putc)
        modem.log = _LOGGER.getChild('xmodem')
        stream = io.BytesIO(file)
        if modem.send(stream):
            _LOGGER.debug('Firmware upload complete')
        else:
            return False
        _LOGGER.debug('Rebooting NCP...')

        self.close()  # better to close after flash
        time.sleep(4)

        return True
