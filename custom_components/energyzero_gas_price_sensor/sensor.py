"""Support for EnergyZero gas price sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

import requests
import pytz

from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CURRENCY_EURO,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Update every 15 minutes
UPDATE_INTERVAL = timedelta(minutes=15)

@dataclass(frozen=True, kw_only=True)
class EnergyZeroGasPriceSensorEntityDescription(SensorEntityDescription):
    """Describes an EnergyZero gas price sensor entity."""

    value_fn: Callable[[dict], float | None]


SENSORS: tuple[EnergyZeroGasPriceSensorEntityDescription, ...] = (
    EnergyZeroGasPriceSensorEntityDescription(
        key="market_incl",
        name="Gas Price Market",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfVolume.CUBIC_METERS}",
        value_fn=lambda data: data.get('market_incl'),
    ),
    EnergyZeroGasPriceSensorEntityDescription(
        key="all_in",
        name="Gas Price All-in",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfVolume.CUBIC_METERS}",
        value_fn=lambda data: data.get('all_in'),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up EnergyZero gas price sensors based on a config entry."""
    coordinator = EnergyZeroGasPriceCoordinator(hass)
    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        EnergyZeroGasPriceSensorEntity(
            coordinator=coordinator,
            description=description,
        )
        for description in SENSORS
    )

    # Fetch additional sensors from the initial data
    data = coordinator.data
    _LOGGER.warn("Fetched gas price data: %s", data)
    current_data = data.get('data', {}).get('current', {})
    prices = current_data.get('prices', [])
    if prices:
        additional_costs = prices[0].get('additionalCosts', [])
        additional_sensors = [
            EnergyZeroGasPriceSensorEntity(
                coordinator=coordinator,
                description=EnergyZeroGasPriceSensorEntityDescription(
                    key=f"cost_{cost.get('name', 'Unknown').replace(' ', '_').lower()}",
                    name=f"Gas Price {cost.get('name', 'Unknown')}",
                    state_class=SensorStateClass.MEASUREMENT,
                    native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfVolume.CUBIC_METERS}",
                    value_fn=lambda data, cost=cost: cost.get('priceIncl'),
                )
            )
            for cost in additional_costs
        ]
        async_add_entities(additional_sensors)


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


class EnergyZeroGasPriceSensorEntity(CoordinatorEntity[EnergyZeroGasPriceCoordinator], SensorEntity):
    """Defines an EnergyZero gas price sensor."""

    entity_description: EnergyZeroGasPriceSensorEntityDescription

    def __init__(
        self,
        *,
        coordinator: EnergyZeroGasPriceCoordinator,
        description: EnergyZeroGasPriceSensorEntityDescription,
    ) -> None:
        """Initialize EnergyZero gas price sensor."""
        super().__init__(coordinator=coordinator)
        self.entity_description = description
        self.entity_id = (
            f"{SENSOR_DOMAIN}.{DOMAIN}_{description.key}"
        )
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            manufacturer="EnergyZero",
            name="EnergyZero Gas Price Sensor",
        )

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)
