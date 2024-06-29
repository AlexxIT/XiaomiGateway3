import asyncio
import logging
import time
from functools import cached_property
from logging import Logger, DEBUG
from typing import Callable

from ..const import GATEWAY
from ..device import XDevice, XDeviceExtra
from ..mini_mqtt import MiniMQTT, MQTTMessage

EVENT_ADD_DEVICE = "add_device"
EVENT_REMOVE_DEVICE = "remove_device"
EVENT_MQTT_CONNECT = "mqtt_connect"
EVENT_MQTT_PUBLISH = "mqtt_publish"
EVENT_TIMER = "timer"


class XGateway:
    devices: dict[str, XDevice] = {}  # key is device.did

    device: XDevice = None
    listeners: dict[str, list[Callable]]
    base_log: Logger = None
    timer_task: asyncio.Task

    def __init__(self, host: str, **kwargs):
        self.host = host

        self.available = False
        self.listeners = {}
        self.mqtt = MiniMQTT()
        self.options: dict = kwargs

        # setup smart loggers
        prefix = __package__[:-10]  # .core.gate
        self.base_log = logging.getLogger(f"{prefix}.gate.{host}")
        self.mqtt_log = logging.getLogger(f"{prefix}.mqtt.{host}")
        self.zigb_log = logging.getLogger(f"{prefix}.zigb.{host}")

        if debug := self.options.get("debug"):
            if "true" in debug:
                self.base_log.setLevel(DEBUG)
            if "mqtt" in debug:
                self.mqtt_log.setLevel(DEBUG)
            if "zigbee" in debug:
                self.zigb_log.setLevel(DEBUG)

    @cached_property
    def stats_domain(self) -> str | None:
        stats = self.options.get("stats")
        if isinstance(stats, bool):
            return "sensor" if stats else None
        return stats

    def as_dict(self) -> dict:
        return {
            "host": self.host,
            "mac": self.device.extra["mac"],
            "name": self.device.human_name,
            "model": self.device.model,
            "fw_ver": self.device.extra["fw_ver"],
        }

    def debug(self, msg: str, device: XDevice = None, exc_info=None, **kwargs):
        if not self.base_log.isEnabledFor(DEBUG):
            return
        if device:
            msg = {"uid": device.uid, "did": device.did, "msg": msg}
        else:
            msg = {"msg": msg}
        self.base_log.debug(msg | kwargs, exc_info=exc_info)

    def warning(self, msg: str, exc_info=None):
        self.base_log.warning({"msg": msg}, exc_info=exc_info)

    def error(self, msg: str, exc_info=None):
        self.base_log.error({"msg": msg}, exc_info=exc_info)

    def add_event_listener(self, event: str, handler: Callable):
        listeners = self.listeners.setdefault(event, [])
        # protection from adding handler two times
        if any(i == handler for i in listeners):
            return
        listeners.append(handler)

    def dispatch_event(self, event: str, *args, **kwargs):
        try:
            if listeners := self.listeners.get(event):
                for handler in listeners:
                    handler(*args, **kwargs)
        except Exception as e:
            self.error(f"dispatch_event: {event} {args} {kwargs}", exc_info=e)

    def remove_all_event_listners(self):
        self.listeners.clear()

    def init_device(self, model: str | int | None, **kwargs) -> XDevice:
        device = XDevice(model, **kwargs)
        self.debug("init_device", device=device, data=device.extra)
        self.devices[device.did] = device
        return device

    def add_device(self, device: XDevice):
        if self in device.gateways:
            return

        device.restore_last_seen(self)

        self.debug("add_device", device=device)
        device.gateways.append(self)
        self.dispatch_event(EVENT_ADD_DEVICE, device)

    def remove_device(self, device: XDevice):
        if self not in device.gateways:
            return
        self.debug("remove_device", device=device)
        device.gateways.remove(self)
        self.dispatch_event(EVENT_REMOVE_DEVICE, device)

    def remove_all_devices(self):
        for device in self.devices.values():
            self.remove_device(device)

    async def base_read_device(self, info: dict[str]):
        self.device = self.devices.get(info["did"])
        if not self.device:
            extra: XDeviceExtra = {
                "did": info["did"],
                "type": GATEWAY,
                "mac": info["mac"].lower(),  # aa:bb:cc:dd:ee:ff
                "fw_ver": info["version"],
            }
            if "lan_mac" in info:
                extra["mac2"] = info["lan_mac"]
            self.device = self.init_device(info["model"], **extra)
        self.add_device(self.device)

    async def handle_mqtt_messages(self):
        if not await self.mqtt.connect(self.host):
            return

        try:
            await self.mqtt.subscribe("#")
            self.on_mqtt_connect()
            async for msg in self.mqtt:
                self.on_mqtt_message(msg)
        except Exception as e:
            self.debug(f"MQTT processing issue", exc_info=e)
        finally:
            try:
                await self.mqtt.disconnect()
                await self.mqtt.close()
                self.on_mqtt_disconnect()
            except Exception as e:
                self.debug(f"MQTT clossing issue", exc_info=e)

    def on_mqtt_connect(self):
        self.debug("MQTT connected")
        self.available = True
        self.dispatch_event(EVENT_MQTT_CONNECT)
        self.timer_task = asyncio.create_task(self.timer())

    def on_mqtt_disconnect(self):
        self.debug("MQTT disconnected")
        self.available = False
        self.timer_task.cancel()
        self.update_devices(int(time.time()))

    def on_mqtt_message(self, msg: MQTTMessage):
        if msg.topic == "broker/ping":
            return  # skip spam from broker/ping

        if self.mqtt_log.isEnabledFor(DEBUG):
            self.mqtt_log.debug({"topic": msg.topic, "data": msg.payload})

        self.dispatch_event(EVENT_MQTT_PUBLISH, msg)

    async def timer(self):
        while True:
            ts = time.time()
            self.update_devices(int(ts))
            self.dispatch_event(EVENT_TIMER, ts)
            await asyncio.sleep(30)

    def update_devices(self, ts: int):
        for device in self.devices.values():
            if self in device.gateways:
                device.update(ts)

    async def send(self, device: XDevice, data: dict):
        pass
