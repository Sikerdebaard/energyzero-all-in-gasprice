from homeassistant.core import HomeAssistant
from homeassistant.helpers import discovery
from .const import DOMAIN

async def async_setup(hass: HomeAssistant, config: dict):
    return True

async def async_setup_entry(hass: HomeAssistant, entry):
    hass.async_create_task(
        discovery.async_load_platform(hass, "sensor", DOMAIN, {}, entry)
    )
    return True

async def async_unload_entry(hass: HomeAssistant, entry):
    return True