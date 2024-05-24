from homeassistant.core import HomeAssistant
from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    _LOGGER.info("Setting up component...")
    return True

async def async_setup_entry(hass: HomeAssistant, entry):
    _LOGGER.info("Setting up entry for domain: %s", DOMAIN)
    hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, "sensor"))
    return True

async def async_unload_entry(hass: HomeAssistant, entry):
    _LOGGER.info("Unloading entry for domain: %s", DOMAIN)
    return await hass.config_entries.async_forward_entry_unload(entry, "sensor")
