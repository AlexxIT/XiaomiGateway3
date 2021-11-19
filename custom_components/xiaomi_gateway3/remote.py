import json
import logging

from homeassistant.components import persistent_notification
from homeassistant.components.remote import ATTR_DEVICE
from homeassistant.helpers.entity import ToggleEntity

from . import DOMAIN
from .core import utils, zigbee
from .core.gateway3 import Gateway3
from .core.helpers import XiaomiEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    def setup(gateway: Gateway3, device: dict, attr: str):
        async_add_entities([Gateway3Entity(gateway, device, attr)])

    gw: Gateway3 = hass.data[DOMAIN][config_entry.entry_id]
    gw.add_setup('remote', setup)


class Gateway3Entity(XiaomiEntity, ToggleEntity):
    @property
    def is_on(self):
        return self._state

    @property
    def icon(self):
        return 'mdi:zigbee'

    async def async_update(self, data: dict = None):
        if 'pairing_start' in data:
            self._state = True

        elif 'pairing_stop' in data:
            self._state = False
            self.gw.pair_model = None

        elif 'added_device' in data:
            # skip already added device, this maybe bug
            did = data['added_device']['did']
            if did in self.gw.devices:
                return

            text = "New device:\n" + '\n'.join(
                f"{k}: {v}" for k, v in data['added_device'].items()
            )
            persistent_notification.async_create(
                self.hass, text, "Xiaomi Gateway 3"
            )

        elif 'removed_did' in data:
            # https://github.com/AlexxIT/XiaomiGateway3/issues/122
            did = data['removed_did']['did'] \
                if isinstance(data['removed_did'], dict) \
                else data['removed_did']
            if did.startswith('lumi.'):
                self.debug(f"Handle removed_did: {did}")
                utils.remove_device(self.hass, did)

        self.async_write_ha_state()

    async def async_turn_on(self):
        # work for any device model, dev_type: 0 - zb1, 1 - zb3, don't matter
        await self.gw.miio.send('miIO.zb_start_provision', {
            'dev_type': 0, 'duration': 60, 'method': 0,
            'model': 'lumi.sensor_switch.v2', 'pid': 62
        })
        # self.gw.send(self.device, {'pairing_start': 60})

    async def async_turn_off(self):
        await self.gw.miio.send('miIO.zb_end_provision', {'code': -1})
        # self.gw.send(self.device, {'pairing_stop': 0})

    async def async_send_command(self, command, **kwargs):
        for cmd in command:
            args = cmd.split(' ', 1)
            cmd = args[0]

            # for testing purposes
            if cmd == 'ble':
                raw = kwargs[ATTR_DEVICE].replace('\'', '"')
                await self.gw.process_ble_event(raw)
            elif cmd == 'pair':
                model: str = kwargs[ATTR_DEVICE]
                self.gw.pair_model = (model[:-3] if model.endswith('.v1')
                                      else model)
                await self.async_turn_on()
            elif cmd in ('reboot', 'ftp', 'dump'):
                await self.gw.send_telnet(cmd)
            elif cmd == 'power':
                power = int(args[1])
                await self.gw.send_zigbee(self.device, {'power_tx': power})
            elif cmd == 'channel':
                channel = int(args[1])
                await self.gw.send_zigbee(self.device, {'channel': channel})
            elif cmd == 'publishstate':
                await self.gw.send_mqtt('publishstate')
            elif cmd == 'parentscan':
                await self.gw.run_parent_scan()
            elif cmd == 'memsync':
                await self.gw.memory_sync()
            elif cmd == 'ota':
                did: str = 'lumi.' + kwargs[ATTR_DEVICE]
                if did not in self.gw.devices:
                    _LOGGER.error(f"Wrong device ID: " + did)
                    return

                device = self.gw.devices[did]

                url = await zigbee.get_ota_link(self.hass, device)
                if url:
                    self.debug(f"Update {did} with {url}")
                    resp = await self.gw.miio.send('miIO.subdev_ota', {
                        'did': did,
                        'subdev_url': url
                    })
                    if not resp or resp.get('result') != ['ok']:
                        _LOGGER.error(f"Can't run update process: {resp}")
                else:
                    _LOGGER.error("No firmware for model " + device['model'])

            elif cmd == 'miio':
                raw = json.loads(args[1])
                resp = await self.gw.miio.send(
                    raw['method'], raw.get('params')
                )
                persistent_notification.async_create(
                    self.hass, str(resp), "Xiaomi Gateway 3"
                )
