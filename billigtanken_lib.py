#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
billigtanken_lib – Gemeinsame Bibliothek für alle BilligTanken-Regionalskripte
Quelle: E-Control Austria API (spritpreisrechner.at)
"""

import requests
import json
import sys
import math
import os
from datetime import datetime
from pathlib import Path

# ── API-Konstanten ─────────────────────────────────────────────────────────────
API_BASE = "https://api.e-control.at/sprit/1.0/search/gas-stations/by-address"
HEADERS  = {"User-Agent": "Mozilla/5.0 (compatible; BilligTanken/1.0)"}

# ── Marken-Farben & Domains ────────────────────────────────────────────────────
BRAND_COLORS = {
    "jet":     "#e30613",
    "avanti":  "#ccff00",
    "disk":    "#005baa",
    "diskont": "#005baa",
    "eni":     "#006db7",
    "omv":     "#012606",
    "shell":   "#c8a800",
    "bp":      "#009a44",
    "esso":    "#003087",
    "avia":    "#e2001a",
    "oil!":    "#005550",
    "baywa":   "#007db5",
    "loacker": "#6db33f",
    "gutmann": "#070605",
}

# Domain → Google Favicon Service (128px) - robuster für regionale Domains
BRAND_DOMAINS = {
    "jet":     "jet-tankstellen.at",
    "avanti":  "avanti.at",
    "disk":    "diskonttanken.at",
    "diskont": "diskonttanken.at",
    "eni":     "eni.at",
    "omv":     "omv.at",
    "shell":   "shell.at",
    "bp":      "bp.com",
    "esso":    "esso.de",
    "avia":    "avia.at",
    "oil!":    "oil-energy.at",
    "baywa":   "baywa.de",
    "loacker": "loacker-recycling.com",
    "gutmann": "gutmann.at",
}

# ── Daten holen ───────────────────────────────────────────────────────────────
def fetch_stations(fuel_type: str, query_points: list) -> list[dict]:
    print(f"⛽  Lade Tankstellendaten ({fuel_type}) von E-Control API …")
    seen_ids: set = set()
    combined: list[dict] = []
    for lat, lon in query_points:
        try:
            url = (
                f"{API_BASE}?latitude={lat}&longitude={lon}"
                f"&fuelType={fuel_type}&includeClosed=false"
            )
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            batch = resp.json()
            new = [s for s in batch if s.get("id") not in seen_ids]
            seen_ids.update(s["id"] for s in new if s.get("id"))
            combined.extend(new)
            print(f"   ({lat:.3f}, {lon:.3f}) → {len(batch)} Stationen, {len(new)} neu")
        except Exception as e:
            print(f"   WARNUNG: ({lat}, {lon}) fehlgeschlagen: {e}", file=sys.stderr)
    print(f"   → {len(combined)} eindeutige Stationen gesamt")
    return combined

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Luftlinienentfernung in km."""
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def extract_price(station: dict, fuel_type: str) -> float | None:
    for p in station.get("prices", []):
        if p.get("fuelType") == fuel_type and p.get("amount"):
            return float(p["amount"])
    return None

def in_corridor(station: dict, lat_min: float, lat_max: float, lon_min: float, lon_max: float) -> bool:
    loc = station.get("location", {})
    lat, lon = loc.get("latitude"), loc.get("longitude")
    if lat is None or lon is None:
        return False
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max

def process(data: list[dict], fuel_type: str,
            home_lat: float, home_lon: float,
            lat_min: float, lat_max: float, lon_min: float, lon_max: float,
            top_n: int) -> list[dict]:
    result = []
    for s in data:
        if not in_corridor(s, lat_min, lat_max, lon_min, lon_max):
            continue
        if s.get("open") is False:
            continue
        price = extract_price(s, fuel_type)
        if price is None:
            continue
        loc = s.get("location", {})
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        home_dist = round(haversine(home_lat, home_lon, lat, lon), 1) if lat and lon else None
        result.append({
            "name":      s.get("name", "–"),
            "street":    loc.get("address", ""),
            "city":      loc.get("city", ""),
            "zip":       loc.get("postalCode", ""),
            "price":     price,
            "dist_km":   round(float(s["distance"]), 1) if s.get("distance") else None,
            "home_dist": home_dist,
            "lat":       lat,
            "lon":       lon,
            "open":      s.get("open", None),
        })
    result.sort(key=lambda x: (x["price"], x["home_dist"] or 999))
    return result[:top_n]

# ── Daten aufbereiten ─────────────────────────────────────────────────────────
def _top6_ranks(stations: list[dict]) -> list[int]:
    """Ranks (1-based) der 6 nächstgelegenen Stationen innerhalb 10 km."""
    ranked = [(i+1, s) for i, s in enumerate(stations) if (s["home_dist"] or 999) <= 10]
    ranked.sort(key=lambda x: (x[1]["home_dist"] or 999))
    return [rank for rank, _ in ranked[:6]]

def _fuel_json(stations: list[dict], stats: dict) -> dict:
    return {
        "stats": {
            "min":    stats["min_p"],
            "second": stats["second_p"],
            "max":    stats["max_p"],
        },
        "top6": _top6_ranks(stations),
        "data": [
            {k: s[k] for k in ("name", "lat", "lon", "price", "street", "zip", "city", "open", "home_dist")}
            for s in stations
        ],
    }

def _stats(stations: list[dict]) -> dict:
    prices = sorted(set(s["price"] for s in stations))
    return {
        "min_p":    prices[0],
        "second_p": prices[1] if len(prices) > 1 else prices[0],
        "max_p":    stations[-1]["price"],
        "avg":      sum(s["price"] for s in stations) / len(stations),
        "span":     stations[-1]["price"] - prices[0],
        "count":    len(stations),
    }

