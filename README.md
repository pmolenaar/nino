# El Niño Monitor

Wekelijkse tracker voor ENSO-datapoints van NOAA, gebaseerd op de voorspelling van een potentieel recordbrekende El Niño in 2026 ([bron](https://chrisgloninger.substack.com/p/something-is-brewing-in-the-pacific)).

## Wat wordt gemonitord

| Datapoint | Bron | Frequentie |
|-----------|------|------------|
| Niño 3.4 SST anomalie | NOAA CPC | Wekelijks |
| Niño 1+2, 3, 4 SST anomalieën | NOAA CPC | Wekelijks |
| Subsurface heat content (0-300m) | NOAA CPC | Maandelijks |
| Passaatwinden (850mb, centraal + west Pacific) | NOAA CPC | Maandelijks |
| Southern Oscillation Index | NOAA CPC | Maandelijks |

## Installatie (Raspberry Pi)

```bash
git clone https://github.com/pmolenaar/nino.git
cd nino
bash install.sh
```

Dit maakt een virtual environment aan, installeert dependencies, en stelt een wekelijkse cron job in (zondag 08:00).

## Handmatig draaien

```bash
.venv/bin/python nino_monitor.py
```

## Output

- **Terminal**: weekrapport met huidige waarden, trends, en alerts
- **`data/`**: CSV-bestanden met historische metingen
- **`reports/`**: tekstbestanden per week

## Alerts

Configureerbaar in `config.json`:

- **Warning**: Niño 3.4 anomalie ≥ 2.0°C
- **Critical**: Niño 3.4 anomalie ≥ 2.3°C (Super El Niño niveau)
- **Warning**: Subsurface heat content ≥ 1.5°C

## Context

De voorspelling is dat de Niño 3.4 anomalie ~2.5°C kan bereiken — vergelijkbaar met de Super El Niño's van 1997 en 2015, maar bovenop een baseline die al 1.4-1.5°C boven pre-industrieel niveau ligt.
