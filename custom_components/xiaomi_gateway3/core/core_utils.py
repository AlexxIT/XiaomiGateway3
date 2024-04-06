import asyncio
import base64
import hashlib
import hmac
import random
import socket

from .const import SUPPORTED_MODELS, PID_BLE
from .mini_miio import AsyncMiIO
from .shell.session import Session
from .xiaomi_cloud import MiCloud


async def check_port(host: str, port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        ok = await asyncio.get_event_loop().run_in_executor(
            None, s.connect_ex, (host, port)
        )
        return ok == 0
    finally:
        s.close()


async def gateway_info(host: str, token: str = None, key: str = None) -> dict | None:
    # Strategy:
    # 1. Check open telnet and return host, did, token, key
    # 2. Try to enable telnet using host, token and (optionaly) key
    # 3. Check open telnet again
    # 4. Return error
    try:
        async with Session(host) as sh:
            info = await sh.get_miio_info()
        info["host"] = host
        return info
    except:
        pass

    if not token:
        return None

    # try to enable telnet and return miio info
    result = await enable_telnet(host, token, key)

    # waiting for telnet to start
    await asyncio.sleep(1)

    # call with empty token so only telnet will check
    if info := await gateway_info(host):
        return info

    # result ok, but telnet can't be opened
    return {"error": "wrong_telnet" if result == "ok" else result}


# universal command for open telnet on all models
TELNET_CMD = "passwd -d $USER; riu_w 101e 53 3012 || echo enable > /sys/class/tty/tty/enable; telnetd"


async def enable_telnet(host: str, token: str, key: str = None) -> str:
    # Strategy:
    # 1. Get miio info
    miio = AsyncMiIO(host, token)
    if miio_info := await miio.info():
        model: str = miio_info.get("model")
        fwver: str = miio_info.get("fw_ver")
        # 2. Send different telnet cmd based on gateway model and firmware
        if model == "lumi.gateway.mgl03":
            if fwver < "1.4.6_0043":
                methods = ["enable_telnet_service"]
            elif fwver < "1.5.5":
                methods = ["set_ip_info"]
            else:
                methods = ["system_command"]
        elif model in ("lumi.gateway.aqcn02", "lumi.gateway.aqcn03"):
            methods = ["set_ip_info" if fwver < "4.0.4" else "system_command"]
        elif model in ("lumi.gateway.mcn001", "lumi.gateway.mgl001"):
            methods = ["set_ip_info" if fwver < "1.0.7" else "system_command"]
        else:
            return "wrong_model"

        if "system_command" in methods and len(key or "") != 16:
            return "no_key"
    else:
        # 3. Send all open telnet cmd if we can't get miio info
        # PS. Can't try `system_command` without `miio_info`
        methods = ["set_ip_info", "enable_telnet_service"]

    # 4. Return ok or some error
    for method in methods:
        if method == "enable_telnet_service":
            params = None
        elif method == "set_ip_info":
            params = {"ssid": '""', "pswd": "1; " + TELNET_CMD}
        elif method == "system_command":
            params = {
                "password": miio_password(miio.device_id, miio_info["mac"], key),
                "command": TELNET_CMD,
            }
        else:
            raise NotImplementedError(method)

        res = await miio.send(method, params, tries=1)
        # set_ip_info: {'result': ['ok']}
        # system_command: {'result': ['ok']}
        # system_command: {'error': {'code': -4004, 'message': 'inner error'}}
        if res and res.get("result") == ["ok"]:
            return "ok"

    if miio_info:
        return "wrong_telnet"

    if miio_info is not None:
        return "wrong_token"

    return "cant_connect"


def miio_password(did: str, mac: str, key: str) -> str:
    secret = hashlib.sha256(f"{did}{mac}{key}".encode()).hexdigest()
    dig = hmac.new(secret.encode(), msg=key.encode(), digestmod=hashlib.sha256).digest()
    return base64.b64encode(dig)[-16:].decode()


async def get_device_info(cloud: MiCloud, device: dict) -> dict:
    info = {"Name": device["name"], "Model": device["model"], "MAC": device["mac"]}

    if device["pid"] != PID_BLE:
        info["IP"] = device["localip"]
        info["Token"] = device["token"]
    else:
        bindkey = await cloud.get_bindkey(device["did"])
        info["Bindkey"] = bindkey or "Can't get from cloud"

    if fw_version := device["extra"].get("fw_version"):
        info["Firmware"] = fw_version

    if device["model"] in SUPPORTED_MODELS:
        gw_info = await gateway_info(device["localip"], device["token"])
        if error := gw_info.get("error"):
            info["Telnet"] = error
        else:
            info["Firmware"] = gw_info["version"]
            info["Key"] = gw_info["key"]
            info["Telnet"] = "open"
    elif device["model"] == "lumi.gateway.v3":
        info["LAN Key"] = await get_lan_key(device["localip"], device["token"])
    elif ".vacuum." in device["model"]:
        info["Rooms"] = await get_room_mapping(
            cloud, device["localip"], device["token"]
        )
    elif device["model"] == "yeelink.light.bslamp2":
        info["LAN mode"] = await enable_bslamp2_lan(device["localip"], device["token"])
    elif device["model"].startswith("yeelink.light."):
        info["Remotes"] = await get_ble_remotes(device["localip"], device["token"])

    return info


async def get_lan_key(host: str, token: str):
    device = AsyncMiIO(host, token)
    resp = await device.send("get_lumi_dpf_aes_key")
    if not resp:
        return "Can't connect to gateway"
    if "result" not in resp:
        return f"Wrong response: {resp}"
    resp = resp["result"]
    if len(resp[0]) == 16:
        return resp[0]
    key = "".join(
        random.choice("abcdefghijklmnopqrstuvwxyz01234567890") for _ in range(16)
    )
    resp = await device.send("set_lumi_dpf_aes_key", [key])
    if resp.get("result") == ["ok"]:
        return key
    return "Can't update gateway key"


async def get_room_mapping(cloud: MiCloud, host: str, token: str):
    try:
        device = AsyncMiIO(host, token)
        local_rooms = await device.send("get_room_mapping")
        cloud_rooms = await cloud.get_rooms()
        result = ""
        for local_id, cloud_id in local_rooms["result"]:
            cloud_name = next(
                (p["name"] for p in cloud_rooms if p["id"] == cloud_id), "-"
            )
            result += f"\n- {local_id}: {cloud_name}"
        return result

    except:
        return "Can't get from cloud"


async def enable_bslamp2_lan(host: str, token: str):
    device = AsyncMiIO(host, token)
    resp = await device.send("get_prop", ["lan_ctrl"])
    if not resp:
        return "Can't connect to lamp"
    if resp.get("result") == ["1"]:
        return "Already enabled"
    resp = await device.send("set_ps", ["cfg_lan_ctrl", "1"])
    if resp.get("result") == ["ok"]:
        return "Enabled"
    return "Can't enable LAN"


async def get_ble_remotes(host: str, token: str):
    device = AsyncMiIO(host, token)
    resp = await device.send("ble_dbg_tbl_dump", {"table": "evtRuleTbl"})
    if not resp:
        return "Can't connect to lamp"
    if "result" not in resp:
        return f"Wrong response"
    return "\n".join(
        [f"{p['beaconkey']} ({format_mac(p['mac'])})" for p in resp["result"]]
    )


def format_mac(s: str) -> str:
    return f"{s[10:]}:{s[8:10]}:{s[6:8]}:{s[4:6]}:{s[2:4]}:{s[:2]}".upper()
