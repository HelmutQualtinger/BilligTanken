#!/bin/sh
set -e

echo "⛽  BilligTanken startet …"

# Einmal sofort ausführen – damit beim Start gleich eine index.html vorhanden ist
WEB_ROOT=/var/www/localhost/htdocs python3 /app/billigtanken-alterlaa.py
WEB_ROOT=/var/www/localhost/htdocs python3 /app/billigtanken-innsbruck.py
WEB_ROOT=/var/www/localhost/htdocs python3 /app/billigtanken-vorarlberg.py
WEB_ROOT=/var/www/localhost/htdocs python3 /app/billigtanken-schaerding.py
WEB_ROOT=/var/www/localhost/htdocs python3 /app/billigtanken-ffb.py

# Cron im Hintergrund
crond

# Apache im Vordergrund (hält den Container am Leben)
exec httpd -D FOREGROUND
