import requests
import logging
from datetime import datetime, timedelta
import pytz

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import DEVICE_CLASS_MONETARY
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

# Update once a day
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=30)

def setup_platform(hass, config, add_entities, discovery_info=None):
    add_entities([
        EnergyZeroGasPriceSensor("Gas Price Market with VAT", "marketPrice"),
        EnergyZeroGasPriceSensor("Gas Price with Energy Taxes and VAT", "priceWithEnergyTaxes"),
        EnergyZeroGasPriceSensor("Gas Price All-in with VAT", "allInPrice")
    ], True)

class EnergyZeroGasPriceSensor(Entity):
    def __init__(self, name, price_type):
        self._name = name
        self._price_type = price_type
        self._state = None
        self.update = Throttle(MIN_TIME_BETWEEN_UPDATES)(self._update)

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return "€/m3"

    @property
    def device_class(self):
        return DEVICE_CLASS_MONETARY

    def _update(self):
        try:
            response = requests.get('https://api.energyzero.nl/v1/energyprices')
            data = response.json()

            if self._price_type in data:
                self._state = data[self._price_type]
            else:
                _LOGGER.error("Price type '%s' not found in response", self._price_type)

        except Exception as e:
            _LOGGER.error("Error fetching gas price: %s", e)

    def update(self):
        # Ensure the update happens around 06:00 Amsterdam time
        now = datetime.now(pytz.timezone('Europe/Amsterdam'))
        if now.hour == 6 and now.minute > 20:
            self._update()