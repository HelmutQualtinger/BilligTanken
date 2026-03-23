#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BilligTanken – Günstigste E5 Tankstellen in Vorarlberg zwischen Bregenz und Feldkirch
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
FUEL_TYPE  = "SUP"
TOP_N      = 80
_web_root  = Path(os.environ.get("WEB_ROOT", "."))
OUTPUT     = _web_root / "index.html"
OUTPUT_NEW = _web_root / "index_new.html"

# Referenzpunkt Rebstein SG, Schweiz (47°23'53"N 9°34'56"E)
HOME_LAT  = 47.3983
HOME_LON  =  9.5824
HOME_NAME = "Rebstein CH"

API_BASE = "https://api.e-control.at/sprit/1.0/search/gas-stations/by-address"
HEADERS  = {"User-Agent": "Mozilla/5.0 (compatible; BilligTanken/1.0)"}

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

# ── Daten holen ───────────────────────────────────────────────────────────────
def fetch_stations() -> list[dict]:
    print("⛽  Lade Tankstellendaten von E-Control API …")
    seen_ids: set = set()
    combined: list[dict] = []
    for lat, lon in QUERY_POINTS:
        try:
            url = (
                f"{API_BASE}?latitude={lat}&longitude={lon}"
                f"&fuelType={FUEL_TYPE}&includeClosed=false"
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

def extract_price(station: dict) -> float | None:
    for p in station.get("prices", []):
        if p.get("fuelType") == FUEL_TYPE and p.get("amount"):
            return float(p["amount"])
    return None

def in_corridor(station: dict) -> bool:
    loc = station.get("location", {})
    lat, lon = loc.get("latitude"), loc.get("longitude")
    if lat is None or lon is None:
        return False
    return LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX

def process(data: list[dict]) -> list[dict]:
    result = []
    for s in data:
        if not in_corridor(s):
            continue
        price = extract_price(s)
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
    "avanti":  "#ff6b00",
    "disk":    "#005baa",
    "diskont": "#005baa",
    "eni":     "#006db7",
    "omv":     "#e30613",
    "shell":   "#c8a800",
    "bp":      "#009a44",
    "esso":    "#003087",
    "avia":    "#e2001a",
    "oil!":    "#555",
    "baywa":   "#007db5",
    "loacker": "#6db33f",
    "gutmann": "#e87722",
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

def render_card(s: dict, rank: int, min_p: float, max_p: float, second_p: float) -> str:
    color           = brand_color(s["name"])
    logo_url        = brand_logo_url(s["name"])
    is_eni          = "eni" in s["name"].lower()
    is_bp           = "bp" in s["name"].lower()
    rclass, rank_html = rank_label(rank, s["price"], min_p, second_p)
    home = f'<span class="dist home-dist" id="dist-{rank}">📍 {s["home_dist"]} km</span>' if s["home_dist"] else f'<span class="dist home-dist" id="dist-{rank}">📍 –</span>'

    if logo_url:
        extra_cls = 'brand-eni' if is_eni else ('brand-bp' if is_bp else '')
        avatar_html = f"""<div class="avatar avatar-logo {extra_cls}" style="--brand:{color}">
          <img src="{logo_url}" alt="{s['name']}"
               onerror="this.parentElement.innerHTML='<span>{brand_initial(s["name"])}</span>'">
        </div>"""
    else:
        avatar_html = f'<div class="avatar" style="background:{color}">{brand_initial(s["name"])}</div>'

    return f"""
    <article class="card {rclass}" id="card-{rank}" style="--brand:{color}"
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
        <a class="address" onclick="focusMarker({rank}); return false;" href="#">
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
          <a class="map-btn route-btn" id="route-{rank}"
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

def build_map_js(stations: list[dict]) -> str:
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
            f"addMarker({s['lat']}, {s['lon']}, {json.dumps(popup)}, "
            f"{json.dumps(color)}, {label}, {rank});"
        )
    return "\n    ".join(markers)

def generate_html(stations: list[dict], fetched_at: str) -> str:
    prices    = sorted(set(s["price"] for s in stations))
    min_p     = prices[0]
    second_p  = prices[1] if len(prices) > 1 else prices[0]
    max_p     = stations[-1]["price"]
    avg       = sum(s["price"] for s in stations) / len(stations)
    span      = max_p - min_p
    cards     = "\n".join(render_card(s, i + 1, min_p, max_p, second_p) for i, s in enumerate(stations))
    map_js = build_map_js(stations)
    # center map on centroid of stations
    clat   = sum(s["lat"] for s in stations) / len(stations)
    clon   = sum(s["lon"] for s in stations) / len(stations)

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>BilligTanken Vorarlberg – E5 Super 95</title>
  
  <meta name="description" content="Aktuelle Benzinpreise (E5 Super 95) in Vorarlberg. Günstigste Tankstellen zwischen Bregenz und Feldkirch im Preisvergleich." />
  <meta name="keywords" content="Tanken, Benzinpreise, Vorarlberg, E5, Super 95, Bregenz, Dornbirn, Feldkirch, Lustenau, billig tanken" />
  
  <meta property="og:title" content="BilligTanken Vorarlberg – E5 Super 95" />
  <meta property="og:description" content="Günstigste Tankstellen in Vorarlberg. Echtzeit-Preise von E-Control." />
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
        --map-filter: none;
      }}
    }}

    :root {{
      --green:   #22c55e;
      --gold:    #fbbf24;
      --silver:  #94a3b8;
      --bronze:  #cd7f32;
      --r:       16px;
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

    .pill {{
      display: inline-block;
      font-size: .72rem; padding: .28rem .75rem; border-radius: 999px;
    }}
    .pill.time {{ color: var(--muted); background: var(--surf2); border: 1px solid var(--border); }}
    .pill.note {{ color: #f59e0b; background: rgba(245,158,11,.1); border: 1px solid rgba(245,158,11,.25); }}

    /* Overview row: left col + map */
    .overview {{
      display: grid;
      grid-template-columns: 260px 1fr;
      gap: 1rem;
      max-width: 1400px;
      margin: 0 auto 2rem;
      align-items: stretch;
    }}
    @media (max-width: 800px) {{
      .overview {{ grid-template-columns: 1fr; }}
    }}

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
      font-size: .78rem; color: var(--muted);
      display: flex; align-items: flex-start; gap: .32rem; line-height: 1.4;
      text-decoration: none; cursor: pointer;
    }}
    .address:hover {{ color: #60a5fa; }}
    .address:hover svg {{ stroke: #60a5fa; }}
    .address svg {{ flex-shrink: 0; margin-top: .15rem; }}

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
      <h1>⛽ BilligTanken Vorarlberg</h1>
      <p class="sub">Top {len(stations)} gemeldete E5 · Super 95 · Korridor Bregenz – Feldkirch · Luftlinie ab {HOME_NAME}</p>
      <div class="pills">
        <span class="pill time">Aktualisiert: {fetched_at}</span>
        <span class="pill note">⚠ Tageshöchstpreis aktiv</span>
        <span class="pill time" id="geo-pill" style="color:#a78bfa">🏠 Standort wird ermittelt …</span>
      </div>
    </header>
    <div class="stats">
      <div class="stat"><div class="val">{min_p:.3f} €</div><div class="lbl">Günstigster Preis</div></div>
      <div class="stat"><div class="val neu">{avg:.3f} €</div><div class="lbl">Ø Top {len(stations)}</div></div>
      <div class="stat"><div class="val hi">{max_p:.3f} €</div><div class="lbl">Tageshöchstpreis</div></div>
      <div class="stat"><div class="val">{span:.3f} €</div><div class="lbl">Max. Ersparnis</div></div>
    </div>
  </div>
  <div id="map"></div>
</div>

<main class="grid">
{cards}
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

  const markers = {{}};

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

  function addMarker(lat, lon, popup, color, label, rank) {{
    const m = L.marker([lat, lon], {{ icon: makeIcon(color, label) }})
      .addTo(map)
      .bindPopup(popup);
    markers[rank] = m;

    m.on('click', () => {{
      const card = document.getElementById('card-' + rank);
      if (card) {{
        document.querySelectorAll('.card').forEach(c => c.classList.remove('highlighted'));
        card.classList.add('highlighted');
        card.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
      }}
    }});
  }}

  function focusMarker(rank) {{
    const m = markers[rank];
    if (!m) return;
    map.setView(m.getLatLng(), 15, {{ animate: true }});
    m.openPopup();
    window.scrollTo({{ top: 0, behavior: 'smooth' }});
    document.querySelectorAll('.card').forEach(c => c.classList.remove('highlighted'));
    document.getElementById('card-' + rank)?.classList.add('highlighted');
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
  const stationCoords = {{{", ".join(f'{i+1}: [{s["lat"]}, {s["lon"]}]' for i, s in enumerate(stations))}}};

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
    // Update distance badges
    for (const [rank, coords] of Object.entries(stationCoords)) {{
      const d = haversineJS(lat, lon, coords[0], coords[1]);
      const el = document.getElementById('dist-' + rank);
      if (el) el.textContent = '📍 ' + d.toFixed(1) + ' km';
    }}
    // Update route links
    for (const [rank] of Object.entries(stationCoords)) {{
      const btn = document.getElementById('route-' + rank);
      if (btn) {{
        const coords = stationCoords[rank];
        btn.href = `https://www.google.com/maps/dir/?api=1&origin=${{lat}},${{lon}}&destination=${{coords[0]}},${{coords[1]}}&travelmode=driving`;
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

  // Draw all markers
  {map_js}
</script>

</body>
</html>"""

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    data       = fetch_stations()
    stations   = process(data)
    fetched_at = datetime.now().strftime("%d.%m.%Y %H:%M Uhr")

    if not stations:
        print("Keine Tankstellen mit Preisdaten gefunden.", file=sys.stderr)
        sys.exit(1)

    max_p = stations[-1]["price"]
    print(f"   → {len(stations)} Stationen mit gemeldeten Preisen\n")
    print(f"{'#':>2}  {'Preis':>8}  {'Ersparnis':>10}  {'Luftlinie':>10}  {'Name':<32}  {'Ort'}")
    print("─" * 85)
    for i, s in enumerate(stations, 1):
        sav  = max_p - s["price"]
        dist = f"{s['home_dist']} km" if s["home_dist"] else "–"
        print(f"{i:>2}  {s['price']:.3f} €  {'−'+f'{sav:.3f} €':>10}  {dist:>10}  {s['name']:<32}  {s['city']}")

    html = generate_html(stations, fetched_at)
    OUTPUT_NEW.write_text(html, encoding="utf-8")
    OUTPUT_NEW.rename(OUTPUT)   # atomic swap – kein halb-fertiges index.html
    print(f"\n✅  HTML gespeichert → {OUTPUT.resolve()}")
