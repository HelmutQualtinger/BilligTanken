#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_bavaria_prices.py – Diesel- und Benzinpreise aller Tankstellen in Bayern

Quelle: Tankerkönig API (creativecommons.tankerkoenig.de)
         Offizielle MTS-K Daten der Bundesnetzagentur

Verwendung:
    export TANKERKOENIG_API_KEY="your-key-here"
    python3 fetch_bavaria_prices.py [--out-csv prices.csv] [--out-json prices.json]

Ausgabe:
    - CSV-Datei mit allen Stationen (id, name, brand, street, city, zip,
      lat, lon, diesel, e5, e10, is_open)
    - JSON-Datei (gleiche Daten)
    - Zusammenfassung auf stdout

API-Einschränkungen:
    - Maximal 25 km Radius pro Anfrage
    - Kein dedizierter "ganz Bayern"-Endpunkt
    → Lösung: Gleichmäßiges Raster über Bayern, Duplikate per station-ID entfernt
"""

import os
import sys
import csv
import json
import time
import argparse
import requests
from datetime import datetime

# ── Bayerische Bounding-Box ────────────────────────────────────────────────────
# Quelle: Geodaten Bayern
BAY_LAT_MIN = 47.27   # Berchtesgaden / südlichster Punkt
BAY_LAT_MAX = 50.57   # Hof / nördlichster Punkt
BAY_LON_MIN =  9.90   # Lindau / westlichster Punkt
BAY_LON_MAX = 13.84   # Passau / östlichster Punkt

# ── Raster-Parameter ───────────────────────────────────────────────────────────
# API-Maximum: 25 km. Rasterabstand 35 km → ausreichend Überlappung.
SEARCH_RADIUS_KM = 25
GRID_STEP_LAT    = 0.31   # ~34 km pro Schritt
GRID_STEP_LON    = 0.46   # ~33 km pro Schritt bei Breitengrad 49°

# ── API ────────────────────────────────────────────────────────────────────────
API_URL = "https://creativecommons.tankerkoenig.de/json/list.php"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BilligTanken/1.0)"}

# Zwischen den Anfragen warten (API Fair-Use: kein offizieller Wert, 2s ist konservativ)
REQUEST_DELAY_S = 2.0


def build_grid() -> list[tuple[float, float]]:
    """Erstellt ein gleichmäßiges Raster über Bayern."""
    points = []
    lat = BAY_LAT_MIN
    while lat <= BAY_LAT_MAX + GRID_STEP_LAT * 0.5:
        lon = BAY_LON_MIN
        while lon <= BAY_LON_MAX + GRID_STEP_LON * 0.5:
            points.append((round(lat, 4), round(lon, 4)))
            lon += GRID_STEP_LON
        lat += GRID_STEP_LAT
    return points


def in_bavaria(lat: float, lon: float) -> bool:
    """Grobe Bounding-Box-Prüfung (Randstationen aus Nachbarländern entfernen)."""
    return BAY_LAT_MIN <= lat <= BAY_LAT_MAX and BAY_LON_MIN <= lon <= BAY_LON_MAX


def fetch_all_stations(api_key: str) -> list[dict]:
    """
    Durchläuft alle Rasterpunkte und sammelt deduplizierte Stationen.
    Gibt eine Liste von Rohdaten-Dicts zurück (Tankerkönig-Format).
    """
    grid = build_grid()
    print(f"Raster: {len(grid)} Abfragepunkte über Bayern (Radius je {SEARCH_RADIUS_KM} km)")
    print(f"Geschätzte Dauer: ~{len(grid) * REQUEST_DELAY_S / 60:.1f} Minuten\n")

    seen_ids: set[str] = set()
    all_stations: list[dict] = []
    errors = 0

    for i, (lat, lon) in enumerate(grid, 1):
        try:
            resp = requests.get(
                API_URL,
                params={
                    "lat":    lat,
                    "lng":    lon,
                    "rad":    SEARCH_RADIUS_KM,
                    "sort":   "dist",
                    "type":   "all",
                    "apikey": api_key,
                },
                headers=HEADERS,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            if not data.get("ok"):
                msg = data.get("message", "unbekannt")
                print(f"  [{i:3d}/{len(grid)}] ({lat}, {lon}) – API-Fehler: {msg}", file=sys.stderr)
                errors += 1
            else:
                batch = data.get("stations", [])
                new = [s for s in batch if s.get("id") not in seen_ids]
                seen_ids.update(s["id"] for s in new if s.get("id"))
                all_stations.extend(new)
                print(f"  [{i:3d}/{len(grid)}] ({lat:.2f}, {lon:.2f}) "
                      f"→ {len(batch):3d} Stationen, {len(new):3d} neu "
                      f"(gesamt: {len(all_stations)})")

        except requests.RequestException as e:
            print(f"  [{i:3d}/{len(grid)}] ({lat}, {lon}) – Netzwerkfehler: {e}", file=sys.stderr)
            errors += 1

        if i < len(grid):
            time.sleep(REQUEST_DELAY_S)

    print(f"\nAbfragen fertig. Fehler: {errors}/{len(grid)}")
    return all_stations


def normalize_stations(raw: list[dict]) -> list[dict]:
    """
    Bereinigt und normalisiert die Rohdaten.
    Behält nur Stationen innerhalb der bayerischen Bounding-Box.
    """
    result = []
    for s in raw:
        lat = s.get("lat")
        lon = s.get("lng")
        if lat is None or lon is None:
            continue
        if not in_bavaria(lat, lon):
            continue

        diesel = s.get("diesel")
        e5     = s.get("e5")
        e10    = s.get("e10")

        # Mindestens ein gültiger Preis nötig
        if not any([diesel, e5, e10]):
            continue

        result.append({
            "id":      s.get("id", ""),
            "name":    (s.get("brand") or s.get("name") or "–").strip(),
            "brand":   (s.get("brand") or "").strip(),
            "street":  f"{s.get('street', '')} {s.get('houseNumber', '')}".strip(),
            "city":    (s.get("place") or "").strip(),
            "zip":     str(s.get("postCode") or ""),
            "lat":     lat,
            "lon":     lon,
            "diesel":  round(float(diesel), 3) if diesel else None,
            "e5":      round(float(e5), 3)     if e5     else None,
            "e10":     round(float(e10), 3)    if e10    else None,
            "is_open": s.get("isOpen"),
        })

    return result


def write_csv(stations: list[dict], path: str) -> None:
    fieldnames = ["id", "name", "brand", "street", "city", "zip",
                  "lat", "lon", "diesel", "e5", "e10", "is_open"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(stations)
    print(f"CSV gespeichert: {path}")


def write_json(stations: list[dict], path: str, fetched_at: str) -> None:
    payload = {
        "fetched_at": fetched_at,
        "count":      len(stations),
        "stations":   stations,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"JSON gespeichert: {path}")


def print_summary(stations: list[dict]) -> None:
    open_s   = [s for s in stations if s["is_open"] is not False]
    has_die  = [s for s in open_s if s["diesel"] is not None]
    has_e5   = [s for s in open_s if s["e5"]     is not None]
    has_e10  = [s for s in open_s if s["e10"]    is not None]

    print("\n" + "=" * 60)
    print(f"  ERGEBNIS – Bayern, Stand {datetime.now().strftime('%d.%m.%Y %H:%M Uhr')}")
    print("=" * 60)
    print(f"  Stationen gesamt:        {len(stations):5d}")
    print(f"  Davon geöffnet:          {len(open_s):5d}")
    print(f"  Mit Diesel-Preis:        {len(has_die):5d}")
    print(f"  Mit Super 95 (E5)-Preis: {len(has_e5):5d}")
    print(f"  Mit E10-Preis:           {len(has_e10):5d}")

    for label, lst, field in [("Diesel", has_die, "diesel"),
                               ("Super 95 (E5)", has_e5, "e5"),
                               ("E10", has_e10, "e10")]:
        if not lst:
            continue
        prices = sorted(s[field] for s in lst)
        cheapest = sorted(lst, key=lambda s: s[field])[:3]
        print(f"\n  {label}:")
        print(f"    Durchschnitt: {sum(prices)/len(prices):.3f} €/l")
        print(f"    Minimum:      {prices[0]:.3f} €/l")
        print(f"    Maximum:      {prices[-1]:.3f} €/l")
        print(f"    Top 3 günstig:")
        for s in cheapest:
            print(f"      {s[field]:.3f} €  {s['name']:<20} {s['city']}")

    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diesel- und Benzinpreise aller Tankstellen in Bayern abrufen."
    )
    parser.add_argument(
        "--out-csv",
        default="bayern_preise.csv",
        metavar="DATEI",
        help="Ausgabe-CSV (Standard: bayern_preise.csv)",
    )
    parser.add_argument(
        "--out-json",
        default="bayern_preise.json",
        metavar="DATEI",
        help="Ausgabe-JSON (Standard: bayern_preise.json)",
    )
    parser.add_argument(
        "--only-open",
        action="store_true",
        help="Nur geöffnete Stationen ausgeben",
    )
    args = parser.parse_args()

    api_key = os.environ.get("TANKERKOENIG_API_KEY")
    if not api_key:
        print("FEHLER: Umgebungsvariable TANKERKOENIG_API_KEY nicht gesetzt.", file=sys.stderr)
        print("  export TANKERKOENIG_API_KEY='dein-api-schluessel'", file=sys.stderr)
        sys.exit(1)

    fetched_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    print(f"BilligTanken – Bayern-Preisabruf gestartet ({fetched_at})\n")

    raw      = fetch_all_stations(api_key)
    stations = normalize_stations(raw)

    if args.only_open:
        stations = [s for s in stations if s["is_open"] is not False]

    stations.sort(key=lambda s: (s["diesel"] or 9999, s["city"]))

    print_summary(stations)

    write_csv(stations,  args.out_csv)
    write_json(stations, args.out_json, fetched_at)


if __name__ == "__main__":
    main()