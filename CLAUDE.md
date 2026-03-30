# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Build and start Docker container
docker compose up -d --build

# View live logs (including cron runs)
docker compose logs -f

# Rebuild after code changes (ALWAYS do this after editing any project file)
docker compose up -d --build

# Stop container
docker compose down
```

## Architecture

Shared library (`billigtanken_lib.py`) + four regional scripts, each generating its own HTML page.

**Regional scripts:**
| Script | Output file | Cron |
|--------|-------------|------|
| `billigtanken-alterlaa.py` | `alterlaa-tanken.html` | `:00` |
| `billigtanken-innsbruck.py` | `innsbruck-tanken.html` | `:15` |
| `billigtanken-vorarlberg.py` | `index-vorarlberg.html` | `:30` |
| `billigtanken-schaerding.py` | `schaerding-tanken.html` | `:45` |

**Data flow (per region):**
1. Queries the Austrian E-Control API (`api.e-control.at/sprit/1.0/`) at multiple coordinate points (API returns max 10 stations per request)
2. Deduplicates by station ID, filters to bounding box, keeps only stations with reported prices
3. Sorts by price ASC, then by Luftlinie (haversine distance) from reference point as tiebreaker
4. Renders a dark-mode HTML page with Leaflet.js map and writes atomically: `*_new.html` → rename → `*.html`

**Key configuration constants** (top of each regional script):
- `TOP_N` – number of cards to show
- `QUERY_POINTS` – list of (lat, lon) tuples for API calls
- `HOME_LAT/HOME_LON/HOME_NAME` – reference point for distance calculation
- `WEB_ROOT` – env var (default `.`), set to `/var/www/localhost/htdocs` in Docker

**Output path** is controlled by `WEB_ROOT` environment variable. Atomic swap prevents serving a half-written file.

**Docker setup:** Single Alpine container (~88 MB) with python3 + py3-requests + apache2 + dcron. Each script runs once at startup and then on its cron schedule. Apache serves static HTML on port 80. Logs at `/var/log/billigtanken.log`.

## Workflow

After **every** code change:
1. `docker compose up -d --build` – rebuild and restart the container
2. `git add` + `git commit` + `git push` – commit and push to GitHub (`HelmutQualtinger/BilligTanken`)

## Design Decisions

- **Map tiles**: Use CARTO Voyager (light/colorful) tiles — dark tiles were rejected by user
- **Price ranking**: All stations tied at the same price get the same medal rank (all 🥇, all 🥈, etc.); distance from reference point is the tiebreaker within each price tier
- **Top 6 panel**: Shows the 6 cheapest stations among the 20 closest (by home_dist). Ranks in the mini-cards match the main grid card IDs for correct scroll-to behavior.
- **CSS theme variables**: Place default CSS variables (e.g. `--link-color`) inside `:root, [data-theme="dark"]` — never in a standalone `:root` block that appears after `[data-theme="light"]`, as equal specificity means last declaration wins and will override the light theme values
- **brand_initial fallback**: Single-character station names duplicate the letter rather than crash

**E-Control API notes:**
- Only `SUP` (Super 95) and `DIE` (Diesel) are valid fuel types – E10 is not sold in Austria
- Austria has a regulated daily maximum price; most brand stations charge exactly this price, only Diskont/Disk/Avanti/JET/BayWa stations typically undercut it
- ~30% of stations in the area don't report prices to the system (Shell, some ENI) and are excluded

**Frontend (embedded in generated HTML):**
- Leaflet.js + CARTO Voyager tiles for the map
- Browser Geolocation API: if granted, recalculates all distances and route links from actual GPS position; falls back to `HOME_LAT/HOME_LON`
- Route buttons open Google Maps Directions with origin set to user's location
- Brand logos via `https://www.google.com/s2/favicons?domain={domain}&sz=128` with initials fallback on error

## SEO & Social Media

Enhanced meta tags and structured data have been added for better search engine indexing and social media sharing.

**Key features:**
- Open Graph tags (og:title, og:description, og:image)
- Twitter Card support (summary_large_image)
- JSON-LD schema (LocalBusiness)
- Favicon and manifest references
- Mobile app installation support

**To enable social media preview with absolute URLs**, pass `base_url` to `generate_html()`:
```python
html = generate_html(
    ...,
    base_url="https://billigtanken.at"
)
```

**Documentation:**
- `SEO_IMPROVEMENTS.md` – Complete SEO guide
- `GENERATE_ASSETS.md` – How to create favicons and preview images
- `generate_seo_assets.py` – Auto-generate required image assets
- `site.webmanifest` – Web app manifest (customize as needed)
