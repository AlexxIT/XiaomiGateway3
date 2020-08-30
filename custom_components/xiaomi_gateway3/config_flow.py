import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow

from . import DOMAIN, gateway3

_LOGGER = logging.getLogger(__name__)


class XiaomiGateway3FlowHandler(ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        """GUI > Configuration > Integrations > Plus > Xiaomi Gateway 3"""
        error = None

        if user_input is not None:
            error = gateway3.is_gw3(user_input['host'], user_input['token'])
            if not error:
                return self.async_create_entry(title=user_input['host'],
                                               data=user_input)

        return self.async_show_form(
            step_id='user',
            data_schema=vol.Schema({
                vol.Required('host'): str,
                vol.Required('token'): str,
            }),
            description_placeholders={
                'error_text': "\nERROR: " + error if error else ''
            }
        )
