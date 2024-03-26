import asyncio
import logging
import re
import time
from functools import cached_property
from typing import Callable, TYPE_CHECKING, TypedDict, Optional

from .const import GATEWAY, ZIGBEE, BLE, MESH, GROUP
from .converters import silabs
from .converters.base import BaseConv, decode_time, encode_time
from .converters.lumi import LUMI_GLOBALS
from .converters.zigbee import ZConverter
from .devices import DEVICES

if TYPE_CHECKING:
    from .gate.base import XGateway

try:
    # noinspection PyUnresolvedReferences
    from xiaomi_gateway3 import DEVICES  # loading external converters
except ModuleNotFoundError:
    pass
except Exception as e:
    logger = logging.getLogger(__package__)
    logger.error("Can't load external converters", exc_info=e)


RE_NETWORK_MAC = re.compile(r"^[0-9a-f:]{17}$")  # lowercase hex with colons
RE_ZIGBEE_IEEE = re.compile(r"^[0-9a-f:]{23}$")  # lowercase hex with colons
RE_NWK = re.compile(r"^0x[0-9a-z]{4}$")  # lowercase hex with prefix 0x

BATTERY_AVAILABLE = 3 * 60 * 60  # 3 hours
POWER_AVAILABLE = 20 * 60  # 20 minutes
POWER_POLL = 9 * 60  # 9 minutes


class XDeviceExtra(TypedDict, total=False):
    # from Gateway:
    type: str  # one of GATEWAY, ZIGBEE, BLE, MESH, GROUP
    did: str  # device ID ("ble." "lumi." "group." "123")
    mac: str  # for GATEWAY, BLE, MESH (lowercase hex with colons)
    mac2: str  # lan mac for Xiaomi Multimode Gateway 2
    ieee: str  # for ZIGBEE (lowercase hex with colons, EUI64)
    nwk: str  # for ZIGBEE
    nwk_parent: str  # for ZIGBEE, NWK of parent device
    fw_ver: int  # firmware version for GATEWAY and ZIGBEE
    hw_ver: int  # hardware version for ZIGBEE
    childs: list[str]  # for mesh GROUP
    cloud_did: str  # for new ZIGBEE devices did will be "lumi", but cloud_did will be "123"
    seq: int  # BLE duplicate event check
    lqi: int  # for ZIGBEE
    rssi: int  # for GATEWAY, ZIGBEE, BLE, MESH
    # from DEVICES
    market_brand: str  # from DEVICES
    market_name: str  # from DEVICES
    market_model: str  # from DEVICES
    # from Cloud
    cloud_name: str  # device name from cloud
    cloud_fw: str  # device firmware from cloud
    # from YAML
    name: str  # device name override from YAML
    model: str  # device model override from YAML
    entity_name: str  # entity name override from YAML
    entities: dict[str, str | None] | bool  # custom domains for attr
    default_transition: float  # default transition for lights
    invert_state: bool  # invert state for binary sensors
    occupancy_timeout: list[float] | float  # occupancy timeout for motion


