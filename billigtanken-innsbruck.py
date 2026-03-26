#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
InnsbruckTanken – Günstigste Tankstellen rund um Innsbruck und das Inntal
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
OUTPUT     = _web_root / "innsbruck-tanken.html"
OUTPUT_NEW = _web_root / "innsbruck-tanken_new.html"

# Referenzpunkt Innsbruck Hauptbahnhof (47°15'36"N 11°24'01"E)
HOME_LAT  = 47.2600
HOME_LON  = 11.4005
HOME_NAME = "Innsbruck Hbf"

# 0.12°×0.20°-Raster über Inntal-Korridor + Umland (Tirol, Vorarlberg Ost, Salzburg West)
LAT_MIN, LAT_MAX = 46.90, 47.70
LON_MIN, LON_MAX = 10.20, 13.00

QUERY_POINTS = [
    (round(lat, 3), round(lon, 3))
    for lat in [46.90 + i * 0.12 for i in range(int((47.70 - 46.90) / 0.12) + 1)]
    for lon in [10.20 + j * 0.20 for j in range(int((13.00 - 10.20) / 0.20) + 1)]
]

# ── Region-spezifische HTML-Strings ───────────────────────────────────────────
TITLE           = "InnsbruckTanken – Günstigste Tankstellen"
META_DESCRIPTION = "Aktuelle Spritpreise rund um Innsbruck und das Inntal. Günstigste Tankstellen in Tirol im Preisvergleich."
META_KEYWORDS   = "Tanken, Benzinpreise, Innsbruck, Tirol, Inntal, E5, Super 95, Diesel, Hall, Wattens, Schwaz, billig tanken"
OG_TITLE        = "InnsbruckTanken – Günstigste Tankstellen"
OG_DESCRIPTION  = "Günstigste Tankstellen rund um Innsbruck. Echtzeit-Preise von E-Control."
H1              = "⛽ InnsbruckTanken"
SUB_SUP         = "Großraum Innsbruck / Inntal"
SUB_DIE         = "Großraum Innsbruck / Inntal"

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
