import asyncio
import io
import logging
import socket
import time
from typing import Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.requirements import async_process_requirements

from . import shell
from .const import DOMAIN
from .shell.base import OPENMIIO_CMD

_LOGGER = logging.getLogger(__name__)


async def update_zigbee_firmware(hass: HomeAssistant, host: str, custom: bool):
    tar_fw = "6.7.10.0" if custom else "6.6.2.0"

    _LOGGER.debug(f"{host} [FWUP] Target zigbee firmware v{tar_fw}")

    session = shell.Session(host)

    try:
        await session.connect()
        sh = await session.login()
    except Exception as e:
        _LOGGER.error("Can't connect to gateway", exc_info=e)
        await session.close()
        return False

    try:
        await async_process_requirements(
            hass,
            DOMAIN,
            [
                "bellows>=0.29.0",
                "pyserial>=3.5",
                "pyserial-asyncio>=0.5",
            ],
        )

        await sh.exec(
            "zigbee_inter_bootloader.sh 1; zigbee_reset.sh 0; zigbee_reset.sh 1; "
            "killall openmiio_agent"
        )
        await sh.exec("/data/openmiio_agent --zigbee.tcp=8889 &")
        await asyncio.sleep(2)

        # some users have broken firmware, so unknown firmware also OK
        cur_fw = await read_firmware(host)
        if cur_fw and cur_fw.startswith(tar_fw):
            _LOGGER.debug(f"{host} [FWUP] No need to update")
            return True

        await sh.exec(
            "zigbee_inter_bootloader.sh 0; zigbee_reset.sh 0; zigbee_reset.sh 1; "
            "killall openmiio_agent"
        )
        await sh.exec("/data/openmiio_agent --zigbee.tcp=8889 --zigbee.baud=115200 &")

        await async_process_requirements(hass, DOMAIN, ["xmodem==0.4.6"])

        client = async_create_clientsession(hass)
        r = await client.get(
            "https://master.dl.sourceforge.net/project/mgl03/zigbee/mgl03_ncp_6_7_10_b38400_sw.gbl?viasf=1"
            if custom
            else "https://master.dl.sourceforge.net/project/mgl03/zigbee/ncp-uart-sw_mgl03_6_6_2_stock.gbl?viasf=1"
        )
        content = await r.read()

        ok = await hass.async_add_executor_job(flash_firmware, host, content)
        if not ok:
            return False

        await sh.exec(
            "zigbee_inter_bootloader.sh 1; zigbee_reset.sh 0; zigbee_reset.sh 1; "
            "killall openmiio_agent"
        )
        await sh.exec("/data/openmiio_agent --zigbee.tcp=8889 &")
        await asyncio.sleep(2)

        cur_fw = await read_firmware(host)
        return cur_fw and cur_fw.startswith(tar_fw)

    except Exception as e:
        _LOGGER.error(f"{host} [FWUP] Can't update firmware", exc_info=e)

    finally:
        await sh.exec(
            "zigbee_inter_bootloader.sh 1; zigbee_reset.sh 0; zigbee_reset.sh 1; "
            "killall openmiio_agent; " + OPENMIIO_CMD
        )
        await sh.close()


async def read_firmware(host: str) -> Optional[str]:
    from bellows.ezsp import EZSP

    ezsp = EZSP({"path": f"socket://{host}:8889", "baudrate": 0, "flow_control": None})
    try:
        # noinspection PyProtectedMember
        await asyncio.wait_for(ezsp._probe(), timeout=10)
        _, _, version = await ezsp.get_board_info()
    except Exception as e:
        _LOGGER.debug(f"{host} [FWUP] Read firmware error: {e}")
        return None
    finally:
        ezsp.close()

    _LOGGER.debug(f"{host} [FWUP] Current zigbee firmware v{version}")

    return version


def flash_firmware(host: str, content: bytes) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(3)
        sock.connect((host, 8889))

        sock.send(b"\x0A")

        if b"Gecko Bootloader v1.8.0" not in read(sock):
            _LOGGER.warning(f"{host} [FWUP] Not in boot before flash")
            return False

        sock.send(b"1")

        if b"CCC" not in read(sock):
            _LOGGER.warning(f"{host} [FWUP] Not in flash mode")
            return False

        # STATIC FUNCTIONS
        def getc(size, timeout=1):
            read_data = sock.recv(size)
            return read_data

        def putc(data, timeout=1):
            sock.send(data)
            time.sleep(0.001)

        # noinspection PyUnresolvedReferences
        from xmodem import XMODEM

        modem = XMODEM(getc, putc)
        modem.log = _LOGGER.getChild("xmodem")
        stream = io.BytesIO(content)

        if not modem.send(stream):
            _LOGGER.warning(f"{host} [FWUP] Xmodem send firmware fail")
            return False

        if b"Serial upload complete" not in read(sock):
            _LOGGER.warning(f"{host} [FWUP] Not in boot after flash")
            return False

        return True


def read(sock: socket) -> bytes:
    raw = b""

    t = time.time() + sock.gettimeout()
    while time.time() < t:
        try:
            b = sock.recv(1)
            if b == 0:
                break
            raw += b
        except socket.timeout:
            break

    return raw
