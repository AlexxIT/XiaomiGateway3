import logging
import re
import time
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

from . import converters
from .converters import (
    Converter,
    LUMI_GLOBALS,
    GATEWAY,
    ZIGBEE,
    BLE,
    MESH,
    MESH_GROUP_MODEL,
)
from .converters.stats import STAT_GLOBALS

if TYPE_CHECKING:
    from .entity import XEntity
    from .gateway.base import GatewayBase

_LOGGER = logging.getLogger(__name__)

RE_DID = re.compile(r"^lumi.[1-9a-f][0-9a-f]{,15}$")
RE_ZIGBEE_MAC = re.compile(r"^0x[0-9a-f]{16}$")
RE_NETWORK_MAC = re.compile(r"^[0-9a-f]{12}$")
RE_NWK = re.compile(r"^0x[0-9a-z]{4}$")

BATTERY_AVAILABLE = 3 * 60 * 60  # 3 hours
POWER_AVAILABLE = 20 * 60  # 20 minutes
POWER_POLL = 9 * 60  # 9 minutes

# all legacy names for backward compatibility with 1st version
LEGACY_ATTR_ID = {
    "channel_1": "channel 1",
    "channel_2": "channel 2",
    "channel_3": "channel 3",
    "gas_density": "gas density",
    "group": "light",
    "outlet": "switch",
    "plug": "switch",
    "smoke_density": "smoke density",
}


