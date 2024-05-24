import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN

class EnergyZeroConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EnergyZero."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            return self.async_create_entry(title="EnergyZero", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EnergyZeroOptionsFlowHandler(config_entry)

class EnergyZeroOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(step_id="init", data_schema=vol.Schema({}))
