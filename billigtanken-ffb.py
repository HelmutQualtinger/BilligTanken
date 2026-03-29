#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFB-Tanken – Günstigste Tankstellen rund um Fürstenfeldbruck
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

# Referenzpunkt: Fürstenfeldbruck Bahnhof
HOME_LAT  = 48.1785
HOME_LON  = 11.2349
HOME_NAME = "Fürstenfeldbruck Bahnhof"

# Suchradius in km (max 25 bei Tankerkönig)
SEARCH_RADIUS_KM = 20

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
    """Holt alle Tankstellen einmalig mit type=all (liefert e5 + diesel in einem Request)."""
    global _raw_cache
    if _raw_cache is not None:
        return _raw_cache
    print(f"⛽  Lade Tankstellendaten (alle) von Tankerkönig API …")
    try:
        resp = requests.get(API_URL, params={
            "lat":    HOME_LAT,
            "lng":    HOME_LON,
            "rad":    SEARCH_RADIUS_KM,
            "sort":   "dist",
            "type":   "all",
            "apikey": API_KEY,
        }, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            print(f"   WARNUNG: API-Fehler: {data.get('message')}", file=sys.stderr)
            _raw_cache = []
        else:
            _raw_cache = data.get("stations", [])
            print(f"   → {len(_raw_cache)} Stationen im Umkreis {SEARCH_RADIUS_KM} km")
    except Exception as e:
        print(f"   FEHLER: {e}", file=sys.stderr)
        _raw_cache = []
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
TITLE            = "FFB-Tanken – Günstigste Tankstellen"
META_DESCRIPTION = ("Aktuelle Spritpreise rund um Fürstenfeldbruck. "
                    "Günstigste Tankstellen im Landkreis FFB und Münchner Westen im Preisvergleich.")
META_KEYWORDS    = ("Tanken, Benzinpreise, Fürstenfeldbruck, FFB, München, Bayern, "
                    "Super 95, E5, Diesel, billig tanken, günstig tanken")
OG_TITLE         = "FFB-Tanken – Günstigste Tankstellen"
OG_DESCRIPTION   = "Günstigste Tankstellen rund um Fürstenfeldbruck. Echtzeit-Preise von Tankerkönig."
H1               = "⛽ FFB-Tanken"
SUB_E5           = "Großraum Fürstenfeldbruck / Münchner Westen"
SUB_DIE          = "Großraum Fürstenfeldbruck / Münchner Westen"

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
