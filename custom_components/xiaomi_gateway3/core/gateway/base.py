import asyncio
import random
import re
from logging import Logger
from typing import Callable, Dict, List, Optional, Union

from ..converters import Converter, GATEWAY
from ..device import XDevice
from ..mini_miio import AsyncMiIO
from ..mini_mqtt import MiniMQTT, MQTTMessage

RE_ENTITIES = re.compile(r"[a-z_]+")

SIGNAL_PREPARE_GW = "prepare_gateway"
SIGNAL_MQTT_CON = "mqtt_connect"
SIGNAL_MQTT_DIS = "mqtt_disconnect"
SIGNAL_MQTT_PUB = "mqtt_publish"
SIGNAL_TIMER = "timer"

SetupHandler = Callable[["XGateway", XDevice, Converter], None]


class GatewayBase:
    """devices and defaults are global between all gateways."""

    # keys:
    # - Gateway: did, "123456789", X digits
    # - Zigbee: did, "lumi.abcdef", 8 byte hex mac without leading zeros
    # - BLE: mac, "blt.x.xxx", alphanum
    # - Mesh: did, "123456789", X digits
    # - Mesh group: did, "group.123456789"
    devices: Dict[str, XDevice] = {}
    # key - mac, 6 byte hex for gw and bluetooth, 8 byte hex for zb with "0x"
    defaults: Dict[str, dict] = {}

    log: Logger = None

    host: str = None
    options: dict = None
    available: bool = None

    dispatcher: Dict[str, List[Callable]] = None
    setups: Dict[str, SetupHandler] = None
    tasks: List[asyncio.Task] = None
    miio_ack: Dict[int, asyncio.Future] = None

    mqtt: MiniMQTT = None
    miio: AsyncMiIO = None

    did: str = None

    @property
    def ble_mode(self):
        return self.options.get("ble", True)

    @property
    def debug_mode(self):
        return self.options.get("debug", "")

    @property
    def stats_enable(self):
        return self.options.get("stats", False)

    @property
    def device(self) -> Optional[XDevice]:
        return self.devices.get(self.did)

    def debug(self, msg: str, exc_info=None):
        """Global debug messages. Passed only if default debug enabled."""
        if "true" in self.debug_mode:
            self.log.debug(f"{self.host} [BASE] {msg}", exc_info=exc_info)

    def warning(self, msg: str, exc_info=None):
        self.log.warning(f"{self.host} | {msg}", exc_info=exc_info)

    def error(self, msg: str, exc_info=None):
        self.log.error(f"{self.host} | {msg}", exc_info=exc_info)

    def exception(self, msg: str):
        self.log.exception(f"{self.host} | {msg}")

    def debug_tag(self, msg: str, tag: str):
        """Debug message with tag. Tag should be in upper case. `debug_mode`
        must be checked before calling.
        """
        self.log.debug(f"{self.host} [{tag}] {msg}")

    def debug_device(self, device: XDevice, msg: str, payload=None, tag: str = "BASE"):
        """Debug message with device. Passed only if default debug enabled."""
        if "true" in self.debug_mode:
            adv = device.nwk if device.nwk else device.model
            self.log.debug(
                f"{self.host} [{tag}] {device.mac} ({adv}) {msg} {payload}"
                if payload
                else f"{self.host} [{tag}] {device.mac} ({adv}) {msg}"
            )

    def dispatcher_connect(self, signal: str, target: Callable):
        targets = self.dispatcher.setdefault(signal, [])
        if target not in targets:
            targets.append(target)

    async def dispatcher_send(self, signal: str, **kwargs):
        if not self.dispatcher.get(signal):
            return
        # better not to use asyncio.gather
        for handler in self.dispatcher[signal]:
            await handler(**kwargs)

    def add_setup(self, domain: str, handler: SetupHandler):
        """Add hass entity setup funcion."""
        if "." in domain:
            _, domain = domain.rsplit(".", 1)
        self.setups[domain] = handler

    def setup_entity(self, domain: str, device: XDevice, conv: Converter):
        if handler := self.setups.get(domain):
            handler(self, device, conv)

    def add_device(self, did: str, device: XDevice):
        # 1. Add XDevice to XDevices registry
        if did not in self.devices:
            self.devices[did] = device

        # 2. Add this XGateway to device.gateways
        if self not in device.gateways:
            device.gateways.append(self)

        # don't setup device with unknown model
        if not device.model:
            return

        # 3. Setup entities for this XDevice with this XGateway
        device.setup_entitites(self, stats=self.stats_enable)
        self.debug_device(
            device, f"setup {device.info.model}:", ", ".join(device.entities.keys())
        )

    def filter_devices(self, feature: str) -> List[XDevice]:
        return [
            device
            for device in self.devices.values()
            if self in device.gateways and device.has_support(feature)
        ]

    async def miio_send(
        self, method: str, params: Union[dict, list] = None, timeout: int = 5
    ):
        fut = asyncio.get_event_loop().create_future()

        cid = random.randint(1_000_000_000, 2_147_483_647)
        self.miio_ack[cid] = fut

        await self.mqtt.publish(
            "miio/command", {"id": cid, "method": method, "params": params}
        )

        try:
            await asyncio.wait_for(self.miio_ack[cid], timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            del self.miio_ack[cid]

        return fut.result()

    async def mqtt_read(self, msg: MQTTMessage):
        if msg.topic == "miio/command_ack":
            if ack := self.miio_ack.get(msg.json["id"]):
                ack.set_result(msg.json)

        elif msg.topic == "miio/report":
            if b'"event.gw.heartbeat"' in msg.payload:
                payload = msg.json["params"][0]
                payload = self.device.decode(GATEWAY, payload)
                self.device.update(payload)

        elif msg.topic.endswith("/heartbeat"):
            payload = self.device.decode(GATEWAY, msg.json)
            self.device.update(payload)