def generate_html(
    stations_sup: list[dict],
    stations_die: list[dict],
    fetched_at: str,
    home_lat: float,
    home_lon: float,
    home_name: str,
    title: str,
    meta_description: str,
    meta_keywords: str,
    og_title: str,
    og_description: str,
    h1: str,
    sub_sup: str,
    sub_die: str,
    base_url: str = "",
    stations_e10: list[dict] | None = None,
    sub_e10: str = "",
) -> str:
    st_sup = _stats(stations_sup)
    st_die = _stats(stations_die)

    # Build STATIONS JSON for JS rendering
    stations_data: dict = {
        "sup": _fuel_json(stations_sup, st_sup),
        "die": _fuel_json(stations_die, st_die),
    }

    # Optional E10 tab (German market only)
    if stations_e10:
        st_e10     = _stats(stations_e10)
        stations_data["e10"] = _fuel_json(stations_e10, st_e10)
        _e10_btn   = '<button id="btn-e10" class="fuel-btn" onclick="switchFuel(\'e10\')">🌿 Benzin E10</button>'
        _e10_sub   = f'<p class="sub" id="fuel-sub-e10" style="display:none">Top {st_e10["count"]} gemeldete E10 · Super E10 · {sub_e10 or sub_sup} · Luftlinie ab {home_name}</p>'
        _e10_stats = f"""<div class="stats" id="stats-e10" style="display:none">
      <div class="stat"><div class="val">{st_e10["min_p"]:.3f} €</div><div class="lbl">Günstigster Preis</div></div>
      <div class="stat"><div class="val neu">{st_e10["avg"]:.3f} €</div><div class="lbl">Ø Top {st_e10["count"]}</div></div>
      <div class="stat"><div class="val hi">{st_e10["max_p"]:.3f} €</div><div class="lbl">Tagesmax.</div></div>
      <div class="stat"><div class="val">{st_e10["span"]:.3f} €</div><div class="lbl">Max. Ersparnis</div></div>
    </div>"""
        _e10_top4  = '<div id="top4-e10" class="top4-grid" style="display:none"></div>'
        _e10_grid  = '<main class="grid" id="grid-e10" style="display:none"></main>'
        _e10_init  = "initStations('e10');"
        _fuel_keys = "['sup', 'e10', 'die']"
    else:
        _e10_btn = _e10_sub = _e10_stats = _e10_top4 = _e10_grid = _e10_init = ""
        _fuel_keys = "['sup', 'die']"

    all_stations = stations_sup
    clat = sum(s["lat"] for s in all_stations) / len(all_stations)
    clon = sum(s["lon"] for s in all_stations) / len(all_stations)

    # Build absolute og:image URL
    og_image_url = f"{base_url}/screenshots/preview.png" if base_url else "screenshots/preview.png"
    page_url = base_url or ""

    # Serialize STATIONS to JS — compact JSON, safe for embedding
    stations_js = json.dumps(stations_data, ensure_ascii=False, separators=(",", ":"))
    brand_colors_js = json.dumps(BRAND_COLORS, ensure_ascii=False)
    brand_domains_js = json.dumps(BRAND_DOMAINS, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="theme-color" content="#0f0f13" />
  <meta name="color-scheme" content="dark light" />
  <title>{title}</title>

  <!-- Cache Control -->
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
  <meta http-equiv="Pragma" content="no-cache" />
  <meta http-equiv="Expires" content="0" />

  <!-- SEO & Meta Tags -->
  <meta name="description" content="{meta_description}" />
  <meta name="keywords" content="{meta_keywords}" />
  <meta name="author" content="BilligTanken" />
  <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1" />
  <meta name="language" content="de" />
  <meta http-equiv="language" content="de-at" />

  <!-- Open Graph (Facebook, LinkedIn, etc.) -->
  <meta property="og:type" content="website" />
  <meta property="og:title" content="{og_title}" />
  <meta property="og:description" content="{og_description}" />
  <meta property="og:image" content="{og_image_url}" />
  <meta property="og:image:type" content="image/png" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  {f'<meta property="og:url" content="{page_url}" />' if page_url else ""}
  <meta property="og:locale" content="de_AT" />
  <meta property="og:site_name" content="BilligTanken" />

  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{og_title}" />
  <meta name="twitter:description" content="{og_description}" />
  <meta name="twitter:image" content="{og_image_url}" />

  <!-- Apple & Mobile -->
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
  <meta name="apple-mobile-web-app-title" content="BilligTanken" />
  <link rel="apple-touch-icon" href="/apple-touch-icon.png" />

  <!-- Favicon -->
  <link rel="icon" type="image/png" href="/favicon-32x32.png" sizes="32x32" />
  <link rel="icon" type="image/png" href="/favicon-16x16.png" sizes="16x16" />
  <link rel="manifest" href="/site.webmanifest" />

  <!-- JSON-LD Structured Data -->
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "LocalBusiness",
    "name": "BilligTanken",
    "description": "{meta_description}",
    "url": "{page_url or 'https://billigtanken.at'}",
    "image": "{og_image_url}",
    "logo": "{base_url + '/logo.png' if base_url else '/logo.png'}",
    "address": {{
      "@type": "PostalAddress",
      "addressCountry": "AT",
      "addressRegion": "Vorarlberg"
    }},
    "sameAs": []
  }}
  </script>

  <!-- Leaflet.js for map (self-hosted to avoid CDN blocks in Brave/Firefox) -->
  <link rel="stylesheet" href="/leaflet.css" />
  <script src="/leaflet.js"></script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    /* ── Dark theme (default) ── */
    :root, [data-theme="dark"] {{
      --bg:      #0f0f13;
      --surface: #1a1a24;
      --surf2:   #22222f;
      --border:  #2e2e40;
      --text:    #e8e8f0;
      --muted:   #8888aa;
      --popup-bg:#1a1a24;
      --popup-border:#2e2e40;
      --popup-text:#e8e8f0;
      --map-filter: none;
      --link-color: #60a5fa;
      --link-weight: 400;
    }}

    /* ── Light theme ── */
    [data-theme="light"] {{
      --bg:      #f4f4f8;
      --surface: #ffffff;
      --surf2:   #eeeef4;
      --border:  #d0d0e0;
      --text:    #1a1a2e;
      --muted:   #666688;
      --popup-bg:#ffffff;
      --popup-border:#d0d0e0;
      --popup-text:#1a1a2e;
      --map-filter: none;
      --link-color: #1a4fa8;
      --link-weight: 700;
    }}

    /* ── System preference ── */
    @media (prefers-color-scheme: light) {{
      :root:not([data-theme="dark"]):not([data-theme="light"]) {{
        --bg:      #f4f4f8;
        --surface: #ffffff;
        --surf2:   #eeeef4;
        --border:  #d0d0e0;
        --text:    #1a1a2e;
        --muted:   #666688;
        --popup-bg:#ffffff;
        --popup-border:#d0d0e0;
        --popup-text:#1a1a2e;
        --link-color: #1a4fa8;
        --link-weight: 700;
        --map-filter: none;
      }}
    }}

    :root {{
      --green:  #22c55e;
      --gold:   #fbbf24;
      --silver: #94a3b8;
      --bronze: #cd7f32;
      --r:      16px;
    }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg); color: var(--text);
      min-height: 100vh; padding: 2rem 1rem 4rem;
      transition: background .25s, color .25s;
    }}

    /* ── Theme toggle button ── */
    .theme-toggle {{
      position: fixed; top: 1rem; right: 1rem; z-index: 9999;
      display: flex; align-items: center; gap: 0;
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 999px; padding: .25rem;
      box-shadow: 0 2px 8px rgba(0,0,0,.15);
    }}
    .theme-toggle button {{
      background: none; border: none; cursor: pointer;
      padding: .3rem .55rem; border-radius: 999px;
      font-size: .8rem; color: var(--muted);
      transition: background .15s, color .15s;
      line-height: 1;
    }}
    .theme-toggle button.active {{
      background: var(--surf2); color: var(--text);
      box-shadow: 0 1px 3px rgba(0,0,0,.2);
    }}
    .theme-toggle button:hover:not(.active) {{ color: var(--text); }}

    /* ── Fuel toggle ── */
    .fuel-toggle {{
      display: inline-flex; gap: 0; margin-bottom: .6rem;
      background: var(--surf2); border: 1px solid var(--border);
      border-radius: 999px; padding: .2rem;
    }}
    .fuel-btn {{
      background: none; border: none; cursor: pointer;
      padding: .35rem .9rem; border-radius: 999px;
      font-size: .82rem; font-weight: 600; color: var(--muted);
      transition: background .15s, color .15s;
    }}
    .fuel-btn.active {{
      background: var(--surface); color: var(--text);
      box-shadow: 0 1px 4px rgba(0,0,0,.2);
    }}
    .fuel-btn:hover:not(.active) {{ color: var(--text); }}

    .pill {{
      display: inline-block;
      font-size: .72rem; padding: .28rem .75rem; border-radius: 999px;
    }}
    .pill.time {{ color: var(--muted); background: var(--surf2); border: 1px solid var(--border); }}
    .pill.note {{ color: #f59e0b; background: rgba(245,158,11,.1); border: 1px solid rgba(245,158,11,.25); }}

    /* Overview row: left col + map + top-4 */
    .overview {{
      display: grid;
      grid-template-columns: 260px 1fr 430px;
      gap: 1rem;
      max-width: 1500px;
      margin: 0 auto 2rem;
      align-items: stretch;
    }}
    @media (max-width: 1100px) {{
      .overview {{ grid-template-columns: 260px 1fr; }}
      .top4-panel {{ display: none; }}
    }}
    @media (max-width: 800px) {{
      .overview {{ grid-template-columns: 1fr; }}
    }}

    /* Top-4 mini-card panel */
    .top4-panel {{
      display: flex; flex-direction: column; gap: .5rem; align-self: start;
    }}
    .top4-grid {{
      display: grid; grid-template-columns: 1fr 1fr; gap: .5rem;
    }}
    .top4-label {{
      font-size: .72rem; font-weight: 700; color: var(--muted);
      text-transform: uppercase; letter-spacing: .05em; margin-bottom: .1rem;
    }}
    .mini-card {{
      background: var(--surface); border: 1px solid var(--border);
      border-radius: var(--r); padding: .6rem .7rem;
      display: flex; flex-direction: column; gap: .25rem;
      cursor: pointer; transition: transform .15s, box-shadow .15s;
      position: relative; overflow: hidden;
    }}
    .mini-card::before {{
      content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px;
      background: var(--brand, #4f46e5);
    }}
    .mini-card.rank-gold::before  {{ background: var(--gold); }}
    .mini-card.rank-silver::before {{ background: var(--silver); }}
    .mini-card:hover {{ transform: translateY(-2px); box-shadow: 0 6px 18px rgba(0,0,0,.35); }}
    .mini-top {{
      display: flex; align-items: center; gap: .4rem;
    }}
    .mini-avatar {{
      width: 26px; height: 26px; border-radius: 6px; flex-shrink: 0;
      display: flex; align-items: center; justify-content: center;
      font-weight: 800; font-size: .6rem; color: #fff;
    }}
    .mini-avatar.avatar-logo {{ background: #fff; padding: 2px; box-shadow: 0 1px 3px rgba(0,0,0,.25); }}
    .mini-avatar.avatar-logo img {{ width: 100%; height: 100%; object-fit: contain; border-radius: 4px; }}
    .mini-avatar.brand-eni img, .mini-avatar.brand-bp img {{ transform: scale(1.3); }}
    .mini-rank .medal {{ font-size: .6rem; padding: .1rem .35rem; }}
    .mini-rank .rank-num {{ font-size: .65rem; }}
    .mini-name {{ font-size: .72rem; font-weight: 600; line-height: 1.3; color: var(--text); }}
    .mini-badges {{
      display: flex; align-items: center; gap: .3rem; flex-wrap: wrap; margin-left: auto;
    }}
    .mini-dist {{ font-size: .62rem; }}
    .mini-address {{
      font-size: .65rem; line-height: 1.3; display: flex; align-items: flex-start; gap: .25rem;
    }}
    .mini-address svg {{ flex-shrink: 0; margin-top: .1rem; }}
    .mini-footer {{
      display: flex; align-items: center; justify-content: space-between; gap: .4rem; margin-top: .1rem;
    }}
    .mini-price {{
      font-size: 1.1rem; font-weight: 800; letter-spacing: -.02em;
      line-height: 1; white-space: nowrap;
    }}
    .mini-price small {{ font-size: .6rem; font-weight: 500; color: var(--muted); }}
    .mini-route {{ font-size: .65rem; padding: .2rem .45rem; }}

    /* Left column: header + stats */
    .left-col {{
      display: flex; flex-direction: column; gap: .9rem;
    }}

    /* Header (now inside left col) */
    header {{ text-align: left; }}
    header h1 {{
      font-size: clamp(1.2rem, 2.5vw, 1.6rem);
      font-weight: 800; letter-spacing: -.03em;
      background: linear-gradient(135deg, #a78bfa, #60a5fa, #34d399);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    }}
    header p.sub {{ color: var(--muted); margin-top: .3rem; font-size: .8rem; line-height: 1.4; }}
    .pills {{ display: flex; flex-wrap: wrap; gap: .4rem; margin-top: .6rem; }}

    /* Stats */
    .stats {{ display: flex; flex-direction: column; gap: .6rem; flex: 1; }}
    .stat {{
      background: var(--surface); border: 1px solid var(--border);
      border-radius: var(--r); padding: .7rem 1rem;
      display: flex; align-items: center; justify-content: space-between; gap: .5rem;
    }}
    .stat .val {{ font-size: 1.2rem; font-weight: 700; color: var(--green); }}
    .stat .val.hi {{ color: #f87171; }}
    .stat .val.neu {{ color: var(--text); }}
    .stat .lbl {{ font-size: .73rem; color: var(--muted); }}

    /* MAP */
    #map {{
      height: 100%; min-height: 340px; border-radius: var(--r);
      border: 1px solid var(--border); overflow: hidden;
    }}

    /* Grid */
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(250px, 250px));
      gap: 1.1rem; max-width: 1400px; margin: 0 auto;
    }}

    /* Card */
    .card {{
      background: var(--surface); border: 1px solid var(--border);
      border-radius: var(--r); padding: .85rem;
      display: flex; flex-direction: column; gap: .55rem;
      position: relative; overflow: hidden;
      transition: transform .2s, box-shadow .2s;
      cursor: default;
    }}
    .card::before {{
      content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px;
      background: var(--brand, #4f46e5);
    }}
    .card:hover {{ transform: translateY(-3px); box-shadow: 0 12px 32px rgba(0,0,0,.5); }}
    .card.highlighted {{ box-shadow: 0 0 0 2px #60a5fa, 0 12px 32px rgba(0,0,0,.5); }}

    .rank-gold   {{ border-color: var(--gold);   }}
    .rank-silver {{ border-color: var(--silver); }}
    .rank-bronze {{ border-color: var(--bronze); }}
    .rank-gold::before   {{ background: var(--gold); height: 4px; }}
    .rank-silver::before {{ background: var(--silver); }}
    .rank-bronze::before {{ background: var(--bronze); }}

    .card-header {{ display: flex; align-items: center; justify-content: space-between; }}
    .avatar {{
      width: 38px; height: 38px; border-radius: 9px; flex-shrink: 0;
      display: flex; align-items: center; justify-content: center;
      font-weight: 800; font-size: .83rem; color: #fff;
      text-shadow: 0 1px 3px rgba(0,0,0,.4);
    }}
    .avatar-logo {{
      background: #fff;
      padding: 4px;
      box-shadow: 0 1px 4px rgba(0,0,0,.3);
    }}
    /* ── Logo Sizing ── */
    .avatar-logo img {{
      width: 100%; height: 100%;
      object-fit: contain; border-radius: 6px;
    }}
    /* Specific fix for Eni logo (often appears small) */
    .brand-eni img {{
      transform: scale(1.4);
    }}
    /* BP logo needs scaling up */
    .brand-bp img {{
      transform: scale(1.5);
    }}
    .card-meta {{ display: flex; align-items: center; gap: .35rem; flex-wrap: wrap; justify-content: flex-end; }}
    .medal {{
      font-size: .72rem; font-weight: 700; padding: .22rem .55rem; border-radius: 999px;
    }}
    .medal.gold   {{ background: rgba(251,191,36,.15); color: var(--gold);   border: 1px solid rgba(251,191,36,.3); }}
    .medal.silver {{ background: rgba(148,163,184,.12); color: var(--silver); border: 1px solid rgba(148,163,184,.25); }}
    .medal.bronze {{ background: rgba(205,127,50,.12);  color: var(--bronze); border: 1px solid rgba(205,127,50,.25); }}
    .rank-num {{ font-size: .78rem; color: var(--muted); font-weight: 600; }}
    .badge {{
      font-size: .67rem; font-weight: 600; padding: .2rem .5rem; border-radius: 999px;
    }}
    .badge.open   {{ background: rgba(34,197,94,.15); color: #22c55e; border: 1px solid rgba(34,197,94,.3); }}
    .badge.closed {{ background: rgba(239,68,68,.15);  color: #ef4444; border: 1px solid rgba(239,68,68,.3); }}
    .dist {{
      font-size: .7rem; color: var(--muted); background: var(--surf2);
      padding: .18rem .48rem; border-radius: 999px; border: 1px solid var(--border);
    }}
    .home-dist {{
      color: #a78bfa; background: rgba(167,139,250,.1); border-color: rgba(167,139,250,.25);
    }}

    .card-body {{ flex: 1; }}
    .station-name {{ font-size: .93rem; font-weight: 700; line-height: 1.3; margin-bottom: .2rem; }}
    .address {{
      font-size: .78rem; color: var(--link-color); font-weight: var(--link-weight);
      display: flex; align-items: flex-start; gap: .32rem; line-height: 1.4;
      text-decoration: underline; cursor: pointer;
    }}
    .address:hover {{ opacity: .75; }}
    .address svg {{ flex-shrink: 0; margin-top: .15rem; stroke: #ef4444; }}

    .card-footer {{
      display: flex; align-items: center; justify-content: space-between;
      padding-top: .5rem; border-top: 1px solid var(--border); gap: .5rem;
    }}
    .price-block {{ display: flex; flex-direction: column; gap: .22rem; min-width: 0; }}
    .price-row {{ display: flex; align-items: baseline; gap: .45rem; flex-wrap: wrap; }}
    .price {{ font-size: 1.45rem; font-weight: 800; letter-spacing: -.02em; line-height: 1; white-space: nowrap; }}
    .price small {{ font-size: .82rem; font-weight: 500; color: var(--muted); }}
    .savings {{
      font-size: .72rem; font-weight: 700; padding: .14rem .48rem;
      border-radius: 999px; align-self: flex-start;
      background: rgba(74,222,128,.12); color: #4ade80; border: 1px solid rgba(74,222,128,.22);
    }}
    .savings.maxprice {{
      background: rgba(248,113,113,.1); color: #f87171; border-color: rgba(248,113,113,.2);
    }}
    .price-bar-wrap {{
      height: 4px; background: var(--border); border-radius: 999px;
      width: 110px; overflow: hidden;
    }}
    .price-bar {{ height: 100%; border-radius: 999px; }}

    .btn-group {{ display: flex; gap: .4rem; flex-shrink: 0; }}
    .map-btn {{
      display: inline-flex; align-items: center; gap: .32rem;
      font-size: .78rem; font-weight: 600; color: var(--text);
      background: var(--surf2); border: 1px solid var(--border);
      padding: .42rem .85rem; border-radius: 8px;
      cursor: pointer; flex-shrink: 0; text-decoration: none;
      transition: background .15s, border-color .15s;
    }}
    .map-btn:hover {{ background: var(--border); border-color: var(--muted); }}
    .route-btn {{ border-color: rgba(96,165,250,.3); color: #60a5fa; }}
    .route-btn:hover {{ background: rgba(96,165,250,.1); border-color: #60a5fa; color: #60a5fa; }}

    /* Leaflet popup themed */
    .leaflet-popup-content-wrapper {{
      background: var(--popup-bg) !important; color: var(--popup-text) !important;
      border: 1px solid var(--popup-border) !important; border-radius: 10px !important;
      box-shadow: 0 8px 24px rgba(0,0,0,.2) !important;
    }}
    .leaflet-popup-tip {{ background: var(--popup-bg) !important; }}
    .leaflet-popup-content {{ font-size: .85rem; line-height: 1.5; }}

    footer.pf {{
      text-align: center; margin-top: 3rem; font-size: .76rem; color: var(--muted);
    }}
    footer.pf a {{ color: var(--muted); }}
  </style>
</head>
<body>

<div class="theme-toggle" id="theme-toggle">
  <button onclick="setTheme('light')" title="Hell">☀️</button>
  <button onclick="setTheme('system')" title="System">💻</button>
  <button onclick="setTheme('dark')" title="Dunkel">🌙</button>
</div>

<div class="overview">
  <div class="left-col">
    <header>
      <h1>{h1}</h1>
      <div class="fuel-toggle">
        <button id="btn-sup" class="fuel-btn active" onclick="switchFuel('sup')">⛽ Benzin E5</button>
        {_e10_btn}
        <button id="btn-die" class="fuel-btn" onclick="switchFuel('die')">🛢 Diesel</button>
      </div>
      <p class="sub" id="fuel-sub-sup">Top {st_sup["count"]} gemeldete E5 · Super 95 · {sub_sup} · Luftlinie ab {home_name}</p>
      {_e10_sub}
      <p class="sub" id="fuel-sub-die" style="display:none">Top {st_die["count"]} gemeldete Diesel · {sub_die} · Luftlinie ab {home_name}</p>
      <div class="pills">
        <span class="pill time">Aktualisiert: {fetched_at}</span>
        <span class="pill note">⚠ Tageshöchstpreis aktiv</span>
        <span class="pill time" id="geo-pill" style="color:#a78bfa">🏠 Standort wird ermittelt …</span>
      </div>
    </header>
    <div class="stats" id="stats-sup">
      <div class="stat"><div class="val">{st_sup["min_p"]:.3f} €</div><div class="lbl">Günstigster Preis</div></div>
      <div class="stat"><div class="val neu">{st_sup["avg"]:.3f} €</div><div class="lbl">Ø Top {st_sup["count"]}</div></div>
      <div class="stat"><div class="val hi">{st_sup["max_p"]:.3f} €</div><div class="lbl">Tageshöchstpreis</div></div>
      <div class="stat"><div class="val">{st_sup["span"]:.3f} €</div><div class="lbl">Max. Ersparnis</div></div>
    </div>
    {_e10_stats}
    <div class="stats" id="stats-die" style="display:none">
      <div class="stat"><div class="val">{st_die["min_p"]:.3f} €</div><div class="lbl">Günstigster Preis</div></div>
      <div class="stat"><div class="val neu">{st_die["avg"]:.3f} €</div><div class="lbl">Ø Top {st_die["count"]}</div></div>
      <div class="stat"><div class="val hi">{st_die["max_p"]:.3f} €</div><div class="lbl">Tageshöchstpreis</div></div>
      <div class="stat"><div class="val">{st_die["span"]:.3f} €</div><div class="lbl">Max. Ersparnis</div></div>
    </div>
  </div>
  <div id="map"></div>
  <div class="top4-panel">
    <div class="top4-label">Top 4 &lt;10 km</div>
    <div id="top4-sup" class="top4-grid"></div>
    {_e10_top4}
    <div id="top4-die" class="top4-grid" style="display:none"></div>
  </div>
</div>

<main class="grid" id="grid-sup"></main>
{_e10_grid}
<main class="grid" id="grid-die" style="display:none"></main>

<footer class="pf">
  Datenquelle: <a href="https://www.spritpreisrechner.at" target="_blank">E-Control Austria</a>
  · Karte: <a href="https://leafletjs.com" target="_blank">Leaflet</a> / <a href="https://www.openstreetmap.org" target="_blank">OpenStreetMap</a>
  · Preise in €/Liter inkl. MwSt. · Alle Angaben ohne Gewähr
</footer>

<script>
  // ── Station data (server-rendered JSON) ──────────────────────────────────
  const STATIONS = {stations_js};

  // ── Brand helpers ─────────────────────────────────────────────────────────
  const BRAND_COLORS  = {brand_colors_js};
  const BRAND_DOMAINS = {brand_domains_js};

  function brandColor(name) {{
    const n = name.toLowerCase();
    for (const [key, color] of Object.entries(BRAND_COLORS)) {{
      if (n.includes(key)) return color;
    }}
    return "#4f46e5";
  }}

  function brandLogo(name) {{
    const n = name.toLowerCase();
    if (n.includes("eni")) return "https://upload.wikimedia.org/wikipedia/de/thumb/8/8a/Logo_ENI.svg/1280px-Logo_ENI.svg.png";
    if (n.includes("bp"))  return "https://1000logos.net/wp-content/uploads/2016/10/BP-Logo.png";
    for (const [key, domain] of Object.entries(BRAND_DOMAINS)) {{
      if (n.includes(key)) return `https://www.google.com/s2/favicons?domain=${{domain}}&sz=128`;
    }}
    return null;
  }}

  function brandInitial(name) {{
    const words = name.trim().split(/\s+/);
    if (!words.length || !words[0]) return "?";
    const first = words[0][0];
    const second = words.length > 1 ? words[1][0] : (words[0].length > 1 ? words[0][1] : first);
    return (first + second).toUpperCase();
  }}

  function markerColor(rank, total) {{
    const hue = Math.round(120 * (1 - (rank - 1) / Math.max(total - 1, 1)));
    return `hsl(${{hue}},80%,45%)`;
  }}

  function rankInfo(rank, price, minP, secondP) {{
    const p = Math.round(price * 1000);
    if (p === Math.round(minP * 1000))    return {{ cls: "rank-gold",   html: '<span class="medal gold">🥇 Günstigste</span>' }};
    if (p === Math.round(secondP * 1000)) return {{ cls: "rank-silver", html: '<span class="medal silver">🥈 2. Preis</span>' }};
    return {{ cls: "", html: `<span class="rank-num">#${{rank}}</span>` }};
  }}

  function openBadge(isOpen) {{
    if (isOpen === true)  return '<span class="badge open">Offen</span>';
    if (isOpen === false) return '<span class="badge closed">Geschlossen</span>';
    return "";
  }}

  function savingsBadge(price, maxP) {{
    const diff = maxP - price;
    if (diff < 0.0005) return '<span class="savings maxprice">Höchstpreis</span>';
    return `<span class="savings">− ${{diff.toFixed(3)}} €</span>`;
  }}

  function priceBar(price, minP, maxP) {{
    const span = maxP - minP;
    const pct = span ? Math.round(100 * (price - minP) / span) : 0;
    const hue = Math.round(120 * (1 - pct / 100));
    return `<div class="price-bar-wrap"><div class="price-bar" style="width:${{Math.max(4, pct)}}%;background:hsl(${{hue}},70%,45%)"></div></div>`;
  }}

  function makeAvatar(name, color, big) {{
    const logo = brandLogo(name);
    const n = name.toLowerCase();
    const isEni = n.includes("eni"), isBp = n.includes("bp");
    if (logo) {{
      const ex = isEni ? "brand-eni" : (isBp ? "brand-bp" : "");
      const cls = big ? `avatar avatar-logo ${{ex}}` : `mini-avatar avatar-logo ${{ex}}`;
      return `<div class="${{cls}}" style="--brand:${{color}}"><img src="${{logo}}" alt="${{name}}" onerror="this.parentElement.innerHTML='<span>${{brandInitial(name)}}</span>'"></div>`;
    }}
    const cls = big ? "avatar" : "mini-avatar";
    return `<div class="${{cls}}" style="background:${{color}}">${{brandInitial(name)}}</div>`;
  }}

  const SVG_PIN = `<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>`;
  const SVG_PIN_SM = `<svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>`;
  const SVG_ROUTE = `<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg>`;
  const SVG_ROUTE_SM = `<svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg>`;

  // ── Card renderers ────────────────────────────────────────────────────────
  function renderCard(s, rank, fkey, stats) {{
    const {{ min, second, max }} = stats;
    const color = brandColor(s.name);
    const {{ cls, html: rankHtml }} = rankInfo(rank, s.price, min, second);
    const distStr = s.home_dist != null ? `📍 ${{s.home_dist.toFixed(1)}} km` : "📍 –";
    const dest = `${{s.lat}},${{s.lon}}`;
    const mapsHref = `https://www.google.com/maps/dir/?api=1&destination=${{dest}}&travelmode=driving`;

    const art = document.createElement('article');
    art.className = `card ${{cls}}`;
    art.id = `card-${{fkey}}-${{rank}}`;
    art.style.cssText = `--brand:${{color}}`;
    art.innerHTML = `
      <div class="card-header">
        ${{makeAvatar(s.name, color, true)}}
        <div class="card-meta">
          ${{rankHtml}}
          ${{openBadge(s.open)}}
          <span class="dist home-dist" id="dist-${{fkey}}-${{rank}}">${{distStr}}</span>
        </div>
      </div>
      <div class="card-body">
        <h2 class="station-name">${{s.name}}</h2>
        <a class="address" onclick="focusMarker('${{fkey}}',${{rank}});return false;" href="#">
          ${{SVG_PIN}} ${{s.street}}, ${{s.zip}} ${{s.city}}
        </a>
      </div>
      <div class="card-footer">
        <div class="price-block">
          <div class="price-row">
            <span class="price">${{s.price.toFixed(3)}} <small>€/L</small></span>
            ${{savingsBadge(s.price, max)}}
          </div>
          ${{priceBar(s.price, min, max)}}
        </div>
        <div class="btn-group">
          <a class="map-btn route-btn" id="route-${{fkey}}-${{rank}}"
             href="${{mapsHref}}" target="_blank" rel="noopener">
            ${{SVG_ROUTE}} Route
          </a>
        </div>
      </div>`;
    return art;
  }}

  function renderMiniCard(s, rank, fkey, stats) {{
    const {{ min, second }} = stats;
    const color = brandColor(s.name);
    const {{ cls, html: rankHtml }} = rankInfo(rank, s.price, min, second);
    const distStr = s.home_dist != null ? `📍 ${{s.home_dist.toFixed(1)}} km` : "📍 –";
    const dest = `${{s.lat}},${{s.lon}}`;
    const mapsHref = `https://www.google.com/maps/dir/?api=1&destination=${{dest}}&travelmode=driving`;

    const div = document.createElement('div');
    div.className = `mini-card ${{cls}}`;
    div.style.cssText = `--brand:${{color}}`;
    div.setAttribute('onclick',
      `document.getElementById('card-${{fkey}}-${{rank}}').scrollIntoView({{behavior:'smooth',block:'center'}})`);
    div.innerHTML = `
      <div class="mini-top">
        ${{makeAvatar(s.name, color, false)}}
        <span class="mini-rank">${{rankHtml}}</span>
        <span class="mini-badges">
          ${{openBadge(s.open)}}
          <span class="dist mini-dist" id="mdist-${{fkey}}-${{rank}}">${{distStr}}</span>
        </span>
      </div>
      <div class="mini-name">${{s.name}}</div>
      <a class="mini-address address" onclick="focusMarker('${{fkey}}',${{rank}});return false;" href="#">
        ${{SVG_PIN_SM}} ${{s.street}}, ${{s.zip}} ${{s.city}}
      </a>
      <div class="mini-footer">
        <div class="mini-price">${{s.price.toFixed(3)}} <small>€/L</small></div>
        <a class="map-btn route-btn mini-route" id="mroute-${{fkey}}-${{rank}}"
           href="${{mapsHref}}" target="_blank" rel="noopener"
           onclick="event.stopPropagation()">
          ${{SVG_ROUTE_SM}} Route
        </a>
      </div>`;
    return div;
  }}

  // ── Leaflet Map ───────────────────────────────────────────────────────────
  const map = L.map('map', {{ zoomControl: true }}).setView([{clat:.4f}, {clon:.4f}], 11);

  L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png', {{
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> © <a href="https://carto.com">CARTO</a>',
    subdomains: 'abcd', maxZoom: 19
  }}).addTo(map);

  const allMarkers = {{ sup: {{}}, e10: {{}}, die: {{}} }};
  let currentFuel = localStorage.getItem('fuel') || 'sup';

  function makeIcon(color, label) {{
    return L.divIcon({{
      className: '',
      html: `<div style="
        background:${{color}};
        width:32px;height:32px;border-radius:50% 50% 50% 0;
        transform:rotate(-45deg);
        border:2px solid rgba(255,255,255,.35);
        box-shadow:0 3px 10px rgba(0,0,0,.5);
        display:flex;align-items:center;justify-content:center;">
        <span style="transform:rotate(45deg);color:#fff;font-weight:800;font-size:11px;">${{label}}</span>
      </div>`,
      iconSize: [32, 32],
      iconAnchor: [16, 32],
      popupAnchor: [0, -34],
    }});
  }}

  function addMarker(fkey, lat, lon, popup, color, label, rank) {{
    const m = L.marker([lat, lon], {{ icon: makeIcon(color, label) }})
      .bindPopup(popup);
    allMarkers[fkey][rank] = m;

    m.on('click', () => {{
      const card = document.getElementById('card-' + fkey + '-' + rank);
      if (card) {{
        document.querySelectorAll('.card').forEach(c => c.classList.remove('highlighted'));
        card.classList.add('highlighted');
        card.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
      }}
    }});
  }}

  function focusMarker(fkey, rank) {{
    const m = allMarkers[fkey][rank];
    if (!m) return;
    map.setView(m.getLatLng(), 15, {{ animate: true }});
    m.openPopup();
    window.scrollTo({{ top: 0, behavior: 'smooth' }});
    document.querySelectorAll('.card').forEach(c => c.classList.remove('highlighted'));
    document.getElementById('card-' + fkey + '-' + rank)?.classList.add('highlighted');
  }}

  function switchFuel(fuel) {{
    if (fuel === currentFuel) return;
    const ids = ['grid', 'stats', 'fuel-sub', 'top4'];
    ids.forEach(id => {{
      document.getElementById(id + '-' + currentFuel).style.display = 'none';
      document.getElementById(id + '-' + fuel).style.display = '';
    }});
    Object.values(allMarkers[currentFuel]).forEach(m => map.removeLayer(m));
    Object.values(allMarkers[fuel]).forEach(m => m.addTo(map));
    document.getElementById('btn-' + currentFuel).classList.remove('active');
    document.getElementById('btn-' + fuel).classList.add('active');
    currentFuel = fuel;
    localStorage.setItem('fuel', fuel);
  }}

  // ── initStations: renders cards + mini-cards + registers markers ──────────
  function initStations(fkey) {{
    const fuel = STATIONS[fkey];
    if (!fuel) return;
    const {{ data, stats, top6 }} = fuel;
    const total = data.length;

    // Main grid cards
    const grid = document.getElementById('grid-' + fkey);
    const frag = document.createDocumentFragment();
    data.forEach((s, i) => {{
      const rank = i + 1;
      frag.appendChild(renderCard(s, rank, fkey, stats));
      const mColor = markerColor(rank, total);
      const distPart = s.home_dist != null ? `<br>📍 ${{s.home_dist.toFixed(1)}} km ab {home_name}` : "";
      const popup = `<b>#${{rank}} ${{s.name}}</b><br>${{s.street}}, ${{s.zip}} ${{s.city}}<br><span style='font-size:1.2em;font-weight:700'>${{s.price.toFixed(3)}} €/L</span>${{distPart}}`;
      addMarker(fkey, s.lat, s.lon, popup, mColor, rank, rank);
    }});
    grid.appendChild(frag);

    // Top-6 mini-cards
    const top4div = document.getElementById('top4-' + fkey);
    const mfrag = document.createDocumentFragment();
    top6.forEach(rank => {{
      mfrag.appendChild(renderMiniCard(data[rank - 1], rank, fkey, stats));
    }});
    top4div.appendChild(mfrag);
  }}

  // ── Theme ────────────────────────────────────────────────────────────────
  function setTheme(t) {{
    const root = document.documentElement;
    if (t === 'system') root.removeAttribute('data-theme');
    else root.setAttribute('data-theme', t);
    localStorage.setItem('theme', t);
    document.querySelectorAll('.theme-toggle button').forEach((btn, i) => {{
      btn.classList.toggle('active', ['light','system','dark'][i] === t);
    }});
  }}
  (function() {{
    const saved = localStorage.getItem('theme') || 'system';
    setTheme(saved);
  }})();

  // ── Geolocation ──────────────────────────────────────────────────────────
  function haversineJS(lat1, lon1, lat2, lon2) {{
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat/2)**2 +
              Math.cos(lat1 * Math.PI/180) * Math.cos(lat2 * Math.PI/180) * Math.sin(dLon/2)**2;
    return R * 2 * Math.asin(Math.sqrt(a));
  }}

  let homeMarker = null;

  function updateWithLocation(lat, lon, isLive) {{
    for (const fkey of {_fuel_keys}) {{
      STATIONS[fkey].data.forEach((s, i) => {{
        const rank = i + 1;
        const d = haversineJS(lat, lon, s.lat, s.lon).toFixed(1);
        const distEl = document.getElementById('dist-' + fkey + '-' + rank);
        if (distEl) distEl.textContent = '📍 ' + d + ' km';
        const mDistEl = document.getElementById('mdist-' + fkey + '-' + rank);
        if (mDistEl) mDistEl.textContent = '📍 ' + d + ' km';
        const origin = `${{lat}},${{lon}}`;
        const dest   = `${{s.lat}},${{s.lon}}`;
        const href   = `https://www.google.com/maps/dir/?api=1&origin=${{origin}}&destination=${{dest}}&travelmode=driving`;
        const routeEl = document.getElementById('route-' + fkey + '-' + rank);
        if (routeEl) routeEl.href = href;
        const mRouteEl = document.getElementById('mroute-' + fkey + '-' + rank);
        if (mRouteEl) mRouteEl.href = href;
      }});
    }}
    map.setView([lat, lon], map.getZoom(), {{ animate: true }});
    if (homeMarker) map.removeLayer(homeMarker);
    const label = isLive ? 'Ihr Standort (GPS)' : '{home_name} (Fallback)';
    homeMarker = L.marker([lat, lon], {{
      zIndexOffset: 1000,
      icon: L.divIcon({{
        className: '',
        html: `<div style="background:${{isLive ? '#22c55e' : '#6366f1'}};width:36px;height:36px;
                           border-radius:50%;border:3px solid #fff;
                           box-shadow:0 3px 10px rgba(0,0,0,.4);
                           display:flex;align-items:center;justify-content:center;font-size:18px;">
                 ${{isLive ? '📱' : '🏠'}}
               </div>`,
        iconSize: [36, 36], iconAnchor: [18, 18], popupAnchor: [0, -20],
      }})
    }}).addTo(map).bindPopup(`<b>${{label}}</b>`);

    const pill = document.getElementById('geo-pill');
    if (pill) {{
      pill.textContent = isLive ? '📱 GPS-Standort aktiv' : '🏠 Fallback: {home_name}';
      pill.style.color = isLive ? '#22c55e' : '#a78bfa';
    }}
  }}

  // ── Startup sequence ──────────────────────────────────────────────────────
  // 1. Render all stations (creates DOM elements + registers map markers)
  initStations('sup');
  initStations('die');
  {_e10_init}

  // 2. Initial location render (DOM elements now exist)
  updateWithLocation({home_lat}, {home_lon}, false);

  // 3. Apply saved fuel preference (adds markers to map, shows correct grid)
  (function initFuel() {{
    Object.values(allMarkers[currentFuel]).forEach(m => m.addTo(map));
    if (currentFuel !== 'sup') {{
      ['grid', 'stats', 'fuel-sub', 'top4'].forEach(id => {{
        document.getElementById(id + '-sup').style.display = 'none';
        document.getElementById(id + '-' + currentFuel).style.display = '';
      }});
      document.getElementById('btn-sup').classList.remove('active');
      document.getElementById('btn-' + currentFuel).classList.add('active');
    }}
  }})();

  // 4. Try GPS (updates distances + route links if granted)
  if (navigator.geolocation) {{
    navigator.geolocation.getCurrentPosition(
      pos => updateWithLocation(pos.coords.latitude, pos.coords.longitude, true),
      ()  => updateWithLocation({home_lat}, {home_lon}, false),
      {{ timeout: 8000 }}
    );
  }}
</script>

</body>
</html>"""

def write_html(html: str, output: Path, output_new: Path) -> None:
    """Atomic write: write to temp file, then rename."""
    output_new.write_text(html, encoding="utf-8")
    output_new.rename(output)   # atomic swap – kein halb-fertiges index.html

def print_summary(stations_sup: list[dict], stations_die: list[dict]) -> None:
    """Print a tabular summary of results to stdout."""
    for label, stations in [("E5/SUP", stations_sup), ("Diesel/DIE", stations_die)]:
        if not stations:
            continue
        max_p = stations[-1]["price"]
        print(f"\n── {label} ─────────────────────────────")
        print(f"{'#':>2}  {'Preis':>8}  {'Ersparnis':>10}  {'Luftlinie':>10}  {'Name':<32}  {'Ort'}")
        print("─" * 85)
        for i, s in enumerate(stations, 1):
            sav  = max_p - s["price"]
            dist = f"{s['home_dist']} km" if s["home_dist"] else "–"
            print(f"{i:>2}  {s['price']:.3f} €  {'−'+f'{sav:.3f} €':>10}  {dist:>10}  {s['name']:<32}  {s['city']}")
