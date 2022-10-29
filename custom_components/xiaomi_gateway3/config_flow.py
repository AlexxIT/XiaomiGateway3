import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, OptionsFlow, ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from . import DOMAIN
from .core import utils
from .core.xiaomi_cloud import MiCloud

ACTIONS = {
    "cloud": "Add Mi Cloud Account",
    "token": "Add Gateway using Token"
}

SERVERS = {
    "cn": "China",
    "de": "Europe",
    "i2": "India",
    "ru": "Russia",
    "sg": "Singapore",
    "us": "United States"
}

OPT_DEBUG = {
    "true": "Basic logs",
    "mqtt": "MQTT logs",
    "zigbee": "Zigbee logs",
}


class FlowHandler(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    cloud = None

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            if user_input["action"] == "cloud":
                return await self.async_step_cloud()
            elif user_input["action"] == "token":
                return await self.async_step_token()
            else:
                device = next(
                    device for device in self.hass.data[DOMAIN]["devices"]
                    if device["did"] == user_input["action"]
                )
                return self.async_show_form(
                    step_id="token",
                    data_schema=vol.Schema({
                        vol.Required("host", default=device["localip"]): str,
                        vol.Required("token", default=device["token"]): str,
                        vol.Optional("telnet_cmd"): str,
                    }),
                )

        if DOMAIN in self.hass.data and "devices" in self.hass.data[DOMAIN]:
            for device in self.hass.data[DOMAIN]["devices"]:
                if (device["model"] in utils.SUPPORTED_MODELS and
                        device["did"] not in ACTIONS):
                    name = f"Add {device['name']} ({device['localip']})"
                    ACTIONS[device["did"]] = name

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("action", default="cloud"): vol.In(ACTIONS)
            })
        )

    async def async_step_cloud(self, user_input=None, error=None):
        if user_input:
            if not user_input["servers"]:
                return await self.async_step_cloud(error="no_servers")

            session = async_create_clientsession(self.hass)
            cloud = MiCloud(session)
            if await cloud.login(
                    user_input["username"], user_input["password"]
            ):
                user_input.update(cloud.auth)
                return self.async_create_entry(
                    title=user_input["username"], data=user_input
                )

            else:
                return await self.async_step_cloud(error="cant_login")

        return self.async_show_form(
            step_id="cloud",
            data_schema=vol.Schema({
                vol.Required("username"): str,
                vol.Required("password"): str,
                vol.Required("servers", default=["cn"]):
                    cv.multi_select(SERVERS)
            }),
            errors={"base": error} if error else None
        )

    async def async_step_token(self, user_input=None, error=None):
        """GUI > Configuration > Integrations > Plus > Xiaomi Gateway 3"""
        if user_input is not None:
            error = await utils.check_gateway(**user_input)
            if error:
                return await self.async_step_token(error=error)

            return self.async_create_entry(
                title=user_input["host"], data=user_input
            )

        return self.async_show_form(
            step_id="token",
            data_schema=vol.Schema({
                vol.Required("host"): str,
                vol.Required("token"): str,
                vol.Optional("telnet_cmd"): str,
            }),
            errors={"base": error} if error else None
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry):
        return OptionsFlowHandler(entry)


TITLE = "Xiaomi Gateway 3"

ZHA_NOTIFICATION = """For **ZHA**, goto:

Configuration > Integrations > Add Integration > Zigbee Home Automation:

- Radio Type: **EZSP**
- Path: `socket://{0}:8888`

For **zigbee2mqtt**, goto:

Supervisor > Zigbee2mqtt > Configuration:

```
serial:
  port: 'tcp://{0}:8888'
  adapter: ezsp
```
"""


# noinspection PyUnusedLocal
class OptionsFlowHandler(OptionsFlow):
    def __init__(self, entry: ConfigEntry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        if "servers" in self.entry.data:
            return await self.async_step_cloud()
        else:
            return await self.async_step_user()

    async def async_step_cloud(self, user_input=None):
        if user_input is not None:
            did = user_input["did"]
            device = next(
                device for device in self.hass.data[DOMAIN]["devices"]
                if device["did"] == did
            )

            if device["pid"] != 6:
                device_info = (
                    f"Name: {device['name']}\n"
                    f"Model: {device['model']}\n"
                    f"IP: {device['localip']}\n"
                    f"MAC: {device['mac']}\n"
                    f"Token: {device['token']}"
                )
            else:
                bindkey = await utils.get_bindkey(
                    self.hass.data[DOMAIN]["cloud"], did
                )
                device_info = (
                    f"Name: {device['name']}\n"
                    f"Model: {device['model']}\n"
                    f"MAC: {device['mac']}\n"
                    f"Bindkey: {bindkey}\n"
                )

            if device["model"] == "lumi.gateway.v3":
                device_info += "\nLAN key: " + await utils.get_lan_key(
                    device["localip"], device["token"]
                )
            elif ".vacuum." in device["model"]:
                device_info += "\nRooms: " + await utils.get_room_mapping(
                    self.hass.data[DOMAIN]["cloud"],
                    device["localip"], device["token"],
                )
            elif device["model"] == "yeelink.light.bslamp2":
                device_info += "\nLAN mode: " + await utils.enable_bslamp2_lan(
                    device["localip"], device["token"]
                )

        elif not self.hass.data[DOMAIN].get("devices"):
            device_info = "No devices in account"
        else:
            device_info = "Choose a device from the list"

        devices = {}
        for device in self.hass.data[DOMAIN].get("devices", []):
            # 0 - wifi, 6 - ble, 8 - wifi+ble
            if device["pid"] in (0, 8):
                info = device["localip"]
            elif device["pid"] == 6:
                info = "BLE"
            else:
                continue
            devices[device["did"]] = f"{device['name']} ({info})"

        return self.async_show_form(
            step_id="cloud",
            data_schema=vol.Schema({
                vol.Required("did"): vol.In(devices)
            }),
            description_placeholders={
                "device_info": device_info
            }
        )

    async def async_step_user(self, user_input=None):
        if user_input:
            old_mode = self.entry.options.get("zha", False)
            new_mode = user_input["zha"]
            if new_mode != old_mode:
                host = user_input["host"]
                if new_mode is True:
                    self.hass.components.persistent_notification.async_create(
                        ZHA_NOTIFICATION.format(host), TITLE
                    )

            return self.async_create_entry(title='', data=user_input)

        host = self.entry.options["host"]
        token = self.entry.options["token"]
        telnet_cmd = self.entry.options.get("telnet_cmd", "")
        ble = self.entry.options.get("ble", True)
        stats = self.entry.options.get("stats", False)
        debug = self.entry.options.get("debug", [])
        # buzzer = self.entry.options.get("buzzer", False)
        memory = self.entry.options.get("memory", False)
        zha = self.entry.options.get("zha", False)

        # filter only supported items
        debug = [k for k in debug if k in OPT_DEBUG]

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("host", default=host): str,
                vol.Required("token", default=token): str,
                vol.Optional("telnet_cmd", default=telnet_cmd): str,
                vol.Required("ble", default=ble): bool,
                vol.Optional("stats", default=stats): bool,
                vol.Optional("debug", default=debug):
                    cv.multi_select(OPT_DEBUG),
                # vol.Optional("buzzer", default=buzzer): bool,
                vol.Optional("memory", default=memory): bool,
                vol.Optional("zha", default=zha): bool,
            }),
        )
