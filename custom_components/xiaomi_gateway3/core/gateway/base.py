import asyncio
import re
from logging import Logger
from typing import Callable, Dict, List, Optional

from ..converters import Converter
from ..device import XDevice
from ..mini_miio import AsyncMiIO
from ..mini_mqtt import MiniMQTT

RE_ENTITIES = re.compile(r"[a-z_]+")

SIGNAL_PREPARE_GW = "prepare_gateway"
SIGNAL_MQTT_CON = "mqtt_connect"
SIGNAL_MQTT_DIS = "mqtt_disconnect"
SIGNAL_MQTT_PUB = "mqtt_publish"
SIGNAL_TIMER = "timer"


class GatewayBase:
    """devices and defaults are global between all gateways."""
    # keys:
    # - Gateway: did, "123456789", X digits
    # - Zigbee: did, "lumi.abcdef", 8 byte hex mac without leading zeros
    # - BLE: mac, "abcdef", 6 byte hex mac
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
    setups: Dict[str, Callable] = None
    tasks: List[asyncio.Task] = None

    mqtt: MiniMQTT = None
    miio: AsyncMiIO = None

    did: str = None
    time_offset = 0

    @property
    def ble_mode(self):
        return self.options.get('ble', True)

    @property
    def debug_mode(self):
        return self.options.get('debug', '')

    @property
    def zha_mode(self) -> bool:
        return self.options.get('zha', False)

    @property
    def stats_enable(self):
        return self.options.get('stats', False)

    @property
    def device(self) -> Optional[XDevice]:
        return self.devices.get(self.did)

    def debug(self, msg: str, exc_info=None):
        """Global debug messages. Passed only if default debug enabled."""
        if 'true' in self.debug_mode:
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

    def debug_device(self, device: XDevice, msg: str, payload=None,
                     tag: str = "BASE"):
        """Debug message with device. Passed only if default debug enabled."""
        if 'true' in self.debug_mode:
            adv = device.nwk if device.nwk else device.model
            self.log.debug(
                f"{self.host} [{tag}] {device.mac} ({adv}) {msg} {payload}"
                if payload else
                f"{self.host} [{tag}] {device.mac} ({adv}) {msg}"
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

    def add_setup(self, domain: str, handler):
        """Add hass entity setup funcion."""
        if "." in domain:
            _, domain = domain.rsplit(".", 1)
        self.setups[domain] = handler

    def setup_entity(self, domain: str, device: XDevice, conv: Converter):
        handler = self.setups.get(domain)
        if handler:
            handler(self, device, conv)

    def add_device(self, did: str, device: XDevice):
        if did not in self.devices:
            self.devices[did] = device

        if self not in device.gateways:
            device.gateways.append(self)

        # don't setup device with unknown model
        if not device.model:
            return

        # if device.entities:
        #     # don't setup if device already has setup entities
        #     self.debug_device(device, "Join to gateway", device.model)
        #     return

        # don't setup device from second gateway
        if len(device.gateways) > 1:
            return

        device.setup_entitites(self, stats=self.stats_enable)
        self.debug_device(
            device, f"setup {device.info.model}:",
            ", ".join(device.entities.keys())
        )

    def filter_devices(self, feature: str) -> List[XDevice]:
        return [
            device for device in self.devices.values()
            if self in device.gateways and device.has_support(feature)
        ]
