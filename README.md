# Hubitat Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration) [![CI](https://github.com/jason0x43/hacs-hubitat/actions/workflows/ci.yml/badge.svg)](https://github.com/jason0x43/hacs-hubitat/actions/workflows/ci.yml)

This integration uses [Hubitat’s](https://hubitat.com) [Maker API](https://docs.hubitat.com/index.php?title=Hubitat™_Maker_API) to make Hubitat devices available for use with Home Assistant.

## Quick Start

1. Create a Maker API instance in Hubitat
2. Add the devices you want to share in Maker API
3. Install HACS
4. Add the Hubitat integration in HACS
5. Add an instance of the Hubitat integration in Home Assistant's Integrations page

> ⚠️ If you notice that devices aren't updating in Home Assistant, see the [Troubleshooting](#troubleshooting) section below.

## Features

The integration creates Home Assistant entities from the devices exposed by a Hubitat Maker API app. Entity types are selected from the capabilities and attributes reported by each Hubitat device; a single Hubitat device can create multiple entities.

Supported Home Assistant platforms include:

- **Alarm control panel**: security keypads, including arm/disarm, optional night arming, alarm triggering, code management, and entry/exit delays
- **Binary sensor**: acceleration, carbon monoxide, contact, connectivity, heat, moisture, motion, natural gas, network status, presence, shock, smoke, sound, tamper, and valve status
- **Climate**: thermostats with heating, cooling, setpoints, fan modes, and supported preset modes
- **Cover**: door controllers, garage doors, window blinds, window shades, and window controls
- **Event**: button event entities for pushed, held, double-tapped, and released events
- **Fan**: fan control, speed, and auto mode where reported by the device
- **Light**: on/off, dimming, color temperature, and color control when supported
- **Lock**: lock and unlock control, including code-related attributes where reported
- **Select**: a select entity for Hubitat location modes when the hub supports modes
- **Sensor**: battery, energy, power, current, voltage, temperature, humidity, illuminance, pressure, air quality, gas/VOC, rain, wind, water flow, hub status, HSM status, Hubitat mode, and other reported attributes
- **Switch**: switches, outlets, power-meter switches, and alarms
- **Valve**: valve position and open/close control

Hubitat button and lock-code events can also be used as Home Assistant device automation triggers. Devices with attributes that do not map to a built-in sensor type are exposed as disabled-by-default generic sensors.

## Installation

This component is an _integration_, which is different from an _add on_. Integrations are managed through the “Devices & Services” configuration menu rather than through “Add-ons, Backups & Supervisor”.

There are two methods for installing this integration. One is to use HACS, a tool that is used to install and update third party integrations (such as this one). The second option is to install this integration manually by cloning the repository and copying the integration files to the proper location in your HA config directory.

Note that you will need to restart Home Assistant after installation, whichever method is used.

### HACS

First, [install HACS](https://www.hacs.xyz/docs/use/configuration/basic/) if you haven't already.

Once HACS has been installed and shows up in the sidebar, open it and go to Integrations, and then click the orange '+' button in the lower right corner to add an integration. Search for “Hubitat” and install it.

### Manually

Clone this repository and copy the `custom_components/hubitat` folder into your `<config>/custom_components/` directory (so you end up with `<config>/custom_components/hubitat`).

## Setup

The basic setup process is:

1. Create a Maker API instance in Hubitat
2. Add the devices you want to use in HA to the Maker API instance
3. Setup the integration in HA

If you plan to use the integration over SSL, you‘ll probably want to enable the “Ignore SSL Certificates” toggle.

To configure the Hubitat integration, go to **Settings** › **Devices & services** in Home Assistant and click **Add integration**. Select **Hubitat**, then provide:

- The address of the hub, like `http://10.0.1.99`. You can also just provide a hostname or address `10.0.1.99` (uses HTTP by default)
- The app ID of the Maker API instance (the number after `/apps/api/` in the Maker API URLs)
- The Maker API access token
- Optional event server config (more details are below)
    - Event server URL. This is useful when Home Assistant runs in a VM or container and Hubitat cannot reach the automatically selected address. More details are below.
    - Event server port. The port is selected automatically when it is omitted. More details are below.
    - Relative paths to an SSL private key and certificate (for example, `ssl/localhost-key.pem` and `ssl/localhost.pem`). When both are provided, the event server serves HTTPS only.
- Optional: the temperature unit (default is `F`)
- Optional: **Synchronize rooms** -- this assigns Home Assistant device areas to the Hubitat rooms reported by Maker API.

### Event server

Hubitat’s official way to push events to receivers is via HTTP POST requests. Every time a device event occurs, the Maker API will make an HTTP POST request to the address set in its “URL to send device events to by POST” setting.

To receive these events, the integration starts up a Python-based web server and updates the POST URL setting in the Maker API instance to point at that server.

Note that the POST URL **must** be visible to Hubitat. Often this will be the case, but not always. For example, if your Home Assistant instance is running in Docker with host mode networking, Home Assistant's IP address will *not* be visible to Hubitat. In this case the default POST URL configured by the integration won’t work. This is where the event server options become useful. 

The key option for this use case is the **event server URL**. This is the complete URL (host + port) that Hubitat should use to access the server. Using the Docker example given earlier, this would typically be the address or hostname of the machine hosting the Docker container. The port in the URL will also be used internally for the event server.

If, for some reason, the event server needs to bind to a different port internally than the port given in the event server URL, you would use the **event server port** option. This option is also useful on its own if you want the event server to bind to a known port all the time instead of using a randomly available port.

> ⚠️ Note that the event server URL, if specified, should only include a protocol and a host, _not_ a path. The server always listens at `/`.

### Device types

The integration assigns Home Assistant device classes based on the capabilities reported by Hubitat. Sometimes the device type is ambiguous; a switchable outlet and a light switch may both only implement Hubitat’s [Switch](https://docs.hubitat.com/index.php?title=Driver_Capability_List#Switch) capability, and will therefore look like the same type of device to the integration. In some of these cases, the integration guesses the device class based on the device’s label (e.g., a switch named “Office Lamp” would be setup as a light in Home Assistant). This heuristic behavior is currently only used for lights and switches.

### Adding new devices

After adding new devices to the Maker API instance in Hubitat, you will need to **reload the integration before the devices will be controllable from Home Assistant**. You can reload the device list by opening **Settings** › **Devices & Services** › **Hubitat**, then tapping **⋮** › **Reload** for the hub instance you’ve updated. Once the integration has loaded the new device list, devices added to the Maker API instance should show up in Home Assistant.

If a switch or light was classified incorrectly, you can use the **Switches → Lights** and **Lights → Switches** override steps in the config flow. Run the hub’s config flow by opening **Settings** › **Devices & Services** › **Hubitat**, then tapping ⚙️ for the hub instance to be updated.

### Removing devices

To remove a device, first remove or disable it in the Maker API instance in Hubitat. Then open the Hubitat integration settings in Home Assistant and go through the config flow. One of the steps in the flow is “Remove devices” — this will allow you to remove any devices added by the integration.

Note that removing a device through the config flow in Home Assistant but not removing it in the Maker API in Hubitat will cause the device to be re-added the next time the integration loads (usually when you restart Home Assistant).

## Services

This integration adds several service calls to Home Assistant.

- Delete the alarm code at a given position in a lock or keypad
  ```yaml
  service: hubitat.clear_code
  data:
    entity_id: lock.some_lock
    position: 1
  ```
- Set a user code for a lock or keypad
  ```yaml
  service: hubitat.set_code
  data:
    entity_id: lock.some_lock
    position: 1
    code: 5213
    name: Guests
  ```
- Set the length of user codes for a lock or keypad
  ```yaml
  service: hubitat.set_code_length
  data:
    entity_id: lock.some_lock
    length: 4
  ```
- Get the user codes for a lock or keypad
  ```yaml
  service: hubitat.get_codes
  data:
    entity_id: lock.some_lock
  response_variable: codes
  ```
- Set the entry delay for a security keypad in seconds
  ```yaml
  service: hubitat.set_entry_delay
  data:
    entity_id: alarm_control_panel.some_alarm
    delay: 30
  ```
- Set the exit delay for a security keypad in seconds
  ```yaml
  service: hubitat.set_exit_delay
  data:
    entity_id: alarm_control_panel.some_alarm
    delay: 30
  ```
- Send a command to a Hubitat device
  ```yaml
  service: hubitat.send_command
  data:
    entity_id: switch.some_switch
    command: on
  ```
  ```yaml
  service: hubitat.send_command
  data:
    entity_id: light.some_light
    command: setHue
    args: 75
  ```
  ```yaml
  service: hubitat.send_command
  data:
    entity_id: light.some_light
    command: setLevel
    args: [50, 3]
  ```
- Activate the siren or strobe on an alarm switch
  ```yaml
  service: hubitat.alarm_siren_on
  data:
    entity_id: switch.some_alarm
  ```
  Use `hubitat.alarm_strobe_on` for the strobe.
- Set a hub's Hubitat Safety Monitor status. The `command` must be one of `armAway`, `armHome`, `armNight`, `disarm`, or `disarmAll`.
  ```yaml
  service: hubitat.set_hsm
  data:
    command: armAway
  ```
- Set a hub's location mode. The mode must exist on the target Hubitat hub.
  ```yaml
  service: hubitat.set_hub_mode
  data:
    mode: Night
  ```

The `set_hsm` and `set_hub_mode` services act on all configured Hubitat hubs by default. To target one hub, add `hub` with the first eight characters of its Maker API token (the hub ID shown in the integration).

## Event-emitting devices

Some devices, such as pushable buttons, emit events rather than having state. The integration creates Home Assistant `event` entities for button devices, with an entity for each button and event types such as `pushed`, `held`, `double_tapped`, and `released`. Locks can also expose unlock-with-code device triggers. Devices that only emit events and have no stateful components may not have any other associated entities in Home Assistant.

Event entities can be used directly as triggers in Home Assistant automations. The integration also provides Home Assistant device triggers for button events and lock code names. For Node-RED or event-based automations, listen for `hubitat_event` and filter the fields in the event data, such as `device_id`, `attribute`, and `value`.

## Updating

The update process depends on how the integration was installed. If it was installed with HACS, open the integration in HACS and click the “Upgrade” link. The process for manually updating is the same as for manual installation.

Note that you will need to restart Home Assistant after updating, whichever method is used.

## Troubleshooting

### Devices aren't updating

If the integration was set up successfully but devices aren't updating, the problem is almost always that Hubitat is unable to send messages to Home Assistant. Just because HA can talk to Hubitat does _not_ mean that Hubitat can talk back to HA. This usually happens when Home Assistant is running in a VM or Docker container that hasn't been bridged to the local network. In this situation, the URL that the integration tells Maker API to send device events to will be an address on the virtualization system's internal network, which Hubitat won't be able to address.

There are two solutions. One is to update the container or VM to use network bridging, so that the virtual system appears like a host on the local network. In this situation, HA's network address will be directly visible to Hubitat, so the integration will be able to set things up automatically.

The second solution is to manually set the event server URL in the integration to something that Hubitat _can_ see. The event server URL should point to the host that's running your Home Assistant VM or container. For example, if the host running the HA instance is on the local network at 192.168.0.10, then the host part of the event server URL would be set to http://192.168.0.10. The port should be set to some open port value (e.g., 12345).

> ⚠️ Note that the event server URL should only include a protocol and a host, _not_ a path. The server always listens at `/`.

### Checking device capabilities

If a device isn't showing up in Home Assistant in the way you expect (like, a fan is showing up as a light), the problem may be that this integration is having trouble telling what kind of device it is. The integration uses "capability" information from the Maker API to determine what type of device a given device is.

You can display the capabilities for a particular device, along with other information, by making a request to the Maker API:

```
$ curl 'http://HUBITAT_ADDRESS/apps/api/MAKER_API_ID/devices/DEVICE_ID?access_token=TOKEN&prettyPrint=true'
```

If you open your Maker API instance in Hubitat, example URLs are shown at the bottom of the page. You can query these URLs with `curl`, as shown above, or in a browser. You should see output like:

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
       custom_components.hubitat: debug
   ```
3. Restart Home Assistant

If you open Home Assistant's log file in **Settings** › **System** › **Logs** after HA restarts, and show the raw logs, you should see quite a few messages related to Hubitat (mixed in with messages for other components), like:

```
2026-08-16 13:49:31.282 WARNING (SyncWorker_0) [homeassistant.loader] We found a custom integration hubitat which has not been tested by Home Assistant. This component might cause stability problems, be sure to disable it if you experience issues with Home Assistant
2026-08-16 13:49:32.752 INFO (MainThread) [homeassistant.bootstrap] Setting up stage 2: {..., 'hubitat', ...}
2026-08-16 13:49:34.128 INFO (MainThread) [homeassistant.setup] Setting up hubitat
2026-08-16 13:49:34.128 INFO (MainThread) [homeassistant.setup] Setup of domain hubitat took 0.00 seconds
2026-08-16 13:49:34.128 DEBUG (MainThread) [custom_components.hubitat] Setting up Hubitat for 56b5611d03ee759672b4511a920c320c
2026-08-16 13:49:34.129 DEBUG (MainThread) [custom_components.hubitat.hub] Creating offline Hubitat hub instance
2026-08-16 13:49:34.129 DEBUG (MainThread) [custom_components.hubitat.hubitatmaker.hub] Setting host to http://10.0.0.57
2026-08-16 13:49:34.129 INFO (MainThread) [custom_components.hubitat.hubitatmaker.hub] Created hub <Hub host=10.0.0.57 app_id=7>
2026-08-16 13:49:34.165 INFO (MainThread) [homeassistant.components.binary_sensor] Setting up hubitat.binary_sensor
2026-08-16 13:49:34.165 DEBUG (MainThread) [custom_components.hubitat.hub] Connecting to Hubitat hub...
2026-08-16 13:49:35.929 DEBUG (MainThread) [custom_components.hubitat.hubitatmaker.hub] Loaded device list
2026-08-16 13:49:35.929 DEBUG (MainThread) [custom_components.hubitat.hubitatmaker.hub] Loading device 1
...
2026-08-16 13:49:37.875 INFO (MainThread) [homeassistant.components.valve] Setting up hubitat.valve
2026-08-16 13:49:37.875 DEBUG (MainThread) [custom_components.hubitat.device] Added device listener for 22 (<class 'custom_components.hubitat.valve.HubitatValve'>)
2026-08-16 13:49:37.875 DEBUG (MainThread) [custom_components.hubitat.hub] Registered platforms
2026-08-16 13:49:37.875 DEBUG (MainThread) [custom_components.hubitat.hub] Synchronizing device rooms...
2026-08-16 13:49:37.876 DEBUG (MainThread) [custom_components.hubitat.hub] Hub connection complete
2026-08-16 13:49:37.876 INFO (MainThread) [custom_components.hubitat] Successfully connected to Hubitat hub
2026-08-16 13:49:37.876 INFO (MainThread) [custom_components.hubitat] Hubitat is ready
...
2026-08-16 14:43:43.584 DEBUG (MainThread) [custom_components.hubitat.light] Turning off Virtual RGB Light
2026-08-16 14:43:43.585 DEBUG (MainThread) [custom_components.hubitat.hubitatmaker.hub] Sending command off(None) to 6
2026-08-16 14:43:43.678 DEBUG (MainThread) [custom_components.hubitat.device] sent off to 6
2026-08-16 14:43:43.758 DEBUG (MainThread) [custom_components.hubitat.hubitatmaker.hub] Received event: {'name': 'switch', 'value': 'off', 'displayName': 'Virtual RGB Light', 'deviceId': '6', 'descriptionText': 'Virtual RGB Light switch was turned off', 'unit': None, 'type': None, 'data': None}
2026-08-16 14:43:43.758 DEBUG (MainThread) [custom_components.hubitat.hubitatmaker.hub] Setting switch to off (None) for device 6 from api 7 at hub 10.0.0.57
```

### HSM status or modes not updating

Ensure that the “POST location events?” toggle is enabled in your Maker API app in Hubitat.

## Developing

The project uses `uv` for its Python environment and Poe the Poet for common tasks. After cloning the repository, install the development dependencies with `uv sync`.

Run code quality checks and unit tests with:

```
$ uv run poe check
$ uv run poe test
```

To start a local Home Assistant container for manual testing, run:

```sh
./home_assistant start
```

This uses the latest stable Home Assistant release. To pin a specific container version, pass it as an argument, for example `./home_assistant start 2026.6.4`. The helper requires Docker.

To run a Home Assistant smoke test against the latest stable release, run:

```sh
uv run poe smoke
```

To test one or more specific Home Assistant container versions, repeat `--ha-version`:

```sh
uv run poe smoke --ha-version 2026.2.3 --ha-version 2026.6.4
```

The smoke test starts a temporary Home Assistant container with a generated minimal Hubitat config entry and a sibling mock Maker API container, then waits for Home Assistant to report that Hubitat is ready.

---

<a href="https://www.buymeacoffee.com/jason0x43" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>
