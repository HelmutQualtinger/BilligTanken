#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AlterlaaTanken – Günstigste Tankstellen rund um die Hochhäuser Alt-Erlaa in Wien
Quelle: E-Control Austria API (spritpreisrechner.at)
"""

import sys
import os
from datetime import datetime
from pathlib import Path

from billigtanken_lib import (
    fetch_stations, process, generate_html, write_html, print_summary
)

# ── Konfiguration ─────────────────────────────────────────────────────────────
TOP_N      = 250
_web_root  = Path(os.environ.get("WEB_ROOT", "."))
OUTPUT     = _web_root / "alterlaa-tanken.html"
OUTPUT_NEW = _web_root / "alterlaa-tanken_new.html"

# Referenzpunkt Alt-Erlaa Hochhäuser, Wien 23 (48°09'06"N 16°18'43"E)
HOME_LAT  = 48.1517
HOME_LON  = 16.3119
HOME_NAME = "Alt-Erlaa Wien"

# 0.10°-Raster über Großraum Wien + NÖ-Umgebung → ~100 Punkte → genug für 250 eindeutige Stationen
LAT_MIN, LAT_MAX = 47.65, 48.50
LON_MIN, LON_MAX = 15.70, 17.10

QUERY_POINTS = [
    (round(lat, 3), round(lon, 3))
    for lat in [47.65 + i * 0.10 for i in range(int((48.50 - 47.65) / 0.10) + 1)]
    for lon in [15.70 + j * 0.14 for j in range(int((17.10 - 15.70) / 0.14) + 1)]
]

# ── Region-spezifische HTML-Strings ───────────────────────────────────────────
TITLE           = "AlterlaaTanken Wien – Günstigste Tankstellen"
META_DESCRIPTION = "Aktuelle Spritpreise rund um Alt-Erlaa in Wien. Günstigste Tankstellen im Umkreis der Hochhäuser Alterlaa im Preisvergleich."
META_KEYWORDS   = "Tanken, Benzinpreise, Wien, Alterlaa, Alt-Erlaa, E5, Super 95, Diesel, Liesing, Meidling, Favoriten, billig tanken"
OG_TITLE        = "AlterlaaTanken Wien – Günstigste Tankstellen"
OG_DESCRIPTION  = "Günstigste Tankstellen rund um Alt-Erlaa Wien. Echtzeit-Preise von E-Control."
H1              = "⛽ AlterlaaTanken Wien"
SUB_SUP         = "Umkreis Alt-Erlaa Wien"
SUB_DIE         = "Umkreis Alt-Erlaa Wien"

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    fetched_at = datetime.now().strftime("%d.%m.%Y %H:%M Uhr")

    data_sup     = fetch_stations("SUP", QUERY_POINTS)
    stations_sup = process(data_sup, "SUP", HOME_LAT, HOME_LON, LAT_MIN, LAT_MAX, LON_MIN, LON_MAX, TOP_N)
    data_die     = fetch_stations("DIE", QUERY_POINTS)
    stations_die = process(data_die, "DIE", HOME_LAT, HOME_LON, LAT_MIN, LAT_MAX, LON_MIN, LON_MAX, TOP_N)

    if not stations_sup and not stations_die:
        print("Keine Tankstellen mit Preisdaten gefunden.", file=sys.stderr)
        sys.exit(1)

    print_summary(stations_sup, stations_die)

    html = generate_html(
        stations_sup, stations_die, fetched_at,
        HOME_LAT, HOME_LON, HOME_NAME,
        TITLE, META_DESCRIPTION, META_KEYWORDS,
        OG_TITLE, OG_DESCRIPTION,
        H1, SUB_SUP, SUB_DIE,
    )
    write_html(html, OUTPUT, OUTPUT_NEW)
