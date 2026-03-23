# ⛽ BilligTanken Vorarlberg

Echtzeit-Übersicht der günstigsten **E5 (Super 95)** Tankstellen im Korridor **Bregenz – Feldkirch**, mit interaktiver Karte, GPS-Standort und Luftlinien-Entfernung.

![BilligTanken Screenshot](screenshots/preview.png)

## Features

- **Top 20 günstigste Stationen** – sortiert nach Preis, bei Gleichstand nach Luftlinie vom Standort
- **Interaktive Leaflet-Karte** – Marker farbcodiert von grün (günstig) → rot (teuer), klickbar
- **GPS-Standort** – Browser-Geolocation aktualisiert Entfernungen und Route-Links live
- **Route-Button** – öffnet Google Maps Directions direkt ab aktuellem Standort
- **Automatische Aktualisierung** – Cron läuft jede volle Stunde, atomarer Datei-Swap (kein Flackern)
- Nur Stationen mit **gemeldeten Preisen** werden angezeigt

## Datenquelle

[E-Control Austria](https://www.spritpreisrechner.at/) – gesetzlich verpflichtende Preistransparenzdatenbank.
In Österreich gilt ein staatlicher **Tageshöchstpreis** (Erhöhungen nur Mo/Mi/Fr um 12 Uhr). Diskont-Ketten (Disk, Avanti, JET) unterbieten ihn regelmäßig.

> **Hinweis:** E10 wird in Österreich nicht verkauft. Das österreichische Äquivalent ist Super 95 (E5).

## Quickstart

```bash
# Lokal (erzeugt index.html im aktuellen Verzeichnis)
pip install requests
python3 billigtanken.py
open index.html

# Docker (empfohlen)
docker compose up -d --build
# → http://localhost:8080
```

## Docker

```bash
docker compose up -d --build   # starten / neu bauen
docker compose logs -f         # live logs
docker compose down            # stoppen
```

| | |
|---|---|
| **Base Image** | `alpine:3.21` |
| **Image-Größe** | ~88 MB |
| **Web-Server** | Apache (httpd) |
| **Aktualisierung** | Cron, jede volle Stunde |
| **Port** | `8080` → Container `80` |

## Konfiguration

Alle Einstellungen am Anfang von `billigtanken.py`:

| Variable | Bedeutung |
|---|---|
| `FUEL_TYPE` | `SUP` (Super 95) oder `DIE` (Diesel) |
| `TOP_N` | Anzahl der angezeigten Kacheln |
| `QUERY_POINTS` | Koordinatenpunkte für die API-Abfrage |
| `HOME_LAT/LON` | Fallback-Referenzpunkt (Standard: Rebstein CH) |
| `WEB_ROOT` | Ausgabeverzeichnis (Env-Variable, Standard: `.`) |
