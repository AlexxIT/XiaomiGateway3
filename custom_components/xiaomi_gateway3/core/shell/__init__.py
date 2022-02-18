import asyncio
import socket
from typing import Union

from .base import TelnetShell
from .shell_e1 import ShellE1
from .shell_gw3 import ShellGw3


async def connect(host: str, port=23) -> Union[TelnetShell, ShellGw3, ShellE1]:
    """Return TelnetShell class for specific gateway. Returns the object in any
    case. To be able to execute the `close()` function.

    Example of usage:

        sh = None
        try:
            sh = await shell.connect(host)
            return True
        except Exception as e:
            return False
        finally:
            if sh:
                await sh.close()
    """
    coro = asyncio.open_connection(host, port, limit=1_000_000)
    reader, writer = await asyncio.wait_for(coro, 5)

    coro = reader.readuntil(b"login: ")
    resp: bytes = await asyncio.wait_for(coro, 3)

    if b"rlxlinux" in resp:
        shell = ShellGw3(reader, writer)
    elif b"Aqara-Hub-E1" in resp:
        shell = ShellE1(reader, writer)
    else:
        raise NotImplementedError

    await shell.login()
    await shell.prepare()

    return shell


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
