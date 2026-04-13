#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFB-Tanken – Günstigste Tankstellen Großraum München
Quelle: Tankerkönig API (creativecommons.tankerkoenig.de)
         Offizielle MTS-K Daten der Bundesnetzagentur
"""

import sys
import os
import requests
import math
import json
from datetime import datetime
from pathlib import Path

from billigtanken_lib import (
    generate_html, write_html, print_summary,
    haversine,
)

# ── Konfiguration ─────────────────────────────────────────────────────────────
TOP_N      = 100
_web_root  = Path(os.environ.get("WEB_ROOT", "."))
OUTPUT     = _web_root / "ffb-tanken.html"
OUTPUT_NEW = _web_root / "ffb-tanken_new.html"

# Referenzpunkt: Fürstenfeldbruck Bahnhof (Tiebreaker / Kartenzentrierung)
HOME_LAT  = 48.1785
HOME_LON  = 11.2349
HOME_NAME = "Fürstenfeldbruck Bahnhof"

# Suchradius in km (max 25 bei Tankerkönig)
SEARCH_RADIUS_KM = 25

# 4×4-Raster über Großraum München (je ~20 km Abstand, 25 km Radius → volle Überlappung)
# Abdeckung: Fürstenfeldbruck–Ebersberg (W–O) × Wolfratshausen–Freising (S–N)
QUERY_POINTS = [
    #          lat      lon       Orientierung
    (47.92,  11.22),  # SW – Gilching / Starnberg West
    (47.92,  11.47),  # S  – Gauting / Würmtal
    (47.92,  11.72),  # S  – München Süd / Grünwald
    (47.92,  11.97),  # SO – Sauerlach / Brunnthal

    (48.10,  11.22),  # W  – Fürstenfeldbruck
    (48.10,  11.47),  # MW – Pasing / Dachau Süd
    (48.10,  11.72),  # M  – München Zentrum
    (48.10,  11.97),  # MO – München Ost / Haar

    (48.28,  11.22),  # NW – Dachau / Karlsfeld
    (48.28,  11.47),  # N  – Unterschleißheim / Oberschleißheim
    (48.28,  11.72),  # N  – Garching / Ismaning
    (48.28,  11.97),  # NO – Markt Schwaben / Erding West

    (48.46,  11.22),  # wN – Petershausen / Odelzhausen
    (48.46,  11.47),  # N  – Freising West
    (48.46,  11.72),  # N  – Freising / Flughafen MUC
    (48.46,  11.97),  # NO – Erding / Dorfen
]

# Tankerkönig API-Key (aus .env / Umgebungsvariable)
API_KEY = os.environ.get("TANKERKOENIG_API_KEY")
if not API_KEY:
    print("FEHLER: TANKERKOENIG_API_KEY nicht gesetzt.", file=sys.stderr)
    sys.exit(1)

API_URL = "https://creativecommons.tankerkoenig.de/json/list.php"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BilligTanken/1.0)"}

# ── Daten holen ───────────────────────────────────────────────────────────────
_raw_cache: list[dict] | None = None

def fetch_all_stations() -> list[dict]:
    """Holt alle Tankstellen via Raster (5 Punkte, type=all) und dedupliziert per ID."""
    global _raw_cache
    if _raw_cache is not None:
        return _raw_cache
    print(f"⛽  Lade Tankstellendaten (Großraum München, {len(QUERY_POINTS)} Abfragepunkte) …")
    seen_ids: set = set()
    combined: list[dict] = []
    for lat, lon in QUERY_POINTS:
        try:
            resp = requests.get(API_URL, params={
                "lat":    lat,
                "lng":    lon,
                "rad":    SEARCH_RADIUS_KM,
                "sort":   "dist",
                "type":   "all",
                "apikey": API_KEY,
            }, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                print(f"   WARNUNG: ({lat}, {lon}) API-Fehler: {data.get('message')}", file=sys.stderr)
            else:
                batch = data.get("stations", [])
                new = [s for s in batch if s.get("id") not in seen_ids]
                seen_ids.update(s["id"] for s in new if s.get("id"))
                combined.extend(new)
                print(f"   ({lat}, {lon}) → {len(batch)} Stationen, {len(new)} neu")
        except Exception as e:
            print(f"   FEHLER: ({lat}, {lon}): {e}", file=sys.stderr)
    print(f"   → {len(combined)} eindeutige Stationen gesamt")
    _raw_cache = combined
    return _raw_cache

def process_de(fuel_type: str) -> list[dict]:
    tk_type = {"E5": "e5", "E10": "e10", "DIE": "diesel"}.get(fuel_type, fuel_type.lower())
    stations = fetch_all_stations()
    result = []
    for s in stations:
        if s.get("isOpen") is False:
            continue
        price = s.get(tk_type)
        if not price or price <= 0:
            continue
        lat = s.get("lat")
        lon = s.get("lng")
        home_dist = round(haversine(HOME_LAT, HOME_LON, lat, lon), 1) if lat and lon else None
        name = s.get("brand") or s.get("name") or "–"
        street = f"{s.get('street', '')} {s.get('houseNumber', '')}".strip()
        result.append({
            "name":      name,
            "street":    street,
            "city":      s.get("place", ""),
            "zip":       str(s.get("postCode", "")),
            "price":     float(price),
            "dist_km":   round(float(s["dist"]), 1) if s.get("dist") else None,
            "home_dist": home_dist,
            "lat":       lat,
            "lon":       lon,
            "open":      s.get("isOpen"),
        })
    result.sort(key=lambda x: (x["price"], x["home_dist"] or 999))
    return result[:TOP_N]

# ── Region-spezifische HTML-Strings ───────────────────────────────────────────
TITLE            = "München-Tanken – Günstigste Tankstellen"
META_DESCRIPTION = ("Aktuelle Spritpreise im Großraum München. "
                    "Günstigste Tankstellen in München, FFB, Dachau, Erding, Ebersberg und Umgebung.")
META_KEYWORDS    = ("Tanken, Benzinpreise, München, Fürstenfeldbruck, FFB, Dachau, Erding, "
                    "Ebersberg, Freising, Bayern, Super 95, E5, Diesel, billig tanken, günstig tanken")
OG_TITLE         = "München-Tanken – Günstigste Tankstellen"
OG_DESCRIPTION   = "Günstigste Tankstellen im Großraum München. Echtzeit-Preise von Tankerkönig."
H1               = "⛽ München-Tanken"
SUB_E5           = "Großraum München (FFB · Dachau · Freising · Erding · Ebersberg)"
SUB_DIE          = "Großraum München (FFB · Dachau · Freising · Erding · Ebersberg)"

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    fetched_at = datetime.now().strftime("%d.%m.%Y %H:%M Uhr")

    stations_e5  = process_de("E5")
    stations_e10 = process_de("E10")
    stations_die = process_de("DIE")

    if not stations_e5 and not stations_die:
        print("Keine Tankstellen mit Preisdaten gefunden.", file=sys.stderr)
        sys.exit(1)

    print_summary(stations_e5, stations_die)

    html = generate_html(
        stations_e5, stations_die, fetched_at,
        HOME_LAT, HOME_LON, HOME_NAME,
        TITLE, META_DESCRIPTION, META_KEYWORDS,
        OG_TITLE, OG_DESCRIPTION,
        H1, SUB_E5, SUB_DIE,
        stations_e10=stations_e10,
        sub_e10=SUB_E5,
    )
    write_html(html, OUTPUT, OUTPUT_NEW)
