import requests
import logging
from datetime import datetime, timedelta, time
import pytz

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorDeviceClass
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from homeassistant.core import HomeAssistant
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Update once a day
MIN_TIME_BETWEEN_UPDATES = timedelta(days=1)

ATTRIBUTION = "Data provided by EnergyZero"

async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, discovery_info=None):
    async_add_entities(await setup_sensors(hass))

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    async_add_entities(await setup_sensors(hass))

async def setup_sensors(hass: HomeAssistant):
    entities = [
        EnergyZeroGasPriceSensor(hass, "Gas Price Market", "market_incl"),
        EnergyZeroGasPriceSensor(hass, "Gas Price All-in", "all_in")
    ]

    data = await hass.async_add_executor_job(get_current_gas_price)
    current_data = data.get('data', {}).get('current', {})
    prices = current_data.get('prices', [])
    if prices:
        additional_costs = prices[0].get('additionalCosts', [])
        for cost in additional_costs:
            name = cost.get('name', 'Unknown')
            entities.append(EnergyZeroGasPriceSensor(hass, f"Gas Price {name}", f"cost_{name.replace(' ', '_').lower()}"))

    return entities

def _query_energyzero_gasprice(gasCurrentFrom, gasCurrentTill):
    gql_endpoint = 'https://api.energyzero.nl/v1/gql'
    gas_qql = '''
        query EnergyMarketPricesGas($gasCurrentFrom: Time!, $gasCurrentTill: Time!) {
            current: energyMarketPrices(
                input: {from: $gasCurrentFrom, till: $gasCurrentTill, intervalType: Daily, type: Gas}
            ) {
                averageIncl
                averageExcl
                prices {
                    energyPriceExcl
                    energyPriceIncl
                    from
                    isAverage
                    till
                    type
                    vat
                    additionalCosts {
                        name
                        priceExcl
                        priceIncl
                    }
                }
            }
        }
    '''
    json_data = {
        'query': gas_qql,
        'variables': {
            'gasCurrentFrom': gasCurrentFrom,
            'gasCurrentTill': gasCurrentTill,
        },
        'operationName': 'EnergyMarketPricesGas',
    }

    try:
        response = requests.post(gql_endpoint, json=json_data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        _LOGGER.error("Error querying EnergyZero API: %s", e)
        return {}

def get_current_gas_price(tz='Europe/Amsterdam', newprices_hour=6):
    timezone = pytz.timezone(tz)
    today = datetime.now(tz=timezone).date()
    dt_today = timezone.localize(datetime.combine(today, time(hour=newprices_hour)))
    dt_tomorrow = dt_today + timedelta(days=1)

    return _query_energyzero_gasprice(
        gasCurrentFrom=dt_today.isoformat(),
        gasCurrentTill=dt_tomorrow.isoformat(),
    )

class EnergyZeroGasPriceSensor(Entity):
    def __init__(self, hass: HomeAssistant, name, price_type):
        self.hass = hass
        self._name = name
        self._price_type = price_type
        self._state = None
        self._attributes = {
            "attribution": ATTRIBUTION
        }
        self.update = Throttle(MIN_TIME_BETWEEN_UPDATES)(self._update)

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return "EUR"

    @property
    def device_class(self):
        return SensorDeviceClass.MONETARY

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def _update(self):
        try:
            data = await self.hass.async_add_executor_job(get_current_gas_price)
            current_data = data.get('data', {}).get('current', {})
            prices = current_data.get('prices', [])
            if not prices:
                _LOGGER.error("No prices found in the response")
                return
            
            first_price = prices[0]
            market_price_incl = first_price.get('energyPriceIncl', None)
            additional_costs = first_price.get('additionalCosts', [])
            
            if self._price_type == "market_incl":
                self._state = market_price_incl
            elif self._price_type == "all_in":
                if market_price_incl is not None:
                    all_additional_costs_summed = sum(item.get('priceIncl', 0) for item in additional_costs)
                    self._state = market_price_incl + all_additional_costs_summed
                else:
                    self._state = None
            else:
                # Handle additional costs
                cost_name = self._name.replace("Gas Price ", "").replace(" ", "_").lower()
                for cost in additional_costs:
                    if cost.get('name', '').replace(' ', '_').lower() == cost_name:
                        self._state = cost.get('priceIncl', None)
                        break

            self._attributes.update({
                'last_updated': datetime.now().isoformat()
            })

        except Exception as e:
            _LOGGER.error("Error fetching gas price: %s", e)

    async def async_update(self):
        # Ensure the update happens around 06:00 Amsterdam time
        now = datetime.now(pytz.timezone('Europe/Amsterdam'))
        if now.hour == 6 and now.minute < 5:
            await self._update()
