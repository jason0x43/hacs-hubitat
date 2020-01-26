{% if prerelease %}This is a beta version!{% endif %}

# Hubitat Integration

This is an integration for Hubitat that uses Hubitat’s Maker API. It currently
supports the following device types (platforms) to varying degrees:

- binary_sensor
- climate
- light
- sensor
- switch

Please see the
[README](https://github.com/jason0x43/hacs-hubitat/blob/master/README.md) for
more information.

## Setup

First, create a Maker API instance in the Hubitat UI. Add whatever devices you'd
like to make available to Home Assistant. Take note of the instance’s app ID
and access token.

To configure the hubitat integration, go to Configuration -> Integrations in the
Home Assistant UI and click the “+” button to add a new integration. Pick
“Hubitat”, then provide:

- The address of the hub (e.g., `http://10.0.1.99` or just `10.0.1.99` if you’re
  not using https)
- The app ID of the Maker API instance (the 3 or 4 digit number after
  `/apps/api/` in any of the Maker API URLs)
- The API access token

After you’ve configured the integration, it will connect to your Hubitat hub
and create devices in Home Assistant for all the devices that were included in
the Maker API instance.
