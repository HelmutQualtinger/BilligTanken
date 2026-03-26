#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AlterlaaTanken – Günstigste Tankstellen rund um die Hochhäuser Alt-Erlaa in Wien
Quelle: E-Control Austria API (spritpreisrechner.at)
"""

import requests
import json
import sys
import math
import os
from datetime import datetime
from pathlib import Path

# ── Konfiguration ─────────────────────────────────────────────────────────────
TOP_N      = 50
_web_root  = Path(os.environ.get("WEB_ROOT", "."))
OUTPUT     = _web_root / "alterlaa-tanken.html"
OUTPUT_NEW = _web_root / "alterlaa-tanken_new.html"

# Referenzpunkt Alt-Erlaa Hochhäuser, Wien 23 (48°09'06"N 16°18'43"E)
HOME_LAT  = 48.1517
HOME_LON  = 16.3119
HOME_NAME = "Alt-Erlaa Wien"

API_BASE = "https://api.e-control.at/sprit/1.0/search/gas-stations/by-address"
HEADERS  = {"User-Agent": "Mozilla/5.0 (compatible; BilligTanken/1.0)"}

QUERY_POINTS = [
    (48.152, 16.312),   # Alt-Erlaa (Zentrum)
    (48.132, 16.323),   # Liesing
    (48.178, 16.325),   # Meidling / Schönbrunn
    (48.162, 16.360),   # Favoriten
    (48.138, 16.355),   # Inzersdorf
    (48.116, 16.267),   # Perchtoldsdorf
    (48.085, 16.284),   # Mödling
    (48.110, 16.335),   # Vösendorf
    (48.135, 16.485),   # Schwechat
    (48.170, 16.410),   # Simmering
    (48.060, 16.310),   # Wiener Neudorf
    (48.090, 16.440),   # Himberg
]

LAT_MIN, LAT_MAX = 48.00, 48.28
LON_MIN, LON_MAX = 16.15, 16.60

# ── Daten holen ───────────────────────────────────────────────────────────────
def fetch_stations(fuel_type: str) -> list[dict]:
    print(f"⛽  Lade Tankstellendaten ({fuel_type}) von E-Control API …")
    seen_ids: set = set()
    combined: list[dict] = []
    for lat, lon in QUERY_POINTS:
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

def in_corridor(station: dict) -> bool:
    loc = station.get("location", {})
    lat, lon = loc.get("latitude"), loc.get("longitude")
    if lat is None or lon is None:
        return False
    return LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX

def process(data: list[dict], fuel_type: str) -> list[dict]:
    result = []
    for s in data:
        if not in_corridor(s):
            continue
        price = extract_price(s, fuel_type)
        if price is None:
            continue
        loc = s.get("location", {})
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        home_dist = round(haversine(HOME_LAT, HOME_LON, lat, lon), 1) if lat and lon else None
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
    return result[:TOP_N]

# ── HTML-Hilfsfunktionen ───────────────────────────────────────────────────────
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
    "oil!":       "#00555",
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

def brand_color(name: str) -> str:
    n = name.lower()
    for key, color in BRAND_COLORS.items():
        if key in n:
            return color
    return "#4f46e5"

def brand_logo_url(name: str) -> str | None:
    n = name.lower()
    # Direct high-quality logos for iconic brands
    if "eni" in n:
        return "https://upload.wikimedia.org/wikipedia/de/thumb/8/8a/Logo_ENI.svg/1280px-Logo_ENI.svg.png"
    if "bp" in n:
        return "https://1000logos.net/wp-content/uploads/2016/10/BP-Logo.png"
    
    for key, domain in BRAND_DOMAINS.items():
        if key in n:
            return f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
    return None

def brand_initial(name: str) -> str:
    words = name.strip().split()
    if not words:
        return "?"
    return (words[0][0] + (words[1][0] if len(words) > 1 else words[0][1])).upper()

def open_badge(is_open) -> str:
    if is_open is True:
        return '<span class="badge open">Offen</span>'
    if is_open is False:
        return '<span class="badge closed">Geschlossen</span>'
    return ""

def savings_badge(price: float, max_price: float) -> str:
    diff = max_price - price
    if diff <= 0:
        return '<span class="savings maxprice">Höchstpreis</span>'
    return f'<span class="savings">− {diff:.3f} €</span>'

def price_bar(price: float, min_price: float, max_price: float) -> str:
    span = max_price - min_price
    pct  = int(100 * (price - min_price) / span) if span else 0
    hue  = int(120 * (1 - pct / 100))
    return (
        f'<div class="price-bar-wrap">'
        f'<div class="price-bar" style="width:{max(4,pct)}%; background:hsl({hue},70%,45%)"></div>'
        f'</div>'
    )

def rank_label(rank: int, price: float, min_price: float, second_price: float) -> tuple[str, str]:
    if price == min_price:
        return "rank-gold", '<span class="medal gold">🥇 Günstigste</span>'
    if price == second_price:
        return "rank-silver", '<span class="medal silver">🥈 2. Preis</span>'
    return "", f'<span class="rank-num">#{rank}</span>'

def marker_color(rank: int, total: int) -> str:
    """Green → yellow → red gradient across ranks."""
    hue = int(120 * (1 - (rank - 1) / max(total - 1, 1)))
    return f"hsl({hue},80%,45%)"

def render_mini_card(s: dict, rank: int, min_p: float, second_p: float, fkey: str) -> str:
    color             = brand_color(s["name"])
    logo_url          = brand_logo_url(s["name"])
    is_eni            = "eni" in s["name"].lower()
    is_bp             = "bp" in s["name"].lower()
    rclass, rank_html = rank_label(rank, s["price"], min_p, second_p)
    home_dist_str = f"{s['home_dist']} km" if s["home_dist"] else "–"
    if logo_url:
        extra_cls   = 'brand-eni' if is_eni else ('brand-bp' if is_bp else '')
        avatar_html = (f'<div class="mini-avatar avatar-logo {extra_cls}" style="--brand:{color}">'
                       f'<img src="{logo_url}" alt="{s["name"]}"'
                       f' onerror="this.parentElement.innerHTML=\'<span>{brand_initial(s["name"])}</span>\'">'
                       f'</div>')
    else:
        avatar_html = f'<div class="mini-avatar" style="background:{color}">{brand_initial(s["name"])}</div>'
    return f"""<div class="mini-card {rclass}" onclick="document.getElementById('card-{fkey}-{rank}').scrollIntoView({{behavior:'smooth',block:'center'}})">
  <div class="mini-top">{avatar_html}<span class="mini-rank">{rank_html}</span><span class="mini-badges">{open_badge(s['open'])}<span class="dist mini-dist" id="mdist-{fkey}-{rank}">📍 {home_dist_str}</span></span></div>
  <div class="mini-name">{s['name']}</div>
  <a class="mini-address address" onclick="focusMarker('{fkey}', {rank}); return false;" href="#">
    <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24"
         fill="none" stroke="currentColor" stroke-width="2.2">
      <path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z"/>
      <circle cx="12" cy="10" r="3"/>
    </svg>
    {s['street']}, {s['zip']} {s['city']}
  </a>
  <div class="mini-footer">
    <div class="mini-price">{s['price']:.3f} <small>€/L</small></div>
    <a class="map-btn route-btn mini-route" id="mroute-{fkey}-{rank}"
       href="https://www.google.com/maps/dir/?api=1&destination={s['lat']},{s['lon']}&travelmode=driving"
       target="_blank" rel="noopener" onclick="event.stopPropagation()">
      <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24"
           fill="none" stroke="currentColor" stroke-width="2">
        <polygon points="3 11 22 2 13 21 11 13 3 11"/>
      </svg>
      Route
    </a>
  </div>
