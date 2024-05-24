# EnergyZero Gas Price Sensor

![EnergyZero Gas Price Sensor](https://brands.home-assistant.io/energyzero/icon.png)

This Home Assistant custom component fetches and displays the current gas prices from the EnergyZero API, including the market price, all-in price, and additional cost components such as energy tax and purchasing cost.

## Features

- Fetches current gas prices from the EnergyZero API
- Displays market price, all-in price, and additional cost components
- Provides sensors for Home Assistant


## Installation

### HACS (Home Assistant Community Store)

1. Ensure that HACS is installed in your Home Assistant setup.
2. Add this repository to HACS as a custom repository:
   - Go to HACS > Integrations
   - Click the three dots in the top right corner and select "Custom repositories"
   - Add the repository URL: `https://github.com/Sikerdebaard/energyzero-all-in-gasprice`
   - Select the category as "Integration"
3. Find "EnergyZero Gas Price Sensor" in the HACS store and install it.

### Manual Installation

1. Download the `energyzero-all-in-gasprice` repository.
2. Copy the `energyzero_gas_price_sensor` directory to your Home Assistant's `custom_components` directory.
3. Restart Home Assistant.

## Configuration

1. Go to the Home Assistant UI.
2. Navigate to `Configuration` > `Devices & Services`.
3. Click `Add Integration` and search for `EnergyZero Gas Price`.
4. Follow the prompts to complete the setup.

The integration will create sensors for the market price (including VAT), the all-in price (including VAT and additional costs), and dynamic sensors for each additional cost component.

## Sensors

- `sensor.gas_price_market`: The market price of gas including VAT.


## Sensors

- `sensor.energyzero_gql_sensor_market_incl`: The market price of gas including VAT.
- `sensor.energyzero_gql_sensor_all_in`: The all-in price of gas including VAT and all additional costs.
- Additional sensors for each dynamic cost component such as `sensor.energyzero_gql_sensor_cost_energy_tax`, `sensor.energyzero_gql_sensor_cost_purchasing_cost`, etc.

## Attribution

Data provided by [EnergyZero](https://www.energyzero.nl).

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Author

[Sikerdebaard](https://github.com/Sikerdebaard)
