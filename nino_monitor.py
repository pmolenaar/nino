#!/usr/bin/env python3
"""
El Niño Monitor — wekelijkse NOAA data tracker voor Raspberry Pi.

Haalt ENSO-gerelateerde datapoints op van NOAA en genereert
een rapport met trends en alerts.
"""

import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "config.json"


def load_config():
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    cfg["data_dir"] = SCRIPT_DIR / cfg["data_dir"]
    cfg["reports_dir"] = SCRIPT_DIR / cfg["reports_dir"]
    cfg["data_dir"].mkdir(exist_ok=True)
    cfg["reports_dir"].mkdir(exist_ok=True)
    return cfg


def fetch_text(url: str) -> str:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_weekly_sst(text: str) -> dict:
    """Parse wksst9120.for — fixed-width weekly SST data.
    Returns the most recent week's data."""
    lines = [l for l in text.strip().splitlines() if l.strip()]
    # Skip header lines (first 4 lines)
    data_lines = lines[4:]
    last = data_lines[-1]

    # Fixed-width columns based on NOAA format:
    # Week          Nino1+2     Nino3       Nino34      Nino4
    #               SST  SSTA   SST  SSTA   SST  SSTA   SST  SSTA
    week = last[:12].strip()
    try:
        nino34_ssta = float(last[45:49].strip())
        nino34_sst = float(last[39:45].strip())
        nino12_ssta = float(last[21:25].strip())
        nino3_ssta = float(last[33:37].strip())
        nino4_ssta = float(last[57:61].strip())
    except (ValueError, IndexError):
        # Fallback: split by whitespace
        parts = last.split()
        # Format: week_start SST SSTA SST SSTA SST SSTA SST SSTA
        nino12_ssta = float(parts[2])
        nino3_ssta = float(parts[4])
        nino34_sst = float(parts[5])
        nino34_ssta = float(parts[6])
        nino4_ssta = float(parts[8])
        week = parts[0]

    return {
        "week": week,
        "nino12_ssta": nino12_ssta,
        "nino3_ssta": nino3_ssta,
        "nino34_sst": nino34_sst,
        "nino34_ssta": nino34_ssta,
        "nino4_ssta": nino4_ssta,
    }


def parse_weekly_sst_history(text: str, n: int = 8) -> list[dict]:
    """Parse laatste n weken uit wksst9120.for."""
    lines = [l for l in text.strip().splitlines() if l.strip()]
    data_lines = lines[4:]
    results = []
    for line in data_lines[-n:]:
        parts = line.split()
        if len(parts) < 9:
            continue
        try:
            results.append({
                "week": parts[0],
                "nino34_ssta": float(parts[6]),
            })
        except (ValueError, IndexError):
            continue
    return results


def parse_heat_content(text: str) -> dict:
    """Parse heat_content_index.txt — monthly subsurface heat content."""
    lines = [l for l in text.strip().splitlines() if l.strip()]
    # Skip header lines
    data_lines = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 5:
            try:
                int(parts[0])  # year
                data_lines.append(parts)
            except ValueError:
                continue

    if not data_lines:
        return {}

    last = data_lines[-1]
    months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    month_idx = int(last[1])
    month_name = months[month_idx] if month_idx < len(months) else last[1]

    return {
        "year": int(last[0]),
        "month": month_name,
        "heat_content_130e_80w": float(last[2]),
        "heat_content_160e_80w": float(last[3]),
        "heat_content_180w_100w": float(last[4]),
    }


def parse_trade_winds(text: str, name: str) -> dict:
    """Parse 850mb trade wind index — monthly values by year."""
    lines = [l for l in text.strip().splitlines() if l.strip()]
    data_lines = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 2:
            try:
                yr = int(parts[0])
                if 1900 < yr < 2100:
                    data_lines.append(parts)
            except ValueError:
                continue

    if not data_lines:
        return {}

    last = data_lines[-1]
    year = int(last[0])
    # Find last non-missing value
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    latest_month = None
    latest_value = None
    for i, val in enumerate(last[1:13], start=0):
        try:
            v = float(val)
            if v > -99:  # missing value marker
                latest_month = months[i]
                latest_value = v
        except ValueError:
            continue

    return {
        "year": year,
        "month": latest_month,
        f"{name}_anomaly": latest_value,
    }


