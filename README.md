# ComfoSpot for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/v/release/Runje/comfospot-homeassistant?include_prereleases&sort=semver)](https://github.com/Runje/comfospot-homeassistant/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A **local, cloud-free** Home Assistant integration for **Zehnder ComfoSpot 55**
decentralised ventilation units behind a **ComfoControl** gateway.

It speaks the gateway's local `Flake` protocol directly over your LAN — no cloud,
no app account, no MQTT broker, no extra daemon. Fan control and sensor readings
show up as native Home Assistant entities, set up entirely through the UI.

> [!IMPORTANT]
> **Unofficial / unaffiliated.** This project is **not** made, supported, or
> endorsed by Zehnder or getair. "ComfoSpot", "ComfoControl", and "Zehnder" are
> trademarks of their respective owners and are used here only to describe
> compatibility. The protocol was reconstructed by clean-room observation of
> local network traffic for the sole purpose of interoperability. Use at your
> own risk.

## Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Entities](#entities)
- [How it works](#how-it-works)
- [Limitations](#limitations)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features

- 🌀 **Fan control** per zone — on/off and stages 1–4
- 🎯 **Target temperature** as a `number` entity (15–30 °C)
- 🌡️ **Temperature** and 💧 **humidity** per zone
- 🫁 **Air quality index** (Bosch BSEC IAQ, 0–500, lower is better)
- 🌤️ **Barometric pressure** (hPa)
- 🔍 **Auto-discovery** of the gateway via UDP broadcast
- 🏠 **100 % local** — `local_polling`, no cloud dependency, no credentials

## Requirements

- A Zehnder **ComfoSpot 55** system with a **ComfoControl** gateway on your LAN
- The gateway reachable from your Home Assistant host on the same subnet
  (discovery uses a UDP broadcast)
- Home Assistant **2024.1** or newer

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Runje&repository=comfospot-homeassistant&category=integration)

1. In HACS → **⋮** → **Custom repositories**, add
   `https://github.com/Runje/comfospot-homeassistant` with category
   **Integration** (or use the button above).
2. Install **ComfoSpot**, then restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration → ComfoSpot**.

### Manual

Copy `custom_components/comfospot` into your Home Assistant
`config/custom_components/` directory and restart Home Assistant.

## Configuration

Everything is configured from the UI — there is **nothing to add to
`configuration.yaml`**. On first add, the integration tries to auto-discover the
gateway via UDP broadcast and pre-fills its IP address; otherwise enter the
gateway's IP manually. No username or password is required (the local protocol
is unauthenticated).

## Entities

| Entity | Type | Notes |
| --- | --- | --- |
| `fan.<zone>` | Fan | On/off + stages 1–4 |
| `number.<zone>_target_temperature` | Number | 15–30 °C |
| `sensor.<zone>_temperature` | Sensor | Indoor temperature |
| `sensor.<zone>_humidity` | Sensor | Indoor relative humidity |
| `sensor.comfospot_air_quality_index` | Sensor | Bosch BSEC IAQ, 0–500, lower is better |
| `sensor.comfospot_air_pressure` | Sensor | Barometric pressure in hPa |
| `sensor.comfospot_operating_hours` | Sensor | Diagnostic |
| `sensor.comfospot_air_quality_sensor_status` | Sensor | Diagnostic — BSEC calibration state |

The gateway carries a BME680-style environmental sensor; its properties mirror
the vendor app's `humidity` / `pressure` / `temperature` / `airQualityIndex` /
`airQualityIndexAccuracy` domain model. In versions before 0.1.8 the pressure
reading was mislabelled as CO₂ and the IAQ index was exposed as "Unknown
0x1043"; existing entities are migrated automatically (history is kept, but
Home Assistant may warn once about the changed unit of the former CO₂ sensor).

The gateway is added as a hub device, and each ventilation zone appears as a
sub-device linked to it.

## How it works

The ComfoControl gateway answers a UDP broadcast on port `9987` and then accepts
a plaintext TCP control connection on port `9986` speaking the `Flake`
object-sync protocol. This integration reimplements that connection/transport
layer (dynamic tokens + ACKs) and the property model, discovers the ventilation
zone(s), and maps them to Home Assistant entities.

In a ComfoSpot **Twin** setup the three physical units act as a single
coordinated zone — alternating supply/exhaust airflow for heat recovery — so they
are presented as one fan.

## Limitations

- **Per-fan values are not exposed.** The gateway publishes only aggregated,
  per-zone values over the network. Individual fan readings live in the internal
  Bluetooth-mesh layer, which is not reachable over the LAN protocol.
- **UDP must reach the gateway.** The gateway only opens its TCP control port
  after receiving a UDP discovery packet, so Home Assistant and the gateway
  should be able to exchange UDP broadcasts (same subnet recommended).

## Troubleshooting

- **"Failed to connect" when adding the integration** — confirm the gateway IP,
  make sure Home Assistant is on the same subnet, and that no firewall/VLAN
  blocks UDP `9987` or TCP `9986`.
- **Entities show "unavailable" after a while** — this usually means the
  gateway stopped pushing updates; the integration re-subscribes on each poll to
  keep them alive. If it persists, reload the integration and open an issue with
  your Home Assistant logs (enable debug logging below).
- **Enable debug logging:**

  ```yaml
  logger:
    default: info
    logs:
      custom_components.comfospot: debug
  ```

## Contributing

Issues and pull requests are welcome! Please do **not** include any decompiled
vendor code or copyrighted firmware in contributions — this project is a
clean-room reimplementation and must stay that way. If you have a different
ComfoSpot model or a multi-zone setup, reports about what works are especially
helpful.

## License

[MIT](LICENSE) © Thomas König
