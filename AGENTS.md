# hacs-hubitat

This is a Home Assistant integration for Hubitat hubs that allows Hubitat devices to be controlled through Home Assistant. The integration uses Hubitat's Maker API to communicate with the hub and includes a local event server to receive real-time device updates.

- The app uses `uv`. Use `uv` to run all tools
- Run integration with local Home Assistant: `./home_assistant start`

## Device Capability Mapping

- Devices are mapped to HA platforms based on Hubitat capabilities
- Some devices may appear as multiple entities (e.g., a lock with battery sensor)
- Device type detection uses heuristics for ambiguous devices (e.g., switches vs lights)

## Event Server

- Python HTTP server runs alongside Home Assistant
- Automatically configured in Hubitat's Maker API
- Port selection is automatic but can be manually configured

## Live Testing

- Start a local instance with `./home_assistant start <version>`, like
`./home_assistant start 2026.3.1`.
- Start a remote tunnel with ssh to forward event server messages:
  `ssh -R 0.0.0.0:12345:localhost:12345 hass`