def parse_soi(text: str) -> dict:
    """Parse Southern Oscillation Index."""
    lines = [l for l in text.strip().splitlines() if l.strip()]
    data_lines = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 2:
            try:
                yr = int(parts[0])
                if 1900 < yr < 2100:
                    data_lines.append(parts)
            except ValueError:
                continue

    if not data_lines:
        return {}

    last = data_lines[-1]
    year = int(last[0])
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    latest_month = None
    latest_value = None
    for i, val in enumerate(last[1:13], start=0):
        try:
            v = float(val)
            if v > -99:
                latest_month = months[i]
                latest_value = v
        except ValueError:
            continue

    return {
        "year": year,
        "month": latest_month,
        "soi": latest_value,
    }


# ---------------------------------------------------------------------------
# Data opslag
# ---------------------------------------------------------------------------

def append_to_csv(filepath: Path, row: dict):
    """Append een rij aan een CSV-bestand, maak het aan als het niet bestaat."""
    file_exists = filepath.exists()
    with open(filepath, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def read_csv_tail(filepath: Path, n: int = 10) -> list[dict]:
    """Lees de laatste n rijen van een CSV."""
    if not filepath.exists():
        return []
    with open(filepath) as f:
        rows = list(csv.DictReader(f))
    return rows[-n:]


# ---------------------------------------------------------------------------
# Rapport & alerts
# ---------------------------------------------------------------------------

def check_alerts(data: dict, thresholds: dict) -> list[str]:
    alerts = []
    nino34 = data.get("nino34_ssta")
    if nino34 is not None:
        if nino34 >= thresholds["nino34_anomaly_critical"]:
            alerts.append(
                f"🔴 CRITICAL: Niño 3.4 anomalie = {nino34:+.1f}°C "
                f"(drempel: {thresholds['nino34_anomaly_critical']}°C)"
            )
        elif nino34 >= thresholds["nino34_anomaly_warn"]:
            alerts.append(
                f"🟡 WARNING: Niño 3.4 anomalie = {nino34:+.1f}°C "
                f"(drempel: {thresholds['nino34_anomaly_warn']}°C)"
            )

    hc = data.get("heat_content_130e_80w")
    if hc is not None and hc >= thresholds["heat_content_warn"]:
        alerts.append(
            f"🟡 WARNING: Subsurface heat content = {hc:+.2f}°C "
            f"(drempel: {thresholds['heat_content_warn']}°C)"
        )

    return alerts


def trend_arrow(values: list[float]) -> str:
    if len(values) < 2:
        return "—"
    diff = values[-1] - values[-2]
    if diff > 0.1:
        return "↑"
    elif diff < -0.1:
        return "↓"
    return "→"


def generate_report(data: dict, history: list[dict], alerts: list[str]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    nino34_values = [float(h["nino34_ssta"]) for h in history if h.get("nino34_ssta")]
    arrow = trend_arrow(nino34_values)

    lines = [
        "=" * 60,
        f"  EL NIÑO MONITOR — WEEKRAPPORT",
        f"  {now}",
        "=" * 60,
        "",
    ]

    # Alerts
    if alerts:
        lines.append("ALERTS:")
        for a in alerts:
            lines.append(f"  {a}")
        lines.append("")

    # SST data
    lines.append("── Sea Surface Temperature (Niño regio's) ──")
    lines.append(f"  Week:           {data.get('week', '?')}")
    lines.append(f"  Niño 3.4 SSTA:  {data.get('nino34_ssta', '?'):+.1f}°C  {arrow}")
    lines.append(f"  Niño 3.4 SST:   {data.get('nino34_sst', '?'):.1f}°C")
    lines.append(f"  Niño 1+2 SSTA:  {data.get('nino12_ssta', '?'):+.1f}°C")
    lines.append(f"  Niño 3 SSTA:    {data.get('nino3_ssta', '?'):+.1f}°C")
    lines.append(f"  Niño 4 SSTA:    {data.get('nino4_ssta', '?'):+.1f}°C")
    lines.append("")

    # Trend laatste weken
    if nino34_values:
        lines.append("  Trend Niño 3.4 (laatste weken):")
        for h in history[-8:]:
            w = h.get("week", "?")
            v = float(h["nino34_ssta"])
            bar = "█" * int(abs(v) * 10)
            sign = "+" if v >= 0 else ""
            lines.append(f"    {w:>12s}  {sign}{v:.1f}°C  {bar}")
        lines.append("")

    # Heat content
    if data.get("heat_content_130e_80w") is not None:
        lines.append("── Subsurface Heat Content (bovenste 300m) ──")
        lines.append(f"  Periode:        {data.get('hc_month', '?')} {data.get('hc_year', '?')}")
        lines.append(f"  130°E-80°W:     {data['heat_content_130e_80w']:+.2f}°C")
        lines.append(f"  160°E-80°W:     {data.get('heat_content_160e_80w', '?'):+.2f}°C")
        lines.append(f"  180°W-100°W:    {data.get('heat_content_180w_100w', '?'):+.2f}°C")
        lines.append("")

    # Trade winds
    if data.get("cpac_anomaly") is not None:
        lines.append("── Passaatwinden (850mb anomalie) ──")
        lines.append(f"  Centraal Pacific: {data['cpac_anomaly']:+.1f} m/s")
        if data.get("wpac_anomaly") is not None:
            lines.append(f"  West Pacific:     {data['wpac_anomaly']:+.1f} m/s")
        lines.append(f"  (negatief = verzwakking → bevordert El Niño)")
        lines.append("")

    # SOI
    if data.get("soi") is not None:
        lines.append("── Southern Oscillation Index ──")
        lines.append(f"  SOI:            {data['soi']:+.1f}")
        lines.append(f"  (negatief = El Niño patroon)")
        lines.append("")

    # Context
    lines.append("── Context (artikel Gloninger) ──")
    lines.append("  Drempel El Niño:        Niño 3.4 ≥ +0.5°C (5 periodes)")
    lines.append("  Super El Niño (1997):    +2.3°C anomalie")
    lines.append("  Super El Niño (2015):    +2.3°C anomalie")
    lines.append("  Voorspelling 2026:      ~+2.5°C anomalie")
    lines.append("  Huidige baseline:        +1.4-1.5°C boven pre-industrieel")
    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run():
    cfg = load_config()
    sources = cfg["sources"]
    thresholds = cfg["alert_thresholds"]
    data_dir = cfg["data_dir"]
    reports_dir = cfg["reports_dir"]

    print("El Niño Monitor — data ophalen...")
    combined = {}
    fetch_date = datetime.now().strftime("%Y-%m-%d")

    # 1. Weekly SST
    try:
        print("  → Weekly SST (Niño 3.4)...")
        text = fetch_text(sources["weekly_sst"])
        sst = parse_weekly_sst(text)
        history = parse_weekly_sst_history(text)
        combined.update(sst)
        row = {"date": fetch_date, **sst}
        append_to_csv(data_dir / "weekly_sst.csv", row)
        print(f"    Niño 3.4 SSTA: {sst['nino34_ssta']:+.1f}°C")
    except Exception as e:
        print(f"    FOUT: {e}")
        history = read_csv_tail(data_dir / "weekly_sst.csv", 8)

    # 2. Heat content
    try:
        print("  → Subsurface heat content...")
        text = fetch_text(sources["heat_content"])
        hc = parse_heat_content(text)
        combined.update(hc)
        combined["hc_year"] = hc.get("year")
        combined["hc_month"] = hc.get("month")
        row = {"date": fetch_date, **hc}
        append_to_csv(data_dir / "heat_content.csv", row)
        print(f"    Heat content (130E-80W): {hc['heat_content_130e_80w']:+.2f}°C")
    except Exception as e:
        print(f"    FOUT: {e}")

    # 3. Trade winds
    for key, name in [("trade_winds_cpac", "cpac"), ("trade_winds_wpac", "wpac")]:
        try:
            print(f"  → Trade winds ({name})...")
            text = fetch_text(sources[key])
            tw = parse_trade_winds(text, name)
            combined.update(tw)
            row = {"date": fetch_date, **tw}
            append_to_csv(data_dir / f"trade_winds_{name}.csv", row)
            val = tw.get(f"{name}_anomaly")
            if val is not None:
                print(f"    {name.upper()} anomaly: {val:+.1f} m/s")
        except Exception as e:
            print(f"    FOUT: {e}")

    # 4. SOI
    try:
        print("  → Southern Oscillation Index...")
        text = fetch_text(sources["soi"])
        soi = parse_soi(text)
        combined.update(soi)
        row = {"date": fetch_date, **soi}
        append_to_csv(data_dir / "soi.csv", row)
        if soi.get("soi") is not None:
            print(f"    SOI: {soi['soi']:+.1f}")
    except Exception as e:
        print(f"    FOUT: {e}")

    # Alerts
    alerts = check_alerts(combined, thresholds)

    # Rapport
    report = generate_report(combined, history, alerts)
    print("\n" + report)

    # Opslaan
    report_file = reports_dir / f"rapport_{fetch_date}.txt"
    with open(report_file, "w") as f:
        f.write(report)
    print(f"\nRapport opgeslagen: {report_file}")

    # Return exit code 1 als er critical alerts zijn
    if any("CRITICAL" in a for a in alerts):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run())
