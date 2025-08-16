import base64

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .core import core_utils
from .core.const import DOMAIN, PID_BLE, PID_WIFI, PID_WIFI_BLE
from .core.xiaomi_cloud import AuthResult, MiCloud
from .hass import hass_utils

SERVERS = {
    "cn": "China",
    "de": "Europe",
    "i2": "India",
    "ru": "Russia",
    "sg": "Singapore",
    "us": "United States",
}


def vol_schema(schema: dict, defaults: dict = None) -> vol.Schema:
    if defaults:
        for key in schema:
            if (value := defaults.get(key.schema)) is not None:
                key.default = vol.default_factory(value)
    return vol.Schema(schema)


class FlowHandler(ConfigFlow, domain=DOMAIN):
    VERSION = 4

    cloud: MiCloud = None
    cloud_user_input: dict = None

    cloud_gateways: list[dict] = None

    async def async_step_user(self, user_input: dict = None):
        if self.cloud_gateways is None:
            self.cloud_gateways = hass_utils.get_cloud_gateways(self.hass)

        if user_input:
            if user_input["action"] == "cloud":
                return await self.async_step_cloud()
            elif user_input["action"] == "token":
                return await self.async_step_token()
            else:
                did = user_input["action"]
                device = next(i for i in self.cloud_gateways if i["did"] == did)
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

        actions = {"cloud": "Add Mi Cloud Account", "token": "Add Gateway using Token"}
        for device in self.cloud_gateways:
            actions[device["did"]] = f"Add {device['name']} ({device['localip']})"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required("action", default="cloud"): vol.In(actions)}
            ),
        )

    def _show_cloud_form(self, defaults: dict, errors: dict = None):
        return self.async_show_form(
            step_id="cloud",
            data_schema=vol_schema(
                {
                    vol.Required("username"): str,
                    vol.Required("password"): str,
                    vol.Required("servers", default=["cn"]): cv.multi_select(SERVERS),
                },
                defaults,
            ),
            errors=errors,
        )

    async def _process_cloud_result(self, result: AuthResult | None):
        if result["ok"]:
            return self.async_create_entry(
                title=self.cloud_user_input["username"],
                data={
                    "username": self.cloud_user_input["username"],
                    "servers": self.cloud_user_input["servers"],
                    "token": result["token"],
                },
            )

        if image := result.get("captcha"):
            image = "data:image/jpeg;base64," + base64.b64encode(image).decode()
            return self.async_show_form(
                step_id="cloud_captcha",
                data_schema=vol_schema({vol.Required("code"): str}),
                description_placeholders={"image": image},
            )

        if email := result.get("email"):
            return self.async_show_form(
                step_id="cloud_email",
                data_schema=vol_schema({vol.Required("code"): str}),
                description_placeholders={"email": email},
            )

        return self._show_cloud_form(
            self.cloud_user_input, errors={"base": "cant_login"}
        )

    async def async_step_cloud(self, user_input: dict = None):
        if not user_input:
            return self._show_cloud_form(user_input)

        if not user_input["servers"]:
            return self._show_cloud_form(user_input, {"base": "no_servers"})

        if not self.cloud:
            self.cloud = MiCloud(async_create_clientsession(self.hass))

        self.cloud_user_input = user_input

        result = await self.cloud.login(
            user_input["username"], self.cloud_user_input["password"]
        )
        return await self._process_cloud_result(result)

    async def async_step_cloud_captcha(self, user_input: dict = None):
        result = await self.cloud.login_captcha(user_input["code"])
        return await self._process_cloud_result(result)

    async def async_step_cloud_email(self, user_input: dict = None):
        result = await self.cloud.verify_email(user_input["code"])
        return await self._process_cloud_result(result)

    async def async_step_token(self, user_input: dict = None):
        """GUI > Configuration > Integrations > Plus > Xiaomi Gateway 3"""
        kwargs = {}

        if user_input:
            if "key" not in user_input:
                user_input["key"] = await hass_utils.restore_gateway_key(
                    self.hass, user_input["token"]
                )

            # check gateway, key is optional
            info = await core_utils.gateway_info(**user_input)
            if "error" not in info:
                return self.async_create_entry(
                    title=user_input["host"], data={}, options=user_input
                )

            kwargs["errors"] = {"base": info["error"]}

        data = vol_schema(
            {
                vol.Required("host"): str,
                vol.Required("token"): str,
                vol.Optional("key"): str,
            },
            user_input,
        )
        return self.async_show_form(step_id="token", data_schema=data, **kwargs)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        return OptionsFlowHandler()


class OptionsFlowHandler(OptionsFlow):
    cloud_devices = None

    @property
    def config_entry(self):
        return self.hass.config_entries.async_get_entry(self.handler)

    @property
    def cloud(self) -> MiCloud:
        return self.hass.data[DOMAIN][self.config_entry.entry_id]

    async def async_step_init(self, user_input: dict = None):
        if self.config_entry.data:
            return await self.async_step_cloud()
        else:
            return await self.async_step_user()

    async def async_step_cloud(self, user_input: dict = None):
        if self.cloud_devices is None:
            devices = {}
            for device in self.cloud.devices or []:
                if device["pid"] in (PID_WIFI, PID_WIFI_BLE):
                    info = device["localip"]
                elif device["pid"] == PID_BLE:
                    info = device["mac"]
                else:
                    continue
                devices[device["did"]] = f"{device['name']} ({info})"
            # sort by name
            self.cloud_devices = dict(sorted(devices.items(), key=lambda x: x[1]))

        if user_input:
            did = user_input["did"]
            device = next(i for i in self.cloud.devices if i["did"] == did)

            info = await core_utils.get_device_info(self.cloud, device)
            device_info = "\n".join(f"{k}: {v}" for k, v in info.items())
        elif self.cloud_devices:
            device_info = "Choose a device from the list"
        else:
            device_info = "No devices in account"

        data = vol_schema({vol.Required("did"): vol.In(self.cloud_devices)}, user_input)
        return self.async_show_form(
            step_id="cloud",
            data_schema=data,
            description_placeholders={"device_info": device_info},
        )

    async def async_step_user(self, user_input: dict = None):
        if user_input:
            return self.async_create_entry(title="", data=user_input)

        defaults = self.config_entry.options.copy()
        data = vol_schema(
            {
                vol.Required("host"): str,
                vol.Required("token"): str,
                vol.Optional("key"): str,
                vol.Optional("stats"): vol.In(
                    {
                        False: "Disabled",  # for backward compatibility
                        True: "Sensors",  # for backward compatibility
                        "binary_sensor": "Binary sensors",
                    }
                ),
                vol.Optional("debug"): cv.multi_select(
                    {
                        "true": "Basic logs",
                        "mqtt": "MQTT logs",
                        "zigbee": "Zigbee logs",
                    }
                ),
            },
            defaults,
        )
        return self.async_show_form(step_id="user", data_schema=data)
