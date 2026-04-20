# El Niño Monitor

Lightweight Python tool that tracks ENSO data points from NOAA to monitor the development of a potentially record-breaking El Niño in 2026. Runs on a Raspberry Pi with weekly cron jobs and includes a Home Assistant integration.

Based on the analysis ["Something is brewing in the Pacific"](https://chrisgloninger.substack.com/p/something-is-brewing-in-the-pacific) by [Chris Gloninger](https://chrisgloninger.substack.com/), predicting a Niño 3.4 anomaly of ~2.5°C — comparable to the 1997 and 2015 Super El Niños, but on top of a baseline already 1.4-1.5°C above preindustrial levels.

## What it tracks

| Data point | Source | Frequency | Why it matters |
|------------|--------|-----------|----------------|
| Niño 3.4 SST anomaly | [NOAA CPC](https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for) | Weekly | Primary El Niño indicator — ≥0.5°C sustained = El Niño |
| Niño 1+2, 3, 4 regions | NOAA CPC | Weekly | Regional SST pattern across the equatorial Pacific |
| Subsurface heat content (0-300m) | [NOAA CPC](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ocean/index/heat_content_index.txt) | Monthly | Warm water reservoir fueling the event |
| Trade winds (850mb) | [NOAA CPC](https://www.cpc.ncep.noaa.gov/data/indices/cpac850) | Monthly | Weakening trades = El Niño locks in |
| Southern Oscillation Index | [NOAA CPC](https://www.cpc.ncep.noaa.gov/data/indices/soi) | Monthly | Atmospheric pressure pattern (negative = El Niño) |

## Current status (auto-updated weekly)

The monitor produces a prediction score (0-9) based on all indicators:

| Score | Status |
|-------|--------|
| 0-1 | Not yet supported |
| 2-3 | Early signals |
| 4-6 | Partially supported |
| 7-9 | Strongly supported |

## Sample output

```
============================================================
  EL NIÑO MONITOR — WEEKRAPPORT
  2026-04-20 14:27
============================================================

── Sea Surface Temperature (Niño regions) ──
  Week:           15APR2026
  Niño 3.4 SSTA:  +0.5°C  ↑
  Niño 3.4 SST:   28.3°C
  Niño 1+2 SSTA:  +1.8°C
  Niño 3 SSTA:    +0.6°C
  Niño 4 SSTA:    +0.9°C

  Trend Niño 3.4 (last weeks):
       18MAR2026  +0.0°C
       25MAR2026  +0.1°C  █
       01APR2026  +0.2°C  ██
       08APR2026  +0.2°C  ██
       15APR2026  +0.5°C  █████

── Subsurface Heat Content (upper 300m) ──
  130°E-80°W:     +1.38°C
  160°E-80°W:     +1.39°C
  180°W-100°W:    +1.36°C

── Trade Winds (850mb anomaly) ──
  Central Pacific: +1.0 m/s
  West Pacific:    +0.6 m/s
  (negative = weakening → favors El Niño)

── Southern Oscillation Index ──
  SOI:            +1.4
  (negative = El Niño pattern)
```

## Installation

Works on any Linux machine (Raspberry Pi, VPS, desktop). Requires Python 3.9+.

```bash
git clone https://github.com/pmolenaar/nino.git
cd nino
bash install.sh
```

This will:
- Create a virtual environment and install dependencies
- Fetch the first data set from NOAA
- Set up a weekly cron job (Sunday 08:00)
- Install and start a systemd service for the API server (port 8099)

### Manual run

```bash
.venv/bin/python nino_monitor.py
```

### Output files

- **`data/`** — CSV files with historical measurements
- **`reports/`** — text reports per week
- **`data/state.json`** — current state for the API

## Home Assistant integration

The monitor includes an HTTP API server on port `8099` that serves the current ENSO state as JSON.

### API endpoint

```
GET http://<your-ip>:8099/api/state
```

Returns:
```json
{
  "prediction_status": "Partially supported",
  "prediction_score": 4,
  "nino34_ssta": 0.5,
  "nino34_mutation": null,
  "nino34_trend": "↑",
  "heat_content": 1.38,
  "trade_wind_cpac": 1.0,
  "soi": 1.4,
  "alerts": [],
  "history_nino34": [0.1, 0.2, 0.2, 0.5]
}
```

### Sensors

Copy the REST configuration from [`homeassistant.yaml`](homeassistant.yaml) into your HA `configuration.yaml`. This creates the following sensors:

| Sensor | Description |
|--------|-------------|
| `sensor.el_nino_voorspelling` | Prediction status with score and reasoning |
| `sensor.nino_3_4_anomalie` | Current Niño 3.4 SST anomaly (°C) |
| `sensor.nino_3_4_mutatie` | Week-over-week change (°C) |
| `sensor.ocean_heat_content` | Subsurface heat content anomaly (°C) |
| `sensor.passaatwinden_centraal_pacific` | Central Pacific trade wind anomaly (m/s) |
| `sensor.soi_index` | Southern Oscillation Index |

Dashboard card examples (entities card + markdown card) are included in `homeassistant.yaml`.

### Managing the API server

```bash
sudo systemctl status nino-server
sudo systemctl restart nino-server
journalctl -u nino-server -f
```

## Alerts

Configurable in `config.json`:

| Level | Condition |
|-------|-----------|
| Warning | Niño 3.4 anomaly ≥ 2.0°C |
| Critical | Niño 3.4 anomaly ≥ 2.3°C (Super El Niño territory) |
| Warning | Subsurface heat content ≥ 1.5°C |

## Data sources

All data comes from [NOAA Climate Prediction Center](https://www.cpc.ncep.noaa.gov/data/indices/) public feeds. No API key required.

## Credits

- **[Chris Gloninger](https://chrisgloninger.substack.com/)** — meteorologist and author of the original analysis that inspired this project
- [Reddit discussion on r/climate](https://reddit.com/r/climate) — *(link will be updated once posted)*

## License

MIT
