import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, OptionsFlow, ConfigEntry
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowHandler
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from . import DOMAIN
from .core import utils
from .core.const import PID_BLE, PID_WIFI, PID_WIFI_BLE
from .core.xiaomi_cloud import MiCloud

ACTIONS = {"cloud": "Add Mi Cloud Account", "token": "Add Gateway using Token"}

SERVERS = {
    "cn": "China",
    "de": "Europe",
    "i2": "India",
    "ru": "Russia",
    "sg": "Singapore",
    "us": "United States",
}

OPT_DEBUG = {
    "true": "Basic logs",
    "mqtt": "MQTT logs",
    "zigbee": "Zigbee logs",
}


def form(
    flow: FlowHandler,
    step_id: str,
    schema: dict,
    defaults: dict = None,
    template: dict = None,
    error: str = None,
):
    """Suppport:
    - overwrite schema defaults from dict (user_input or entry.options)
    - set base error code (translations > config > error > code)
    - set custom error via placeholders ("template": "{error}")
    """
    if defaults:
        for key in schema:
            if key.schema in defaults:
                key.default = vol.default_factory(defaults[key.schema])

    if template and "error" in template:
        error = {"base": "template"}
    elif error:
        error = {"base": error}

    return flow.async_show_form(
        step_id=step_id,
        data_schema=vol.Schema(schema),
        description_placeholders=template,
        errors=error,
    )


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
                    device
                    for device in self.hass.data[DOMAIN]["devices"]
                    if device["did"] == user_input["action"]
                )
                return self.async_show_form(
                    step_id="token",
                    data_schema=vol.Schema(
                        {
                            vol.Required("host", default=device["localip"]): str,
                            vol.Required("token", default=device["token"]): str,
                            vol.Optional("key"): str,
                        }
                    ),
                )

        if DOMAIN in self.hass.data and "devices" in self.hass.data[DOMAIN]:
            for device in self.hass.data[DOMAIN]["devices"]:
                if (
                    device["model"] in utils.SUPPORTED_MODELS
                    and device["did"] not in ACTIONS
                ):
                    name = f"Add {device['name']} ({device['localip']})"
                    ACTIONS[device["did"]] = name

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required("action", default="cloud"): vol.In(ACTIONS)}
            ),
        )

    async def async_step_cloud(self, data=None):
        kwargs = {
            "step_id": "cloud",
            "schema": {
                vol.Required("username"): str,
                vol.Required("password"): str,
                vol.Required("servers", default=["cn"]): cv.multi_select(SERVERS),
            },
            "defaults": data,
            "template": {"verify": ""},
        }

        if data:
            if data["servers"]:
                session = async_create_clientsession(self.hass)
                cloud = MiCloud(session)
                if await cloud.login(data["username"], data["password"]):
                    data.update(cloud.auth)
                    return self.async_create_entry(title=data["username"], data=data)

                elif cloud.verify:
                    kwargs["error"] = "verify"
                    kwargs["template"]["verify"] = f"\n[Verify url]({cloud.verify})"
                else:
                    kwargs["error"] = "cant_login"
            else:
                kwargs["error"] = "no_servers"

        return form(self, **kwargs)

    async def async_step_token(self, user_input: dict = None, error=None):
        """GUI > Configuration > Integrations > Plus > Xiaomi Gateway 3"""
        if user_input is not None:
            # check gateway, key is optional
            info = await utils.gateway_info(**user_input)
            if error := info.get("error"):
                return await self.async_step_token(error=error)

            # get key if we don't have it
            if not user_input.get("key"):
                user_input["key"] = info["key"]

            return self.async_create_entry(
                title=user_input["host"], data={}, options=user_input
            )

        return self.async_show_form(
            step_id="token",
            data_schema=vol.Schema(
                {
                    vol.Required("host"): str,
                    vol.Required("token"): str,
                    vol.Optional("key"): str,
                }
            ),
            errors={"base": error} if error else None,
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry):
        return OptionsFlowHandler(entry)


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
                device
                for device in self.hass.data[DOMAIN]["devices"]
                if device["did"] == did
            )

            if device["pid"] != PID_BLE:
                device_info = (
                    f"Name: {device['name']}\n"
                    f"Model: {device['model']}\n"
                    f"IP: {device['localip']}\n"
                    f"MAC: {device['mac']}\n"
                    f"Token: {device['token']}"
                )
            else:
                bindkey = await utils.get_bindkey(self.hass.data[DOMAIN]["cloud"], did)
                device_info = (
                    f"Name: {device['name']}\n"
                    f"Model: {device['model']}\n"
                    f"MAC: {device['mac']}\n"
                    f"Bindkey: {bindkey}\n"
                )

            if device["model"] in utils.SUPPORTED_MODELS:
                info = await utils.gateway_info(device["localip"], device["token"])
                device_info += "\nTelnet: " + info.get("error", "open")
                if key := info.get("key"):
                    device_info += "\nKey: " + key
                    await utils.store_gateway_key(self.hass, info)
            elif device["model"] == "lumi.gateway.v3":
                device_info += "\nLAN key: " + await utils.get_lan_key(
                    device["localip"], device["token"]
                )
            elif ".vacuum." in device["model"]:
                device_info += "\nRooms: " + await utils.get_room_mapping(
                    self.hass.data[DOMAIN]["cloud"],
                    device["localip"],
                    device["token"],
                )
            elif device["model"] == "yeelink.light.bslamp2":
                device_info += "\nLAN mode: " + await utils.enable_bslamp2_lan(
                    device["localip"], device["token"]
                )
            elif device["model"].startswith("yeelink.light."):
                device_info += "\nRemotes: " + await utils.get_ble_remotes(
                    device["localip"], device["token"]
                )

        elif not self.hass.data[DOMAIN].get("devices"):
            device_info = "No devices in account"
        else:
            device_info = "Choose a device from the list"

        devices = {}
        for device in self.hass.data[DOMAIN].get("devices", []):
            if device["pid"] in (PID_WIFI, PID_WIFI_BLE):
                info = device["localip"]
            elif device["pid"] == PID_BLE:
                info = "BLE"
            else:
                continue
            devices[device["did"]] = f"{device['name']} ({info})"

        return self.async_show_form(
            step_id="cloud",
            data_schema=vol.Schema({vol.Required("did"): vol.In(devices)}),
            description_placeholders={"device_info": device_info},
        )

    async def async_step_user(self, user_input=None):
        if user_input:
            return self.async_create_entry(title="", data=user_input)

        host = self.entry.options["host"]
        token = self.entry.options["token"]
        key = self.entry.options.get("key")
        ble = self.entry.options.get("ble", True)
        stats = self.entry.options.get("stats", False)
        debug = self.entry.options.get("debug", [])

        # filter only supported items
        debug = [k for k in debug if k in OPT_DEBUG]

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("host", default=host): str,
                    vol.Required("token", default=token): str,
                    vol.Optional("key", default=key): str,
                    vol.Required("ble", default=ble): bool,
                    vol.Optional("stats", default=stats): bool,
                    vol.Optional("debug", default=debug): cv.multi_select(OPT_DEBUG),
                }
            ),
        )
