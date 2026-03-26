#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SchärdingTanken – Günstigste Tankstellen rund um Schärding (Innviertel, OÖ)
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
OUTPUT     = _web_root / "schaerding-tanken.html"
OUTPUT_NEW = _web_root / "schaerding-tanken_new.html"

# Referenzpunkt Schärding (48°27'16"N 13°26'15"E)
HOME_LAT  = 48.4545
HOME_LON  = 13.4375
HOME_NAME = "Schärding"

# 0.12°×0.20°-Raster über Schärding / Innviertel + Umland (OÖ, Teile von Bayern)
LAT_MIN, LAT_MAX = 48.10, 48.75
LON_MIN, LON_MAX = 12.80, 14.10

QUERY_POINTS = [
    (round(lat, 3), round(lon, 3))
    for lat in [48.10 + i * 0.12 for i in range(int((48.75 - 48.10) / 0.12) + 1)]
    for lon in [12.80 + j * 0.20 for j in range(int((14.10 - 12.80) / 0.20) + 1)]
]

# ── Region-spezifische HTML-Strings ───────────────────────────────────────────
TITLE           = "SchärdingTanken – Günstigste Tankstellen"
META_DESCRIPTION = "Aktuelle Spritpreise rund um Schärding und das Innviertel. Günstigste Tankstellen in Oberösterreich im Preisvergleich."
META_KEYWORDS   = "Tanken, Benzinpreise, Schärding, Innviertel, Oberösterreich, E5, Super 95, Diesel, Ried, Braunau, billig tanken"
OG_TITLE        = "SchärdingTanken – Günstigste Tankstellen"
OG_DESCRIPTION  = "Günstigste Tankstellen rund um Schärding. Echtzeit-Preise von E-Control."
H1              = "⛽ SchärdingTanken"
SUB_SUP         = "Großraum Schärding / Innviertel"
SUB_DIE         = "Großraum Schärding / Innviertel"

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