class XDevice:
    converters: List[Converter] = None

    available_timeout: float = 0
    poll_timeout: float = 0
    decode_ts: float = 0
    encode_ts: float = 0

    _available: bool = None

    def __init__(
        self,
        type: str,
        model: Union[str, int, None],
        did: str,
        mac: str,
        nwk: str = None,
    ):
        """Base class to handle device of any type."""
        assert type in (GATEWAY, ZIGBEE, BLE, MESH)
        if type == ZIGBEE:
            assert isinstance(model, str) or model is None
            assert RE_DID.match(did)
            assert RE_ZIGBEE_MAC.match(mac)
            assert RE_NWK.match(nwk)
        elif type == BLE:
            assert isinstance(model, int)
            assert did.startswith("blt.") or did.isdecimal()
            assert RE_NETWORK_MAC.match(mac)
        elif model == MESH_GROUP_MODEL:
            assert did.startswith("group.")
        elif type == MESH:
            assert isinstance(model, int)
            assert did.isdecimal()
            assert RE_NETWORK_MAC.match(mac), mac
        elif type == GATEWAY:
            assert isinstance(model, str)
            assert did.isdecimal()
            assert RE_NETWORK_MAC.match(mac), mac

        # TODO: assert mac
        self.type = type
        self.model = model
        self.did = did
        self.mac = mac
        self.nwk = nwk

        # device brand, model, name and converters
        self.info = converters.get_device_info(model, type) if model else None
        # all device entities
        self.entities: Dict[str, "XEntity"] = {}
        # device gateways (one for GW and Zigbee), multiple for BLE and Mesh
        self.gateways: List["GatewayBase"] = []

        # internal device storage from any useful data
        self.extra: Dict[str, Any] = {}
        self.lazy_setup = set()

    def as_dict(self, ts: float) -> dict:
        resp = {k: getattr(self, k) for k in ("type", "model", "fw_ver", "available")}
        if self.decode_ts:
            resp["decode_time"] = round(ts - self.decode_ts)
        if self.encode_ts:
            resp["encode_time"] = round(ts - self.encode_ts)

        resp["entities"] = {
            attr: entity.hass_state for attr, entity in self.entities.items()
        }
        resp["gateways"] = [gw.device.unique_id for gw in self.gateways]

        if self.type in self.entities:
            resp["stats"] = self.entities[self.type].extra_state_attributes

        return resp

    @property
    def available(self):
        return self._available

    @available.setter
    def available(self, value: bool):
        if self._available == value:
            return
        self._available = value
        if self.entities:
            self.update_available()

    @property
    def unique_id(self) -> str:
        return self.extra.get("unique_id", self.mac)

    @property
    def name(self) -> str:
        return self.info.name if self.info else "Unknown"

    @property
    def fw_ver(self) -> Any:
        return self.extra.get("fw_ver")

    @property
    def ieee(self) -> str:
        """For Hass device connections."""
        return ":".join([self.mac[i : i + 2] for i in range(2, 18, 2)])

    @property
    def has_zigbee_conv(self) -> bool:
        if not self.converters:
            return False
        return any(True for conv in self.converters if conv.zigbee)

    def has_support(self, feature: str) -> bool:
        if feature == "zigbee":
            return self.type == ZIGBEE

        if feature == "zigbee+ble":
            return self.type in (ZIGBEE, BLE)

        if not self.model:
            return False

        if feature == "bind_from":
            # Aqara Opple support binding from
            if self.type == ZIGBEE and self.model.endswith("86opcn01"):
                return True

            conv = self.converters[0]
            return (
                conv.zigbee == "on_off"
                and conv.domain == "sensor"
                and getattr(conv, "bind", False)
            )

        if feature == "bind_to":
            conv = self.converters[0]
            return self.type == ZIGBEE and conv.domain in ("switch", "light")

    def update_model(self, value: str):
        # xiaomi soft adds tail to some models: .v1 or .v2 or .v3
        self.model = value[:-3] if value[-3:-1] == ".v" else value
        self.info = converters.get_device_info(self.model, self.type)

    def attr_unique_id(self, attr: str):
        return f"{self.unique_id}_{LEGACY_ATTR_ID.get(attr, attr)}"

    def attr_name(self, attr: str):
        # this words always uppercase
        if attr in ("ble", "led", "rssi", "usb"):
            return self.info.name + " " + attr.upper()

        attr = attr.replace("_", " ").title()

        # skip second attr in name if exists
        if attr in self.info.name:
            return self.info.name

        return self.info.name + " " + attr

    def entity_id(self, conv: Converter):
        name = self.extra.get("entity_name", self.mac)
        return f"{conv.domain}.{name}_{conv.attr}"

    # TODO: rename
    def subscribe_attrs(self, conv: Converter):
        attrs = {conv.attr}
        if conv.childs:
            attrs |= set(conv.childs)
        attrs.update(c.attr for c in self.converters if c.parent == conv.attr)
        return attrs

    def __str__(self):
        s = f"XDevice({self.type}, {self.model}, {self.mac}"
        s += f", {self.nwk})" if self.nwk else ")"
        return s

    def setup_entitites(self, gateway: "GatewayBase", stats: bool = False):
        """
        xiaomi_gateway3:
          devices:
            0x001234567890:  # match device by IEEE
              entities:
                plug: light            # change entity domain (switch to light)
                power:                 # disable default entity
                zigbee: sensor         # adds stat entity only for this device
                parent: sensor         # adds entity from attribute value
                lqi: sensor            # adds entity from attribute value
              model: lumi.plug.mitw01            # overwrite model
              name: Kitchen Refrigerator         # overwrite device name
              entity_name: kitchen_refrigerator  # overwrite entity name

        System kwargs:
          decode_ts - aka "last_seen" from device (stored in config folder)
          unique_id - ID legacy format from 1st version
          restore_entities - skip lazy status for exist entities
        """
        kwargs: Dict[str, Any] = {}

        if stats:
            kwargs["entities"] = {self.type: "sensor"}

        for key in (self.type, self.model, self.mac, self.did):
            if key in gateway.defaults:
                update(kwargs, gateway.defaults[key])

        if "decode_ts" in kwargs and self.decode_ts == 0:
            self.decode_ts = kwargs["decode_ts"]

        if "model" in kwargs:
            # support change device model in config
            self.update_model(kwargs["model"])

        if "name" in kwargs:
            # support set device name in config
            self.info.name = kwargs["name"]

        for k in ("entity_name", "unique_id"):
            if k in kwargs:
                self.extra[k] = kwargs[k]

        entities = kwargs.get("entities") or {}
        restore_entities = kwargs.get("restore_entities") or []

        self.setup_converters(entities)
        # update available before create entities
        self.setup_available()

        for conv in self.converters:
            # support change attribute domain in config
            domain = kwargs.get(conv.attr, conv.domain)
            if domain is None:
                continue
            if conv.enabled is None and conv.attr not in restore_entities:
                self.lazy_setup.add(conv.attr)
                continue
            gateway.setup_entity(domain, self, conv)

    def setup_converters(self, entities: dict = None):
        """If no entities - use only required converters. Otherwise search for
        converters in:
           - STAT_GLOBALS list
           - converters childs list (always sensor)
        """
        if entities is None:
            self.converters = self.info.spec
            return

        self.converters = self.info.spec.copy()

        for attr, domain in entities.items():
            if not isinstance(domain, str):
                continue
            if attr in STAT_GLOBALS:
                self.converters.append(STAT_GLOBALS[attr])
                continue
            for conv in self.converters:
                if conv.childs and attr in conv.childs:
                    conv = Converter(attr, domain)
                    self.converters.append(conv)

    def setup_available(self):
        # TODO: change to better logic?
        if self.type == GATEWAY or self.model == MESH_GROUP_MODEL:
            self.available = True
            return

        # TODO: change to better logic?
        if any(True for c in self.converters if c.attr == "battery"):
            self.available_timeout = self.info.ttl or BATTERY_AVAILABLE
        else:
            self.available_timeout = self.info.ttl or POWER_AVAILABLE
            self.poll_timeout = POWER_POLL

        self.available = (time.time() - self.decode_ts) < self.available_timeout

    def decode(self, attr_name: str, value: Any) -> Optional[dict]:
        """Find converter by attr_name and decode value."""
        for conv in self.converters:
            if conv.attr == attr_name:
                self.available = True
                self.decode_ts = time.time()

                payload = {}
                conv.decode(self, payload, value)
                return payload
        return None

    def decode_lumi(self, value: list) -> dict:
        """Decode value from Zigbee Lumi/MIoT spec."""
        payload = {}

        for param in value:
            # Lumi spec has `error_code`, MIoT spec has `code`
            if param.get("error_code", 0) != 0 or param.get("code", 0) != 0:
                continue
            if "value" in param:
                v = param["value"]
            else:
                v = param["arguments"]
                if v and "siid" in param:
                    # add siid to every argument
                    for item in param["arguments"]:
                        if "piid" in item or "eiid" in item and "siid" not in item:
                            item["siid"] = param["siid"]

            # res_name is Lumi format
            if "res_name" in param:
                prop = param["res_name"]
                conv: Converter = LUMI_GLOBALS.get(prop)
                if conv:
                    conv.decode(self, payload, v)
                    if conv.attr == "online":
                        return payload

            # piid or eiid is MIoT format
            elif "piid" in param:
                prop = f"{param['siid']}.p.{param['piid']}"
            elif "eiid" in param:
                prop = f"{param['siid']}.e.{param['eiid']}"
            else:
                raise RuntimeError

            self.available = True
            self.decode_ts = time.time()

            for conv in self.converters:
                if conv.mi == prop:
                    conv.decode(self, payload, v)

        return payload

    def decode_miot(self, value: list):
        """Decode value from Mesh MIoT spec."""
        if MESH in self.entities:
            self.update(self.decode(MESH, value))

        return self.decode_lumi(value)

    def decode_zigbee(self, value: dict) -> Optional[dict]:
        """Decode value from Zigbee spec."""
        self.available = True
        self.decode_ts = time.time()

        payload = {}
        for conv in self.converters:
            if conv.zigbee == value["cluster"]:
                conv.decode(self, payload, value)
        return payload

    def encode(self, value: dict) -> dict:
        """Encode payload to supported spec, depends on attrs.

        @param value: dict with {attr: value} pairs
        @return: dict with `params` (lumi spec), `mi_spec` (miot spec),
            `commands` (zigbee spec)
        """
        self.encode_ts = time.time()
        payload = {}
        for k, v in value.items():
            for conv in self.converters:
                if conv.attr == k:
                    conv.encode(self, payload, v)
        return payload

    def encode_read(self, attrs: set) -> dict:
        self.encode_ts = time.time()
        payload = {}
        for conv in self.converters:
            if conv.attr in attrs:
                conv.read(self, payload)
        return payload

    @property
    def powered(self) -> bool:
        return "sensor" not in self.converters[0].domain

    def update(self, value: dict):
        """Push new state to Hass entities."""
        if not value:
            return

        attrs = value.keys()

        if self.lazy_setup:
            for attr in self.lazy_setup & attrs:
                conv = next(c for c in self.converters if c.attr == attr)
                gateway = self.gateways[0]
                if conv.domain not in gateway.setups:
                    return
                self.lazy_setup.remove(attr)
                gateway.setups[conv.domain](gateway, self, conv)

        for entity in self.entities.values():
            if entity.subscribed_attrs & attrs:
                entity.async_set_state(value)
                # noinspection PyProtectedMember
                if entity.added:
                    entity.async_write_ha_state()

    def update_available(self):
        for entity in self.entities.values():
            entity.async_update_available()
            # noinspection PyProtectedMember
            if entity.added:
                entity.async_write_ha_state()


