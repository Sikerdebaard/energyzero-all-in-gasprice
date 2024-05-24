from homeassistant.core import HomeAssistant

DOMAIN = "energyzero_gas_price_sensor"

async def async_setup(hass: HomeAssistant, config: dict):
    return True