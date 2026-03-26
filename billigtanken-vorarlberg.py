#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BilligTanken – Günstigste E5 Tankstellen in Vorarlberg zwischen Bregenz und Feldkirch
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
TOP_N      = 80
_web_root  = Path(os.environ.get("WEB_ROOT", "."))
OUTPUT     = _web_root / "index-vorarlberg.html"
OUTPUT_NEW = _web_root / "index-vorarlberg_new.html"

# Referenzpunkt Rebstein SG, Schweiz (47°23'53"N 9°34'56"E)
HOME_LAT  = 47.3983
HOME_LON  =  9.5824
HOME_NAME = "Rebstein CH"

QUERY_POINTS = [
    (47.505, 9.747),   # Bregenz
    (47.474, 9.751),   # Wolfurt
    (47.478, 9.664),   # Fußach
    (47.460, 9.730),   # Lauterach / Hard
    (47.427, 9.661),   # Lustenau
    (47.413, 9.743),   # Dornbirn
    (47.367, 9.697),   # Hohenems
    (47.370, 9.680),   # Götzis
    (47.311, 9.646),   # Klaus
    (47.300, 9.610),   # Weiler
    (47.274, 9.576),   # Meiningen
    (47.271, 9.617),   # Rankweil
    (47.238, 9.596),   # Feldkirch
]

LAT_MIN, LAT_MAX = 47.20, 47.55
LON_MIN, LON_MAX =  9.50,  9.80

# ── Region-spezifische HTML-Strings ───────────────────────────────────────────
TITLE           = "BilligTanken Vorarlberg – E5 Super 95"
META_DESCRIPTION = "Aktuelle Benzinpreise (E5 Super 95) in Vorarlberg. Günstigste Tankstellen zwischen Bregenz und Feldkirch im Preisvergleich."
META_KEYWORDS   = "Tanken, Benzinpreise, Vorarlberg, E5, Super 95, Bregenz, Dornbirn, Feldkirch, Lustenau, billig tanken"
OG_TITLE        = "BilligTanken Vorarlberg – E5 Super 95"
OG_DESCRIPTION  = "Günstigste Tankstellen in Vorarlberg. Echtzeit-Preise von E-Control."
H1              = "⛽ BilligTanken Vorarlberg"
SUB_SUP         = "Korridor Bregenz – Feldkirch"
SUB_DIE         = "Korridor Bregenz – Feldkirch"

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
