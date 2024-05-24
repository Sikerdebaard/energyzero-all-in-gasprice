import requests
import logging
from datetime import datetime, timedelta, time
import pytz

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity, SensorDeviceClass
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Update every 15 minutes
UPDATE_INTERVAL = timedelta(minutes=15)

ATTRIBUTION = "Data provided by EnergyZero"

async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, discovery_info=None):
    _LOGGER.warn("Setting up platform...")
    await async_setup_entry(hass, config, async_add_entities)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    _LOGGER.warn("Setting up entry for sensors...")

    coordinator = EnergyZeroGasPriceCoordinator(hass)
    await coordinator.async_config_entry_first_refresh()

    sensors = [
        EnergyZeroGasPriceSensor(coordinator, "Gas Price Market", "market_incl"),
        EnergyZeroGasPriceSensor(coordinator, "Gas Price All-in", "all_in")
    ]

    # Fetch data for additional sensors
    data = coordinator.data
    _LOGGER.warn("Fetched gas price data: %s", data)
    current_data = data.get('data', {}).get('current', {})
    prices = current_data.get('prices', [])
    if prices:
        additional_costs = prices[0].get('additionalCosts', [])
        for cost in additional_costs:
            name = cost.get('name', 'Unknown')
            sensors.append(EnergyZeroGasPriceSensor(coordinator, f"Gas Price {name}", f"cost_{name.replace(' ', '_').lower()}"))

    _LOGGER.warn("Sensors setup complete with entities: %s", sensors)
    async_add_entities(sensors, update_before_add=True)

class EnergyZeroGasPriceCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant):
        super().__init__(
            hass,
            _LOGGER,
            name="EnergyZeroGasPrice",
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self):
        return await self.hass.async_add_executor_job(get_current_gas_price)

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

class EnergyZeroGasPriceSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: EnergyZeroGasPriceCoordinator, name, price_type):
        super().__init__(coordinator)
        _LOGGER.warn("Initializing sensor: %s with type: %s", name, price_type)
        self._name = name
        self._price_type = price_type
        self._state = None
        self._attributes = {
            "attribution": ATTRIBUTION
        }

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

    @property
    def available(self):
        return self.coordinator.last_update_success

    async def async_update(self):
        await self.coordinator.async_request_refresh()

    @property
    def should_poll(self):
        return False

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data
        _LOGGER.warn("Fetched gas price data in update: %s", data)
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
        _LOGGER.warn("Updated sensor state: %s to: %s", self._name, self._state)
        self.async_write_ha_state()