</div>"""

def render_card(s: dict, rank: int, min_p: float, max_p: float, second_p: float, fkey: str) -> str:
    color           = brand_color(s["name"])
    logo_url        = brand_logo_url(s["name"])
    is_eni          = "eni" in s["name"].lower()
    is_bp           = "bp" in s["name"].lower()
    rclass, rank_html = rank_label(rank, s["price"], min_p, second_p)
    home = f'<span class="dist home-dist" id="dist-{fkey}-{rank}">📍 {s["home_dist"]} km</span>' if s["home_dist"] else f'<span class="dist home-dist" id="dist-{fkey}-{rank}">📍 –</span>'

    if logo_url:
        extra_cls = 'brand-eni' if is_eni else ('brand-bp' if is_bp else '')
        avatar_html = f"""<div class="avatar avatar-logo {extra_cls}" style="--brand:{color}">
          <img src="{logo_url}" alt="{s['name']}"
               onerror="this.parentElement.innerHTML='<span>{brand_initial(s["name"])}</span>'">
        </div>"""
    else:
        avatar_html = f'<div class="avatar" style="background:{color}">{brand_initial(s["name"])}</div>'

    return f"""
    <article class="card {rclass}" id="card-{fkey}-{rank}" style="--brand:{color}"
             data-lat="{s['lat']}" data-lon="{s['lon']}" data-rank="{rank}">
      <div class="card-header">
        {avatar_html}
        <div class="card-meta">
          {rank_html}
          {open_badge(s['open'])}
          {home}
        </div>
      </div>
      <div class="card-body">
        <h2 class="station-name">{s['name']}</h2>
        <a class="address" onclick="focusMarker('{fkey}', {rank}); return false;" href="#">
          <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24"
               fill="none" stroke="currentColor" stroke-width="2.2">
            <path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z"/>
            <circle cx="12" cy="10" r="3"/>
          </svg>
          {s['street']}, {s['zip']} {s['city']}
        </a>
      </div>
      <div class="card-footer">
        <div class="price-block">
          <div class="price-row">
            <span class="price">{s['price']:.3f} <small>€/L</small></span>
            {savings_badge(s['price'], max_p)}
          </div>
          {price_bar(s['price'], min_p, max_p)}
        </div>
        <div class="btn-group">
          <a class="map-btn route-btn" id="route-{fkey}-{rank}"
             href="https://www.google.com/maps/dir/?api=1&destination={s['lat']},{s['lon']}&travelmode=driving"
             target="_blank" rel="noopener">
            <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24"
                 fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="3 11 22 2 13 21 11 13 3 11"/>
            </svg>
            Route
          </a>
        </div>
      </div>
    </article>"""

def build_map_js(stations: list[dict], fkey: str) -> str:
    total = len(stations)
    markers = []
    for i, s in enumerate(stations):
        rank  = i + 1
        color = marker_color(rank, total)
        label = rank
        dist_str = f"<br>📍 {s['home_dist']} km ab {HOME_NAME}" if s.get("home_dist") else ""
        popup = (
            f"<b>#{rank} {s['name']}</b><br>"
            f"{s['street']}, {s['zip']} {s['city']}<br>"
            f"<span style='font-size:1.2em;font-weight:700'>{s['price']:.3f} €/L</span>"
            f"{dist_str}"
        )
        markers.append(
            f"addMarker({json.dumps(fkey)}, {s['lat']}, {s['lon']}, {json.dumps(popup)}, "
            f"{json.dumps(color)}, {label}, {rank});"
        )
    return "\n    ".join(markers)

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

def generate_html(stations_sup: list[dict], stations_die: list[dict], fetched_at: str) -> str:
    st_sup = _stats(stations_sup)
    st_die = _stats(stations_die)
    cards_sup  = "\n".join(render_card(s, i+1, st_sup["min_p"], st_sup["max_p"], st_sup["second_p"], "sup") for i, s in enumerate(stations_sup))
    cards_die  = "\n".join(render_card(s, i+1, st_die["min_p"], st_die["max_p"], st_die["second_p"], "die") for i, s in enumerate(stations_die))
    top4_sup   = "\n".join(render_mini_card(s, i+1, st_sup["min_p"], st_sup["second_p"], "sup") for i, s in enumerate(stations_sup[:4]))
    top4_die   = "\n".join(render_mini_card(s, i+1, st_die["min_p"], st_die["second_p"], "die") for i, s in enumerate(stations_die[:4]))
    map_js_sup = build_map_js(stations_sup, "sup")
    map_js_die = build_map_js(stations_die, "die")
    all_stations = stations_sup  # for map center
    clat = sum(s["lat"] for s in all_stations) / len(all_stations)
    clon = sum(s["lon"] for s in all_stations) / len(all_stations)
    # backward-compat aliases used in the template below
    stations = stations_sup
    min_p, max_p, avg, span = st_sup["min_p"], st_sup["max_p"], st_sup["avg"], st_sup["span"]

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>AlterlaaTanken Wien – Günstigste Tankstellen</title>

  <meta name="description" content="Aktuelle Spritpreise rund um Alt-Erlaa in Wien. Günstigste Tankstellen im Umkreis der Hochhäuser Alterlaa im Preisvergleich." />
  <meta name="keywords" content="Tanken, Benzinpreise, Wien, Alterlaa, Alt-Erlaa, E5, Super 95, Diesel, Liesing, Meidling, Favoriten, billig tanken" />

  <meta property="og:title" content="AlterlaaTanken Wien – Günstigste Tankstellen" />
  <meta property="og:description" content="Günstigste Tankstellen rund um Alt-Erlaa Wien. Echtzeit-Preise von E-Control." />
  <meta property="og:image" content="screenshots/preview.png" />
  <meta property="og:type" content="website" />
  <meta name="twitter:card" content="summary_large_image" />

  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
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
      <h1>⛽ AlterlaaTanken Wien</h1>
      <div class="fuel-toggle">
        <button id="btn-sup" class="fuel-btn active" onclick="switchFuel('sup')">⛽ Benzin E5</button>
        <button id="btn-die" class="fuel-btn" onclick="switchFuel('die')">🛢 Diesel</button>
      </div>
      <p class="sub" id="fuel-sub-sup">Top {st_sup["count"]} gemeldete E5 · Super 95 · Umkreis Alt-Erlaa Wien · Luftlinie ab {HOME_NAME}</p>
      <p class="sub" id="fuel-sub-die" style="display:none">Top {st_die["count"]} gemeldete Diesel · Umkreis Alt-Erlaa Wien · Luftlinie ab {HOME_NAME}</p>
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
    <div class="stats" id="stats-die" style="display:none">
      <div class="stat"><div class="val">{st_die["min_p"]:.3f} €</div><div class="lbl">Günstigster Preis</div></div>
      <div class="stat"><div class="val neu">{st_die["avg"]:.3f} €</div><div class="lbl">Ø Top {st_die["count"]}</div></div>
      <div class="stat"><div class="val hi">{st_die["max_p"]:.3f} €</div><div class="lbl">Tageshöchstpreis</div></div>
      <div class="stat"><div class="val">{st_die["span"]:.3f} €</div><div class="lbl">Max. Ersparnis</div></div>
    </div>
  </div>
  <div id="map"></div>
  <div class="top4-panel">
    <div class="top4-label">Top 4</div>
    <div id="top4-sup" class="top4-grid">
{top4_sup}
    </div>
    <div id="top4-die" class="top4-grid" style="display:none">
{top4_die}
    </div>
  </div>
</div>

<main class="grid" id="grid-sup">
{cards_sup}
</main>
<main class="grid" id="grid-die" style="display:none">
{cards_die}
</main>

<footer class="pf">
  Datenquelle: <a href="https://www.spritpreisrechner.at" target="_blank">E-Control Austria</a>
  · Karte: <a href="https://leafletjs.com" target="_blank">Leaflet</a> / <a href="https://www.openstreetmap.org" target="_blank">OpenStreetMap</a>
  · Preise in €/Liter inkl. MwSt. · Alle Angaben ohne Gewähr
</footer>

<script>
  // ── Leaflet Map ───────────────────────────────────────────────────────────
  const map = L.map('map', {{ zoomControl: true }}).setView([{clat:.4f}, {clon:.4f}], 11);

  L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png', {{
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> © <a href="https://carto.com">CARTO</a>',
    subdomains: 'abcd', maxZoom: 19
  }}).addTo(map);

  const allMarkers = {{ sup: {{}}, die: {{}} }};
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
    allMarkers[fkey][rank] = m;  // always store; initFuel() adds to map

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
  // Init from localStorage or system
  (function() {{
    const saved = localStorage.getItem('theme') || 'system';
    setTheme(saved);
  }})();

  // ── Geolocation ──────────────────────────────────────────────────────────
  const stationCoords = {{
    sup: {{{", ".join(f'{i+1}: [{s["lat"]}, {s["lon"]}]' for i, s in enumerate(stations_sup))}}},
    die: {{{", ".join(f'{i+1}: [{s["lat"]}, {s["lon"]}]' for i, s in enumerate(stations_die))}}}
  }};

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
    // Update distance badges and route links for both fuel sets
    for (const fkey of ['sup', 'die']) {{
      for (const [rank, coords] of Object.entries(stationCoords[fkey])) {{
        const distEl = document.getElementById('dist-' + fkey + '-' + rank);
        if (distEl) distEl.textContent = '📍 ' + haversineJS(lat, lon, coords[0], coords[1]).toFixed(1) + ' km';
        const routeEl = document.getElementById('route-' + fkey + '-' + rank);
        if (routeEl) routeEl.href = `https://www.google.com/maps/dir/?api=1&origin=${{lat}},${{lon}}&destination=${{coords[0]}},${{coords[1]}}&travelmode=driving`;
        const mRouteEl = document.getElementById('mroute-' + fkey + '-' + rank);
        if (mRouteEl) mRouteEl.href = `https://www.google.com/maps/dir/?api=1&origin=${{lat}},${{lon}}&destination=${{coords[0]}},${{coords[1]}}&travelmode=driving`;
        const mDistEl = document.getElementById('mdist-' + fkey + '-' + rank);
        if (mDistEl) mDistEl.textContent = '📍 ' + haversineJS(lat, lon, coords[0], coords[1]).toFixed(1) + ' km';
      }}
    }}
    // Update home marker on map
    if (homeMarker) map.removeLayer(homeMarker);
    const label = isLive ? 'Ihr Standort (GPS)' : '{HOME_NAME} (Fallback)';
    homeMarker = L.marker([lat, lon], {{
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

    // Update pill
    const pill = document.getElementById('geo-pill');
    if (pill) {{
      pill.textContent = isLive ? '📱 GPS-Standort aktiv' : '🏠 Fallback: {HOME_NAME}';
      pill.style.color = isLive ? '#22c55e' : '#a78bfa';
    }}
  }}

  if (navigator.geolocation) {{
    navigator.geolocation.getCurrentPosition(
      pos => updateWithLocation(pos.coords.latitude, pos.coords.longitude, true),
      ()  => updateWithLocation({HOME_LAT}, {HOME_LON}, false),
      {{ timeout: 8000 }}
    );
  }} else {{
    updateWithLocation({HOME_LAT}, {HOME_LON}, false);
  }}

  // ── Rebstein Fallback-Marker (wird bei GPS ersetzt) ───────────────────────
  // (homeMarker wird durch updateWithLocation gesetzt)
  updateWithLocation({HOME_LAT}, {HOME_LON}, false); // initial render

  // Register all markers (none added to map yet)
  {map_js_sup}
  {map_js_die}

  // Properly initialize fuel state from localStorage (handles all UI + markers)
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
</script>

</body>
</html>"""

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    fetched_at = datetime.now().strftime("%d.%m.%Y %H:%M Uhr")

    data_sup    = fetch_stations("SUP")
    stations_sup = process(data_sup, "SUP")
    data_die    = fetch_stations("DIE")
    stations_die = process(data_die, "DIE")

    if not stations_sup and not stations_die:
        print("Keine Tankstellen mit Preisdaten gefunden.", file=sys.stderr)
        sys.exit(1)

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

    html = generate_html(stations_sup, stations_die, fetched_at)
    OUTPUT_NEW.write_text(html, encoding="utf-8")
    OUTPUT_NEW.rename(OUTPUT)   # atomic swap – kein halb-fertiges index.html
    print(f"\n✅  HTML gespeichert → {OUTPUT.resolve()}")