def update(orig_dict: dict, new_dict: dict):
    for k, v in new_dict.items():
        if isinstance(v, dict):
            orig_dict[k] = update(orig_dict.get(k, {}), v)
        elif isinstance(v, list):
            orig_dict[k] = orig_dict.get(k, []) + v
        else:
            orig_dict[k] = new_dict[k]
    return orig_dict


def logger_wrapper(func, log: deque, name: str = None):
    def wrap(*args):
        if not (name is None and args[0] == "ble"):
            ts = datetime.now().isoformat(timespec="milliseconds")
            log.append(
                {"ts": ts, "type": name, "value": args[0]}
                if name
                else {"ts": ts, "type": "decode_" + args[0], "value": args[1]}
            )
        return func(*args)

    return wrap


def logger(device: XDevice) -> Optional[list]:
    if "logger" not in device.extra:
        device.extra["logger"] = log = deque(maxlen=100)
        device.decode = logger_wrapper(device.decode, log)
        device.decode_lumi = logger_wrapper(device.decode_lumi, log, "decode_lumi")
        device.decode_zigbee = logger_wrapper(
            device.decode_zigbee, log, "decode_silabs"
        )
        device.encode = logger_wrapper(device.encode, log, "encode")
        device.encode_read = logger_wrapper(device.encode_read, log, "encode_read")
        return None

    return list(device.extra["logger"])
