import asyncio
import logging
import time

from .base import GatewayBase, SIGNAL_MQTT_PUB, SIGNAL_TIMER, SIGNAL_PREPARE_GW
from .. import shell, utils
from ..converters import GATEWAY
from ..mini_mqtt import MQTTMessage


class OpenmiioGateway(GatewayBase):
    openmiio_ts: float = 0

    def openmiio_init(self):
        self.dispatcher_connect(SIGNAL_PREPARE_GW, self.openmiio_prepare_gateway)
        self.dispatcher_connect(SIGNAL_MQTT_PUB, self.openmiio_mqtt_publish)
        self.dispatcher_connect(SIGNAL_TIMER, self.openmiio_timer)

    async def openmiio_prepare_gateway(self, sh: shell.ShellOpenMiio):
        if self.log.isEnabledFor(logging.DEBUG):
            log = await sh.read_file(
                "/var/log/openmiio.log", as_base64=True, tail="10k"
            )
            if log and not log.startswith(b"cat:"):
                self.debug(f"openmiio: previous log: {log}")

        latest = await sh.check_openmiio()
        if not latest:
            self.debug("openmiio: download latest version")
            await sh.download_openmiio()

            latest = await sh.check_openmiio()
            if not latest:
                raise Exception("openmiio: can't run latest version")
        else:
            self.debug("openmiio: latest version detected")

        if "openmiio_agent" not in await sh.get_running_ps():
            self.debug("openmiio: run latest version")
            await sh.run_openmiio()

            mqtt_online = await utils.check_port(self.host, 1883)
            if not mqtt_online:
                self.debug("openmiio: waiting for MQTT to start")
                await asyncio.sleep(2)

        # let openmiio boot
        self.openmiio_ts = time.time() + 60

    async def openmiio_mqtt_publish(self, msg: MQTTMessage):
        if msg.topic == "openmiio/report":
            self.openmiio_ts = time.time() + 60
            payload = self.device.decode(GATEWAY, msg.json)
            self.device.update(payload)

    async def openmiio_timer(self, ts: float):
        if ts < self.openmiio_ts:
            return

        self.debug("openmiio: WARNING report timeout")

        payload = self.device.decode(GATEWAY, {"openmiio": {"uptime": None}})
        self.device.update(payload)

        try:
            async with shell.Session(self.host) as sh:
                if not await sh.only_one():
                    self.debug("Connection from a second Hass detected")
                    return

                await self.openmiio_prepare_gateway(sh)

        except Exception as e:
            self.warning("Can't restart openmiio", e)
