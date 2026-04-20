#!/bin/bash
# Installatiescript voor El Niño Monitor op Raspberry Pi
# Gebruik: bash install.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "=== El Niño Monitor — Installatie ==="

# Python venv aanmaken
echo "→ Virtual environment aanmaken..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Dependencies installeren
echo "→ Dependencies installeren..."
pip install -r "$SCRIPT_DIR/requirements.txt"

# Data directories aanmaken
mkdir -p "$SCRIPT_DIR/data" "$SCRIPT_DIR/reports"

# Cron job instellen (elke zondag 08:00)
CRON_CMD="0 8 * * 0 cd $SCRIPT_DIR && $VENV_DIR/bin/python nino_monitor.py >> $SCRIPT_DIR/data/cron.log 2>&1"

# Check of cron job al bestaat
if crontab -l 2>/dev/null | grep -q "nino_monitor.py"; then
    echo "→ Cron job bestaat al, overslaan."
else
    echo "→ Wekelijkse cron job instellen (zondag 08:00)..."
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "  Toegevoegd: $CRON_CMD"
fi

# Systemd service voor API server
echo ""
echo "→ API server service installeren..."
if [ -f /etc/systemd/system/nino-server.service ]; then
    echo "  Service bestaat al, overslaan."
else
    # Pas paden aan voor huidige installatie
    sed "s|/home/pi/nino|$SCRIPT_DIR|g" "$SCRIPT_DIR/nino-server.service" | \
        sed "s|User=pi|User=$(whoami)|g" | \
        sudo tee /etc/systemd/system/nino-server.service > /dev/null
    sudo systemctl daemon-reload
    sudo systemctl enable nino-server
    sudo systemctl start nino-server
    echo "  Service gestart op poort 8099"
fi

# Eerste data ophalen
echo ""
echo "→ Eerste data ophalen..."
"$VENV_DIR/bin/python" "$SCRIPT_DIR/nino_monitor.py"

echo ""
echo "=== Installatie compleet ==="
echo ""
echo "Handmatig draaien:  $VENV_DIR/bin/python $SCRIPT_DIR/nino_monitor.py"
echo "Cron schema:        Elke zondag om 08:00"
echo "API server:         http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost'):8099/api/state"
echo "Data opslag:        $SCRIPT_DIR/data/"
echo "Rapporten:          $SCRIPT_DIR/reports/"
echo ""
echo "Home Assistant:     Kopieer de REST config uit homeassistant.yaml"
echo "                    naar je HA configuration.yaml"