class XDevice:
    configs: dict[str, dict] = {}  # key is device.uid
    restore: dict[str, dict] = {}  # key is device.cloud_did

    converters: list[BaseConv]

    def __init__(self, model: str | int, **kwargs):
        self.available: bool = False
        self.gateways: list["XGateway"] = []
        self.extra: XDeviceExtra = kwargs
        self.listeners: list[Callable] = []
        self.model = model

        self.last_decode_gw: Optional["XGateway"] = None
        self.last_decode_ts: float = 0
        self.last_encode_ts: float = 0
        self.last_report: dict | None = None
        self.payload: dict | None = {}

        self.available_timeout: float = 0
        self.poll_timeout: float = 0

        self.assert_extra()
        self.init_defaults()
        self.init_converters()

        if self.available_timeout == 0:
            self.available = True
        elif self.last_decode_ts != 0:
            self.available = time.time() - self.last_decode_ts < self.available_timeout
        else:
            self.available = False

    # def __repr__(self) -> str:
    #     gw = sum(gw.available for gw in self.gateways)
    #     return (
    #         f"{self.type} {self.model} uid={self.uid} "
    #         f"av={self.available} gw={gw}/{len(self.gateways)}"
    #     )

    @cached_property
    def uid(self) -> str:
        """Universal Hass UID for devices."""
        if "mac" in self.extra:
            return self.extra["mac"].replace(":", "")
        if "ieee" in self.extra:
            return "0x" + self.extra["ieee"].replace(":", "")
        if "did" in self.extra:
            return self.extra["did"].replace(".", "")

    @cached_property
    def type(self) -> str:
        return self.extra.get("type") or "none"

    @cached_property
    def did(self) -> str:
        return self.extra["did"]

    @cached_property
    def cloud_did(self) -> str | None:
        """Cloud DID same as DID for most devices except new ZIGBEE."""
        return self.extra.get("cloud_did") or self.extra.get("did")

    @cached_property
    def nwk(self) -> str:
        return self.extra.get("nwk") or "0x0000"  # 0 - for GATEWAY

    @cached_property
    def ieee(self) -> str:
        return self.extra["ieee"]

    @cached_property
    def market_name(self) -> str:
        return f"{self.extra['market_brand']} {self.extra['market_name']}"

    @cached_property
    def miot_model(self) -> str | None:
        """Get device model for Xiaomi MiOT cloud."""
        if isinstance(self.model, str) and self.model.startswith("lumi."):
            return self.model  # for GATEWAY and ZIGBEE
        model = self.extra.get("market_model") or str(self.model)
        if m := re.search(r"[a-z0-9]+\.[a-z0-9_.]+", model):
            return m[0]

    @property
    def human_name(self) -> str:
        return (
            self.extra.get("name")  # from yaml
            or self.extra.get("cloud_name")  # from cloud
            or self.extra.get("market_name")  # from DEVICES
            or "Unknown " + self.type
        )

    @property
    def human_model(self) -> str:
        s = self.type.upper() if self.type == BLE else self.type.capitalize()
        if "market_model" in self.extra:
            s += ": " + self.extra["market_model"]
            if isinstance(self.model, str):
                s += ", " + self.model  # for GATEWAY and ZIGBEE
        else:
            s += f": {self.model}"
        return s

    @cached_property
    def firmware(self) -> str | None:
        return self.extra.get("fw_ver") or self.extra.get("cloud_fw")

    def as_dict(self, ts: float = None) -> dict[str, int | str | bool]:
        if ts is None:
            ts = time.time()

        data = {
            "available": self.available,
            "extra": self.extra,
            "listeners": len(self.listeners),
            "model": self.model,
            "ttl": encode_time(self.available_timeout),
            "uid": self.uid,
        }
        if self.last_decode_gw:
            data["last_decode_gw"] = self.last_decode_gw.as_dict()
        if self.last_decode_ts:
            data["last_decode"] = encode_time(ts - self.last_decode_ts)
        if self.last_encode_ts:
            data["last_encode"] = encode_time(ts - self.last_encode_ts)
        if len(self.gateways) > 1:
            data["gateways"] = ", ".join(i.device.uid for i in self.gateways)
        for k in ("last_report", "payload"):
            if v := getattr(self, k):
                data[k] = v

        return data

    def add_listener(self, handler: Callable):
        if handler not in self.listeners:
            self.listeners.append(handler)

    def dispatch(self, data: dict):
        """Notify all listeners with new data."""
        for handler in self.listeners:
            handler(data)

    def remove_listener(self, handler: Callable):
        if handler in self.listeners:
            self.listeners.remove(handler)

    def has_battery(self) -> bool:
        """Device has any converter with "battery" in name."""
        return any(i.attr.startswith("battery") for i in self.converters)

    def has_controls(self) -> bool:
        """Device has any non sensor entity."""
        return any("sensor" not in i.domain for i in self.converters if i.domain)

    def has_silabs(self) -> bool:
        """Device has any silabs (zigbee) converter."""
        return any(isinstance(i, ZConverter) for i in self.converters)

    def assert_extra(self):
        """Validate some extra fields."""
        if type := self.extra.get("type"):
            assert type in (GATEWAY, ZIGBEE, BLE, MESH, GROUP)
        if mac := self.extra.get("mac"):
            assert RE_NETWORK_MAC.match(mac), mac
        if ieee := self.extra.get("ieee"):
            assert RE_ZIGBEE_IEEE.match(ieee), ieee
        if did := self.extra.get("did"):
            if type == GATEWAY:
                assert did.isdecimal()
            elif type == ZIGBEE:
                assert did.startswith("lumi.")
            elif type == BLE:
                assert did.startswith("blt.")  # not sure if can be isdecimal()
            elif type == MESH:
                assert did.isdecimal()
            elif type == GROUP:
                assert did.startswith("group.")

    def init_defaults(self):
        # restore device setting based on cloud did
        if restore := XDevice.restore.get(self.cloud_did):
            if "cloud_name" in restore:
                self.extra["cloud_name"] = restore["cloud_name"]
            if "cloud_fw" in restore:
                self.extra["cloud_fw"] = restore["cloud_fw"]
            if "last_decode_ts" in restore:
                self.last_decode_ts = restore["last_decode_ts"]
        # init device extra from yaml config based on type, model, uid
        for k in (self.type, self.model, self.uid):
            if extra := XDevice.configs.get(k):
                self.extra.update(extra)

    def init_converters(self):
        # support custom model from yaml
        model = self.extra.get("model") or self.model

        for desc in DEVICES:
            # if this spec for current model
            if info := desc.get(model):
                self.extra["market_brand"] = info[0]
                self.extra["market_name"] = info[1]
                self.extra["market_model"] = ", ".join(info[2:])
                break
            # if this spec for current type
            if self.type == desc.get("default"):
                break
        else:
            self.converters = []
            return

        self.converters = desc["spec"]

        if self.type in (GATEWAY, GROUP):
            return

        # init available_timeout and poll_timeout
        if not self.has_battery():
            self.available_timeout = POWER_AVAILABLE
            self.poll_timeout = POWER_POLL
        else:
            self.available_timeout = BATTERY_AVAILABLE

        ttl = desc.get("ttl")
        if isinstance(ttl, str):
            ttl = decode_time(ttl)
        if ttl is not None:
            self.available_timeout = ttl

    def decode(self, data: dict | list) -> dict:
        """Decode data from device. Support only one item or list of items."""
        payload = {}
        if isinstance(data, list):
            for value in data:
                self.decode_one(payload, value)
        else:
            self.decode_one(payload, data)
        return payload

    def decode_one(self, payload: dict, value: dict):
        if "res_name" in value:
            self.decode_lumi(payload, value)
        elif "siid" in value:
            self.decode_miot(payload, value)
        elif "eid" in value:
            self.decode_mibeacon(payload, value)
        elif "clusterId" in value:
            self.decode_silabs(payload, value)

    def decode_lumi(self, payload: dict, value: dict):
        """Internal func for unpack one lumi or miio attribute."""
        if value.get("error_code", 0) != 0:
            return

        mi = value["res_name"]
        v = value["value"]

        if conv := LUMI_GLOBALS.get(mi):
            conv.decode(self, payload, v)

        for conv in self.converters:
            if conv.mi == mi:
                conv.decode(self, payload, v)

    def decode_miot(self, payload: dict, value: dict):
        if value.get("code", 0) != 0:
            return

        # {"cmd":"report","did":"lumi","params":[{"aiid":1,"in":[],"siid":8}]}
        if "piid" in value:
            # process property
            mi = f"{value['siid']}.p.{value['piid']}"
            for conv in self.converters:
                if conv.mi == mi:
                    conv.decode(self, payload, value["value"])
        elif "eiid" in value:
            # process event
            mi = f"{value['siid']}.e.{value['eiid']}"
            for conv in self.converters:
                if conv.mi == mi:
                    conv.decode(self, payload, None)
            # process event arguments properties
            for item in value["arguments"]:
                item.setdefault("siid", mi)
                self.decode_miot(payload, item)

    def decode_mibeacon(self, payload: dict, value: dict):
        for conv in self.converters:
            if conv.mi == value["eid"]:
                conv.decode(self, payload, value["edata"])

    def decode_silabs(self, payload: dict, value: dict):
        """Internal func for unpack Silabs MQTT message."""
        cluster_id = int(value["clusterId"], 0)
        endpoint = int(value["sourceEndpoint"], 0)
        v = None  # decode payload on demand

        for conv in self.converters:
            if (
                isinstance(conv, ZConverter)
                and conv.cluster_id == cluster_id
                and (conv.ep is None or conv.ep == endpoint)
            ):
                if v is None and not (v := silabs.decode(value)):
                    return
                conv.decode(self, payload, v)

    def encode(self, value: dict) -> dict:
        """Encode payload to supported spec, depends on attrs.

        @param value: dict with {attr: value} pairs
        @return: dict with `params` (lumi spec), `mi_spec` (miot spec),
            `commands` (zigbee spec)
        """
        payload = {}

        for k, v in value.items():
            for conv in self.converters:
                if conv.attr == k:
                    conv.encode(self, payload, v)

        return payload

    def encode_read(self, attrs: set) -> dict:
        payload = {}

        for conv in self.converters:
            if conv.attr in attrs:
                conv.encode_read(self, payload)

        return payload

    def on_report(self, data: dict | list, gw: "XGateway" = None) -> dict:
        """Process data from device."""
        if payload := self.decode(data):
            self.last_decode_gw = gw
            self.last_decode_ts = time.time()
            self.last_report = payload
            self.payload.update(payload)

            if not self.available:
                # update available and state with one step
                self.available = payload["available"] = True

            # log before dispatch
            gw.debug("on_report", device=self, data=payload)

            self.dispatch(payload)

        return payload

    @property
    def send_gateway(self) -> "XGateway":
        """Select best gateway for send command (write or read)."""
        if self.last_decode_gw in self.gateways and self.last_decode_gw.available:
            return self.last_decode_gw

        return next((i for i in self.gateways if i.available), None)

    def write(self, payload: dict):
        """Send write command to device."""
        if (gw := self.send_gateway) and (data := self.encode(payload)):
            self.last_encode_ts = time.time()
            gw.debug("write", device=self, data=payload)
            return asyncio.create_task(gw.write(self, data))

    def read(self, attrs: set = None):
        """Send read command to device."""
        if attrs is None:
            attrs = {i.attr for i in self.converters}

        if (gw := self.send_gateway) and (data := self.encode_read(attrs)):
            self.last_encode_ts = time.time()
            gw.debug("read", device=self, data=attrs)
            return asyncio.create_task(gw.read(self, data))

    def update(self, ts: float = None):
        """Update device available and state if necessary."""
        if ts is None:
            ts = time.time()

        # 1. Check if last message from device more than timeout
        # 2. Check if any device gateways available
        if self.available_timeout and ts - self.last_decode_ts > self.available_timeout:
            available = False
        elif not any(i.available for i in self.gateways):
            available = False
        else:
            available = True

        if self.available != available:
            self.available = available
            self.dispatch({"available": available})

        # 1. Check if device can be polled
        # 2. Check if last message from device more than timeout
        # 3. Check if last message to device more than timeout
        if (
            self.poll_timeout
            and ts - self.last_decode_ts > self.poll_timeout
            and ts - self.last_encode_ts > self.poll_timeout
        ):
            self.read()
