# ComfoSpot for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A **local, cloud-free** Home Assistant integration for **Zehnder ComfoSpot 55**
decentralised ventilation units behind a **ComfoControl** gateway.

It talks the gateway's local `Flake` protocol directly over your LAN — no cloud,
no MQTT broker, no extra daemon. Fan control and sensor readings appear as native
Home Assistant entities.

> [!IMPORTANT]
> **Unofficial / unaffiliated.** This project is **not** made, supported or
> endorsed by Zehnder or getair. "ComfoSpot", "ComfoControl" and "Zehnder" are
> trademarks of their respective owners and are used here only to describe
> compatibility. The protocol was reconstructed by clean-room observation of
> network traffic for the sole purpose of interoperability. Use at your own risk.

## Features

- 🌀 **Fan control** per zone — on/off and stages 1–4
- 🎯 **Target temperature** (number entity)
- 🌡️ **Temperature** and 💧 **humidity** per zone
- 🫁 **Air quality** (CO₂, ppm)
- 🔧 **Devices in mesh** (diagnostic) — best-effort count of connected fan units
- 🏠 **100 % local** — `local_polling`, no cloud dependency

## How it works

The ComfoControl gateway answers a UDP broadcast on port `9987` and then accepts
a plaintext TCP control connection on port `9986` speaking the `Flake` object-sync
protocol. This integration reimplements that connection/transport layer and the
property model, discovers the ventilation zone(s), and maps them to Home Assistant
entities. The three physical ComfoSpot units of a Twin setup act as a single
coordinated zone (alternating supply/exhaust for heat recovery), so they appear as
one fan.

## Requirements

- A Zehnder **ComfoSpot 55** system with a **ComfoControl** gateway on your LAN
- The gateway reachable from your Home Assistant host (same subnet recommended,
  since discovery uses a UDP broadcast)
- Home Assistant 2024.1 or newer

## Installation

### HACS (recommended)

1. In HACS → **⋮** → **Custom repositories**, add
   `https://github.com/koenigthomas/comfospot-homeassistant` with category
   **Integration**.
2. Install **ComfoSpot**, then restart Home Assistant.
3. **Settings → Devices & Services → Add Integration → ComfoSpot**.

### Manual

Copy `custom_components/comfospot` into your Home Assistant `config/custom_components/`
directory and restart Home Assistant.

## Configuration

The integration is configured from the UI. On first add it tries to auto-discover
the gateway via UDP broadcast and pre-fills the IP address; otherwise enter the
gateway's IP manually. No username or password is required (the local protocol is
unauthenticated).

## Entities

| Entity | Type | Notes |
| --- | --- | --- |
| `fan.<zone>` | Fan | On/off + stages 1–4 |
| `number.<zone>_target_temperature` | Number | 15–30 °C |
| `sensor.<zone>_temperature` | Sensor | Indoor temperature |
| `sensor.<zone>_humidity` | Sensor | Indoor relative humidity |
| `sensor.comfospot_air_quality` | Sensor | CO₂ in ppm |
| `sensor.comfospot_devices_in_mesh` | Sensor | Diagnostic, best-effort |

## Limitations / notes

- Individual per-fan sensor values are **not** exposed by the gateway over the
  network — only the aggregated zone values. Per-fan data lives in the internal
  Bluetooth-mesh layer.
- "Devices in mesh" is a best-effort reading and its exact semantics are not
  officially documented.
- The gateway only opens the TCP control port after a UDP discovery packet, so
  Home Assistant and the gateway should be able to exchange UDP broadcasts.

## Contributing

Issues and pull requests are welcome. Please do **not** include any decompiled
vendor code or copyrighted firmware in contributions.

## License

[MIT](LICENSE) © Thomas König
