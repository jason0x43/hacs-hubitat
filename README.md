# Hubitat Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

This integration uses [Hubitat’s](hubitat.com) [Maker API](https://docs.hubitat.com/index.php?title=Hubitat™_Maker_API) to make Hubitat devices available for use with Home Assistant.

The following device types (platforms) are currently supported:

- binary_sensor
  - acceleration
  - carbon monoxide
  - contact
  - moisture
  - motion
  - smoke
- climate
  - thermostat
  - fan
- cover
  - door controller
  - garage door controller
  - window shade
- light
- sensor
  - battery
  - humidity
  - illuminance
  - power (watts)
  - temperature
  - voltage
- switch
- fan

## Installation

### HACS

Add this repository as a custom repository in HACS (Marketplace -> Settings).

### Manually

Clone this repository and copy the `hubitat` folder into your `<config>/custom_components/` directory. Be sure to copy the entire directory, including the (possibly hidden) `.translations` subdirectory.

## Setup

First, create a Maker API instance in the Hubitat UI. Add whatever devices you'd like to make available to Home Assistant.

To configure the hubitat integration, go to Configuration -> Integrations in the Home Assistant UI and click the “+” button to add a new integration. Pick “Hubitat”, then provide:

- The address of the hub (e.g., `http://10.0.1.99` or just `10.0.1.99` if you’re not using https)
- The app ID of the Maker API instance (the 3 or 4 digit number after `/apps/api/` in any of the Maker API URLs)
- The API access token
- Optionally a port for the event listener server to listen on (this will be chosen automatically by default)

## Network setup

Hubitat must be able to see your Home Assistant server on your local network to be able to push device events to it. The integration will start its own web server on a random port on whatever device Home Assistant is running on to listen for these events.

## Device types

The integration assigns Home Assistant device classes based on the capabilities reported by Hubitat. Sometimes the device type is ambiguous; a switchable outlet and a light switch both look like simple switches. In these cases, the
integration guesses the device class based on the device's label (e.g., a switch named "Office Lamp" would be setup as a light in Home Assistant). This heuristic behavior is currently only used for lights and switches.
