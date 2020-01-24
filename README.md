# Hubitat Integration for Home Assistant

This is an integration for Hubitat that uses Hubitat’s Maker API. Some people
are working on MQTT integrations, but a broker is just something else to manage.
😀

It currently supports the following device types (platforms) to varying degrees:

- binary_sensor
- climate
- light
- sensor
- switch

## Installation

### HACS

Add this repository as a custom repository in HACS (Marketplace -> Settings).

### Manually

Clone this repository and copy the `hubitat` folder into your
`<config>/custom_components/` directory. Be sure to copy the entire directory,
including the (possibly hidden) `.translations` subdirectory.

## Setup

First, create a Maker API instance in the Hubitat UI. Add whatever devices you'd
like to make available to Home Assistant.

To configure the hubitat integration, go to Configuration -> Integrations in the
Home Assistant UI and click the “+” button to add a new integration. Pick
“Hubitat”, then provide:

- The address of the hub (e.g., `http://10.0.1.99` or just `10.0.1.99` if you’re
  not using https)
- The app ID of the Maker API instance (the 3 or 4 digit number after
  `/apps/api/` in any of the Maker API URLs)
- The API access token
