# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Generate index.html locally (requires internet access to E-Control API)
python3 billigtanken.py

# Build and start Docker container (serves on http://localhost:8080)
docker compose up -d --build

# View live logs (including cron runs)
docker compose logs -f

# Rebuild after code changes (ALWAYS do this after editing any project file)
docker compose up -d --build

# Stop container
docker compose down
```

## Architecture

Single-file Python app (`billigtanken.py`) that fetches fuel price data and generates a self-contained HTML page.

**Data flow:**
1. Queries the Austrian E-Control API (`api.e-control.at/sprit/1.0/`) at 5 coordinate points along the Bregenz–Feldkirch corridor (API returns max 10 stations per request)
2. Deduplicates by station ID, filters to bounding box, keeps only stations with reported prices
3. Sorts by price ASC, then by Luftlinie (haversine distance) from reference point as tiebreaker
4. Renders a dark-mode HTML page with Leaflet.js map and writes atomically: `index_new.html` → rename → `index.html`

**Key configuration constants** (top of `billigtanken.py`):
- `FUEL_TYPE` – API fuel code (`SUP` = Super 95/E5, `DIE` = Diesel)
- `TOP_N` – number of cards to show
- `QUERY_POINTS` – list of (lat, lon) tuples for API calls
- `HOME_LAT/HOME_LON/HOME_NAME` – reference point for distance calculation (currently Rebstein CH)
- `WEB_ROOT` – env var (default `.`), set to `/var/www/localhost/htdocs` in Docker

**Output path** is controlled by `WEB_ROOT` environment variable. Atomic swap prevents serving a half-written file.

**Docker setup:** Single Alpine container (~88 MB) with python3 + py3-requests + apache2 + dcron. Cron triggers the script every full hour (`0 * * * *`). Apache serves the static HTML on port 80 (mapped to 8080 externally). Logs at `/var/log/billigtanken.log` inside the container.

## Workflow

- After every code change: run `docker compose up -d --build` to rebuild and restart the container
- After every code change: commit and push to GitHub (`HelmutQualtinger/BilligTanken`)

## Design Decisions

- **Map tiles**: Use CARTO Voyager (light/colorful) tiles — dark tiles were rejected by user
- **Price ranking**: All stations tied at the same price get the same medal rank (all 🥇, all 🥈, etc.); distance from reference point is the tiebreaker within each price tier

**E-Control API notes:**
- Only `SUP` (Super 95) and `DIE` (Diesel) are valid fuel types – E10 is not sold in Austria
- Austria has a regulated daily maximum price; most brand stations charge exactly this price, only Diskont/Disk/Avanti/JET/BayWa stations typically undercut it
- ~30% of stations in the area don't report prices to the system (Shell, some ENI) and are excluded

**Frontend (embedded in generated HTML):**
- Leaflet.js + CARTO Voyager tiles for the map
- Browser Geolocation API: if granted, recalculates all distances and route links from actual GPS position; falls back to `HOME_LAT/HOME_LON`
- Route buttons open Google Maps Directions with origin set to user's location
- Brand logos via `https://www.google.com/s2/favicons?domain={domain}&sz=128` with initials fallback on error
