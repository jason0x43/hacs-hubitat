# hacs-hubitat

This file provides guidance to AI agents when working with code in this repository.

## Project Overview

This is a Home Assistant integration for Hubitat hubs that allows Hubitat devices to be controlled through Home Assistant. The integration uses Hubitat's Maker API to communicate with the hub and includes a local event server to receive real-time device updates.

## Development Commands

### Requirements

- Python >=3.13.2
- Home Assistant >=2025.4.0

### Development Setup

- Initialize development environment: `uv sync`

### Testing

- Run tests: `uv run pytest`
- Test with specific pattern: `uv run pytest -k "test_pattern"`

### Code Quality

- Type checking: `uv run ty check`
- Linting: `uv run ruff check`
- Format code: `uv run ruff format`

### Package Management

- Install dependencies: `uv sync`
- Add development dependency: `uv add --dev <package>`

### Local Development

- Run integration with local Home Assistant: `./home_assistant start`
- Pre-commit hooks run automatically on commit (ruff + type checking)
- Install pre-commit manually: `uv run pre-commit install`

### Publishing

- Create new release: `python scripts/publish.py` (prompts for version, creates tag, pushes)

## Architecture

### Core Components

**Integration Entry Point** (`custom_components/hubitat/__init__.py`):

- Manages the lifecycle of the integration
- Handles config entry setup/unload
- Registers services and event listeners

**Hub Management** (`custom_components/hubitat/hub.py`):

- Central hub class that manages connection to Hubitat
- Handles device discovery and registration
- Manages the event server for real-time updates
- Coordinates between Home Assistant and Hubitat devices

**Hubitat Maker Library** (`custom_components/hubitat/hubitatmaker/`):

- Low-level communication with Hubitat's Maker API
- Device modeling and event handling
- HTTP server for receiving device events from Hubitat

### Device Platforms

The integration supports multiple Home Assistant platforms, each in its own file:

- `alarm_control_panel.py` - Home security systems
- `binary_sensor.py` - Motion, contact, smoke, etc.
- `climate.py` - Thermostats and HVAC controls
- `cover.py` - Garage doors, window shades
- `event.py` - Event entities
- `fan.py` - Fan controls
- `light.py` - Lights with various capabilities (dimming, color, etc.)
- `lock.py` - Door locks and keypads
- `sensor.py` - Temperature, humidity, battery, etc.
- `switch.py` - Basic on/off switches
- `valve.py` - Water valves

### Configuration Flow

**Config Flow** (`custom_components/hubitat/config_flow.py`):

- Handles initial setup wizard
- Device discovery and selection
- SSL configuration for event server
- Device removal workflow

### Event System

The integration uses a bi-directional communication model:

1. **Control**: Home Assistant → Hubitat via Maker API HTTP requests
2. **Updates**: Hubitat → Home Assistant via HTTP POST to local event server

The event server is automatically configured in the Maker API instance to push device updates in real-time.

## Key Configuration

### Manifest (`custom_components/hubitat/manifest.json`)

- Integration metadata and Home Assistant compatibility
- No external dependencies (uses built-in HTTP libraries)

### Constants (`custom_components/hubitat/const.py`)

- Platform definitions, configuration keys
- Device capability mappings
- Event types and trigger definitions

## Development Notes

### Git Workflow

- Main branch: `master` (not `main`)
- PRs should target `master`

### Device Capability Mapping

- Devices are mapped to HA platforms based on Hubitat capabilities
- Some devices may appear as multiple entities (e.g., a lock with battery sensor)
- Device type detection uses heuristics for ambiguous devices (e.g., switches vs lights)

### Event Server Architecture

- Python HTTP server runs alongside Home Assistant
- Automatically configured in Hubitat's Maker API
- Supports SSL for secure communication
- Port selection is automatic but can be manually configured

### Testing Strategy

- Unit tests focus on device mapping and capability detection
- Mock Hubitat API responses for predictable testing
- Integration tests validate the full setup flow

### Testing Gotchas

- **Device classes**: Device class assignment is based on capabilities. When adding new device types, verify `device_class` is set correctly (see tests/test_*.py for patterns).
- **Mock responses**: Mock data in `tests/hubitatmaker/` should match real Hubitat API responses for accuracy.

### Dependencies

- Uses `uv` for dependency management
- Built-in Home Assistant libraries for core functionality
