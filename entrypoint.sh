#!/bin/sh
set -e

# Clear logfile at startup to prevent unbounded growth
> /var/log/billigtanken.log

echo "⛽  BilligTanken startet …"

# Einmal sofort ausführen – damit beim Start gleich eine index.html vorhanden ist
# Startup logs redirected to /dev/null to prevent logfile bloat
WEB_ROOT=/var/www/localhost/htdocs python3 /app/billigtanken-alterlaa.py > /dev/null 2>&1
WEB_ROOT=/var/www/localhost/htdocs python3 /app/billigtanken-innsbruck.py > /dev/null 2>&1
WEB_ROOT=/var/www/localhost/htdocs python3 /app/billigtanken-vorarlberg.py > /dev/null 2>&1
WEB_ROOT=/var/www/localhost/htdocs python3 /app/billigtanken-schaerding.py > /dev/null 2>&1
WEB_ROOT=/var/www/localhost/htdocs python3 /app/billigtanken-ffb.py > /dev/null 2>&1

# Cron im Hintergrund
crond

# Apache im Vordergrund (hält den Container am Leben)
exec httpd -D FOREGROUND
