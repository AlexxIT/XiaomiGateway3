import asyncio
import base64
import inspect
import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .core import core_utils
from .core import key_recovery
from .core.const import DOMAIN, PID_BLE, PID_WIFI, PID_WIFI_BLE
from .core.xiaomi_cloud import AuthResult, MiCloud
from .hass import hass_utils

_LOGGER = logging.getLogger(__name__)

_KEY_RECOVERY_ERRORS = {
    "invalid_input",
    "cannot_connect",
    "invalid_token",
    "unsupported_firmware",
    "invalid_identity",
    "callback_unavailable",
    "method_rejected",
    "upload_timeout",
    "invalid_upload",
}

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
    _key_recovery_context: dict = None
    _key_recovery_identity = None
    _key_recovery_callback_address: str = None
    _key_recovery_task: asyncio.Task = None
    _key_recovery_error: str = None
    _recovered_gateway_key: str = None
    _gateway_info_retry_input: dict = None

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

    async def _process_cloud_result(self, result: AuthResult):
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

        if verify := result.get("verify"):
            return self.async_show_form(
                step_id="cloud_verify",
                data_schema=vol_schema({vol.Required("code"): str}),
                description_placeholders={"address": verify},
            )

        _LOGGER.error("Can't login", exc_info=result["exception"])

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

    async def async_step_cloud_verify(self, user_input: dict = None):
        result = await self.cloud.login_verify(user_input["code"])
        return await self._process_cloud_result(result)

    def _supports_cancellable_recovery_progress(self) -> bool:
        """Only offer recovery where HA can cancel its progress task."""
        progress_method = getattr(self, "async_show_progress", None)
        if progress_method is None:
            return False
        try:
            parameters = inspect.signature(progress_method).parameters
        except (TypeError, ValueError):
            return False
        return "progress_task" in parameters

    async def _async_offer_key_recovery(self, user_input: dict) -> bool:
        """Offer recovery before gateway_info makes another Telnet attempt."""
        if await core_utils.check_port(user_input["host"], 23):
            return False

        identity = await key_recovery.async_probe_gateway(
            user_input["host"], user_input["token"]
        )
        if not key_recovery.supports_recovery(identity, experimental=False):
            return False

        self._key_recovery_context = {
            "host": user_input["host"],
            "token": user_input["token"],
        }
        self._key_recovery_identity = identity
        try:
            self._key_recovery_callback_address = key_recovery.callback_ipv4(
                user_input["host"]
            )
        except key_recovery.RecoveryError:
            self._key_recovery_callback_address = ""
        return True

    def _show_key_recovery_form(self, user_input: dict = None, errors: dict = None):
        defaults = {
            "callback_address": self._key_recovery_callback_address or "",
        }
        if user_input:
            defaults.update(
                {
                    key: user_input[key]
                    for key in ("callback_address", "key", "confirm_recovery")
                    if key in user_input
                }
            )

        return self.async_show_form(
            step_id="key_recovery",
            data_schema=vol_schema(
                {
                    vol.Optional("callback_address"): str,
                    vol.Optional("key"): str,
                    vol.Required("confirm_recovery", default=False): bool,
                },
                defaults,
            ),
            errors=errors,
            description_placeholders={
                "callback_address": self._key_recovery_callback_address or "not detected",
            },
        )

    @staticmethod
    def _key_recovery_error_code(error: Exception) -> str:
        code = getattr(error, "code", None)
        return code if code in _KEY_RECOVERY_ERRORS else "recovery_failed"

    async def async_step_key_recovery(self, user_input: dict = None):
        if not user_input:
            error = self._key_recovery_error
            self._key_recovery_error = None
            errors = {"base": error} if error else None
            return self._show_key_recovery_form(errors=errors)

        manual_key = user_input.get("key")
        consent = user_input.get("confirm_recovery", False)
        if manual_key and consent:
            return self._show_key_recovery_form(
                user_input, errors={"base": "recovery_choose_one"}
            )
        if manual_key:
            context = self._key_recovery_context
            return await self.async_step_token(
                {
                    "host": context["host"],
                    "token": context["token"],
                    "key": manual_key,
                }
            )
        if not consent:
            return self._show_key_recovery_form(
                user_input, errors={"base": "recovery_consent_required"}
            )

        self._key_recovery_callback_address = user_input.get(
            "callback_address", ""
        )
        self._key_recovery_error = None
        self._recovered_gateway_key = None
        self._key_recovery_task = self.hass.async_create_task(
            self._async_run_key_recovery()
        )
        return await self.async_step_key_recovery_progress()

    async def _async_run_key_recovery(self) -> None:
        """Keep the key out of the Task result and any surfaced exception."""
        context = self._key_recovery_context
        try:
            recovered_key = await key_recovery.async_recover_gateway_key(
                context["host"],
                context["token"],
                callback_address=self._key_recovery_callback_address or None,
                identity=self._key_recovery_identity,
                timeout=90,
                port=0,
                experimental=False,
            )
        except asyncio.CancelledError:
            raise
        except Exception as error:
            # Convert exceptions to a safe code; do not retain error text.
            self._key_recovery_error = self._key_recovery_error_code(error)
            return

        if not isinstance(recovered_key, str) or len(recovered_key) != 16:
            self._key_recovery_error = "invalid_upload"
            return
        self._recovered_gateway_key = recovered_key

    async def async_step_key_recovery_progress(self, user_input: dict = None):
        task = self._key_recovery_task
        if task is None:
            return await self.async_step_key_recovery()
        if not task.done():
            return self.async_show_progress(
                step_id="key_recovery_progress",
                progress_action="recovering_key",
                progress_task=task,
            )

        try:
            # The wrapper stores the validated key privately and always returns
            # None, so it cannot appear in a Task result or progress state.
            task.result()
        except asyncio.CancelledError:
            self._key_recovery_task = None
            self._recovered_gateway_key = None
            return self.async_show_progress_done(next_step_id="key_recovery")
        except Exception:
            # The wrapper normally converts failures to safe error codes.
            self._key_recovery_error = "recovery_failed"

        if not self._key_recovery_error and not self._recovered_gateway_key:
            self._key_recovery_error = "invalid_upload"
        self._key_recovery_task = None
        next_step = (
            "key_recovery"
            if self._key_recovery_error
            else "key_recovery_confirm"
        )
        return self.async_show_progress_done(next_step_id=next_step)

    async def async_step_key_recovery_confirm(self, user_input: dict = None):
        if user_input:
            if not user_input.get("confirm_setup"):
                errors = {"base": "confirm_setup_required"}
            elif not self._key_recovery_context or not self._recovered_gateway_key:
                return await self.async_step_token()
            else:
                return await self.async_step_token(
                    {
                        "host": self._key_recovery_context["host"],
                        "token": self._key_recovery_context["token"],
                        "key": self._recovered_gateway_key,
                    }
                )
        else:
            errors = None

        return self.async_show_form(
            step_id="key_recovery_confirm",
            data_schema=vol.Schema(
                {vol.Required("confirm_setup", default=False): bool}
            ),
            errors=errors,
        )

    async def async_step_token(self, user_input: dict = None):
        """GUI > Configuration > Integrations > Plus > Xiaomi Gateway 3"""
        kwargs = {
            "description_placeholders": {
                "link": "https://github.com/AlexxIT/XiaomiGateway3#obtain-mi-home-device-token",
            },
        }

        if user_input:
            user_input = user_input.copy()
            if not user_input.get("key"):
                retry_input = self._gateway_info_retry_input
                if (
                    retry_input
                    and retry_input["host"] == user_input["host"]
                    and retry_input["token"] == user_input["token"]
                    and self._recovered_gateway_key
                    and retry_input.get("key") == self._recovered_gateway_key
                ):
                    # HA clients may omit a form default when retrying after a
                    # gateway_info error. Preserve the recovered key for this same
                    # host/token rather than exporting it again.
                    user_input["key"] = retry_input["key"]
                elif "key" not in user_input:
                    user_input["key"] = await hass_utils.restore_gateway_key(
                        self.hass, user_input["token"]
                    )

            # A missing key on this confirmed build would make gateway_info
            # check Telnet again after reporting no_key. Offer recovery first,
            # but only when HA supports cancellable progress tasks.
            preflight_error = None
            if (
                not user_input.get("key")
                and self._supports_cancellable_recovery_progress()
            ):
                try:
                    if await self._async_offer_key_recovery(user_input):
                        return await self.async_step_key_recovery()
                except Exception as error:
                    preflight_error = self._key_recovery_error_code(error)
                    _LOGGER.debug("Gateway key recovery preflight failed: %s", preflight_error)

            # check gateway, key is optional
            info = await core_utils.gateway_info(**user_input)
            if "error" not in info:
                return self.async_create_entry(
                    title=user_input["host"], data={}, options=user_input
                )

            if preflight_error and info["error"] == "no_key":
                info["error"] = preflight_error
            kwargs["errors"] = {"base": info["error"]}
            self._gateway_info_retry_input = user_input.copy()

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
