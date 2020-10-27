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
* [Troubleshooting](#troubleshooting)
  * [Checking device capabilities](#checking-device-capabilities)
  * [Logging](#logging)
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
  - pressure
- switch

## Installation

Note that you will need to restart Home Assistant after installion, whichever method is used.

### HACS

In HACS, go to Integrations, and then click the orange '+' button in the lower right corner to add an integration. Search for "Hubitat" and install it.

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

## Troubleshooting

### Checking device capabilities

If a device isn't showing up in Home Assistant in the way you expect (like, a fan is showing up as a light), the problem may be that this integration is having trouble telling what kind of device it is. The integration uses "capability" information from the Maker API to determine what type of device a given device is.

You can display the capabilities for a particular device, along with other information, by making a request to the Maker API:

```
$ curl 'http://HUBITAT_ADDRESS/apps/api/MAKER_API_ID/devices/DEVICE_ID?access_token=TOKEN&prettyPrint=true
```

If you open your Maker API instance in Hubitat, example URLs are shown at the bottom of the page. You can query these URLs using a command like command like `curl`, as show above, or in a browser. You should see output like:

<details>
  <summary>(Expand for sample output)</summary>
<pre>
{
    "id": "2178",
    "name": "Virtual RGB light",
    "label": "Virtual RGB light",
    "attributes": [
        {
            "name": "RGB",
            "currentValue": null,
            "dataType": "STRING"
        },
        {
            "name": "color",
            "currentValue": null,
            "dataType": "STRING"
        },
        {
            "name": "colorName",
            "currentValue": "Blue",
            "dataType": "STRING"
        },
        {
            "name": "hue",
            "currentValue": 66,
            "dataType": "NUMBER"
        },
        {
            "name": "level",
            "currentValue": 74,
            "dataType": "NUMBER"
        },
        {
            "name": "saturation",
            "currentValue": 57,
            "dataType": "NUMBER"
        },
        {
            "name": "switch",
            "currentValue": "on",
            "dataType": "ENUM",
            "values": [
                "on",
                "off"
            ]
        },
        {
            "name": "switch",
            "currentValue": "on",
            "dataType": "ENUM",
            "values": [
                "on",
                "off"
            ]
        }
    ],
    "capabilities": [
        "Switch",
        {
            "attributes": [
                {
                    "name": "switch",
                    "dataType": null
                }
            ]
        },
        "SwitchLevel",
        {
            "attributes": [
                {
                    "name": "level",
                    "dataType": null
                }
            ]
        },
        "ColorControl",
        {
            "attributes": [
                {
                    "name": "hue",
                    "dataType": null
                },
                {
                    "name": "saturation",
                    "dataType": null
                },
                {
                    "name": "color",
                    "dataType": null
                },
                {
                    "name": "colorName",
                    "dataType": null
                },
                {
                    "name": "RGB",
                    "dataType": null
                }
            ]
        },
        "Actuator",
        "Light",
        {
            "attributes": [
                {
                    "name": "switch",
                    "dataType": null
                }
            ]
        }
    ],
    "commands": [
        "off",
        "off",
        "on",
        "on",
        "setColor",
        "setHue",
        "setLevel",
        "setSaturation"
    ]
}
</pre>
</details>
<br>

If you open an issue for a broken device, this information may be useful to include.

### Logging

If you run into problems, one of the first steps to take is to enable debug logging for the Hubitat integration. This will provide more insight into what the integration is doing, and may help track down problems. To enable debug logging:

1. Open your Home Assistant `configuration.yaml` file in an editor
2. Add the following content. If you already have a `logger` section, add the `hubitatmaker` and `custom_components.hubitat` lines to it.
   ```yaml
   logger:
     default: info
     logs:
       hubitatmaker: debug
       custom_components.hubitat: debug
   ```
3. Restart Home Assistant

If you open Home Assistant's log file (`config/home-assistant.log`) after HA restarts, you should see quite a few messages related to hubitat (mixed in with messages for other components), like:

```
2020-05-19 08:28:07 DEBUG (MainThread) [hubitatmaker.hub] Setting host to 10.0.1.99
2020-05-19 08:28:07 DEBUG (MainThread) [hubitatmaker.hub] Set mac to ab:cd:ef:12:34:56
2020-05-19 08:28:07 INFO (MainThread) [hubitatmaker.hub] Created hub <Hub host=10.0.1.99 app_id=2269>
2020-05-19 08:28:07 DEBUG (MainThread) [hubitatmaker.hub] Listening on 10.0.1.206:39513
2020-05-19 08:28:07 INFO (MainThread) [hubitatmaker.hub] Setting event update URL to http://10.0.1.206:39513
...
2020-05-19 08:28:08 DEBUG (MainThread) [hubitatmaker.hub] Loaded device list
2020-05-19 08:28:08 DEBUG (MainThread) [hubitatmaker.hub] Loading device 6
2020-05-19 08:28:08 DEBUG (MainThread) [hubitatmaker.hub] Loaded device 6
2020-05-19 08:28:08 DEBUG (MainThread) [hubitatmaker.hub] Loading device 14
...
2020-05-19 08:28:14 DEBUG (MainThread) [custom_components.hubitat.entities] Migrating unique_ids for binary_sensor...
2020-05-19 08:28:14 DEBUG (MainThread) [custom_components.hubitat.entities] Checking for existence of entity 10.0.1.99::2269::14::acceleration...
2020-05-19 08:28:14 DEBUG (MainThread) [custom_components.hubitat.entities] Checking for existence of entity 10.0.1.99::2269::1122::acceleration...
2020-05-19 08:28:14 DEBUG (MainThread) [custom_components.hubitat.entities] Checking for existence of entity 10.0.1.99::2269::1890::acceleration...
2020-05-19 08:28:14 DEBUG (MainThread) [custom_components.hubitat.entities] Checking for existence of entity 10.0.1.99::2269::1954::acceleration...
2020-05-19 08:28:14 DEBUG (MainThread) [custom_components.hubitat.entities] Added HubitatAccelerationSensor entities: [<Entity Barn Sensor acceleration: off>, <Entity Garage Sensor acceleration: off>, <Entity Garage Door Sensor acceleration: off>, <Entity Breezeway Sensor acceleration: off>]
...
2020-05-19 08:28:15 DEBUG (MainThread) [custom_components.hubitat.device_trigger] Attaching trigger {'platform': 'event', 'event_type': 'hubitat_event', 'event_data': {'device_id': '180', 'name': 'pushed', 'value': '1'}}
...
2020-05-19 08:28:18 DEBUG (MainThread) [custom_components.hubitat.light] Turning off Basement Hearth Lights
2020-05-19 08:28:18 DEBUG (MainThread) [hubitatmaker.hub] Sending command off() to 1510
...
```

## Developing

To get setup for development, clone this repo and run

```
$ ./dev init
```

This script will setup the tools needed to validate typings and code style. Whenever you make a commit to the repo, validators will be automatically run.

To run the type checker and unit tests, run

```
$ ./dev test
```
