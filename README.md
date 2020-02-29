# Hubitat Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

This integration uses [Hubitat’s](hubitat.com) [Maker API](https://docs.hubitat.com/index.php?title=Hubitat™_Maker_API) to make Hubitat devices available for use with Home Assistant.

<!-- vim-markdown-toc GFM -->

* [Features](#features)
* [Installation](#installation)
  * [HACS](#hacs)
  * [Manually](#manually)
* [Setup](#setup)
  * [Event server](#event-server)
  * [Device types](#device-types)
* [Updating](#updating)
* [Developing](#developing)

<!-- vim-markdown-toc -->

## Features

The following device types are currently supported. The first level bullets are Home Assistant platforms, while the sub-bullets are specific device classes.

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
- fan
- light
- sensor
  - battery
  - humidity
  - illuminance
  - power (watts)
  - temperature
  - voltage
- switch

## Installation

Note that you will need to restart Home Assistant after installion, whichever method is used.

### HACS

Add this repository as a custom repository in HACS (Marketplace -> Settings).

### Manually

Clone this repository and copy the `custom_components/hubitat` folder into your `<config>/custom_components/` directory (so you end up with `<config>/custom_components/hubitat`). Be sure to copy the entire directory, including the (possibly hidden) `.translations` subdirectory.

## Setup

First, create a Maker API instance in the Hubitat UI. Add whatever devices you’d like to make available to Home Assistant.

To configure the hubitat integration, go to Configuration -> Integrations in the Home Assistant UI and click the “+” button to add a new integration. Pick “Hubitat”, then provide:

- The address of the hub (e.g., `http://10.0.1.99` or just `10.0.1.99` if you’re not using https)
- The app ID of the Maker API instance (the 3 or 4 digit number after `/apps/api/` in any of the Maker API URLs)
- The API access token
- A port for the event server to listen on (more about this below); this will be chosen automatically by default

### Event server

Hubitat’s official way to push events to receivers is via HTTP POST requests. Every time a device event occurs, the Maker API will make an HTTP POST request to the address set in its “URL to send device events to by POST” setting.

To receive these events, the integration starts up a Python-based web server and updates the POST URL setting in the Maker API instance. Note that for this to work, Hubitat must be able to see your Home Assistant server on your local network.

### Device types

The integration assigns Home Assistant device classes based on the capabilities reported by Hubitat. Sometimes the device type is ambiguous; a switchable outlet and a light switch may both only implement Hubitat’s [Switch](https://docs.hubitat.com/index.php?title=Driver_Capability_List#Switch) capability, and will therefore look like the same type of device to the integration. In some of these cases, the integration guesses the device class based on the device’s label (e.g., a switch named “Office Lamp” would be setup as a light in Home Assistant). This heuristic behavior is currently only used for lights and switches.

## Updating

The update process depends on how the integration was installed. If it was installed with HACS, open the integration in HACS and click the “Upgrade” link. The process for manually updating is the same as for manual installation.

Note that you will need to restart Home Assistant after updating, whichever method is used.

## Developing

To get setup for development, clone this repo and run `init.sh`. This script will setup the tools needed to validate typings and code style. Whenever you make a commit to the repo, validators will be automatically run. You can also run validators manually with pipenv:

- `pipenv run black` - formatting
- `pipenv run flake8` - linting
- `pipenv run mypy` - type checking
