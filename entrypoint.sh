#!/bin/sh
set -e

# Clear logfile at startup to prevent unbounded growth
> /var/log/billigtanken.log

echo "⛽  BilligTanken startet …"

# Einmal sofort ausführen – damit beim Start gleich eine index.html vorhanden ist
# Startup logs redirected to /dev/null to prevent logfile bloat
# "|| true": ein Fehler in EINER Region (z.B. externe API down) darf wegen "set -e"
# nicht den kompletten Container/Apache-Start verhindern (siehe Ausfall 15./16.08.,
# als die Tankerkönig-API down war und dadurch die ganze Seite nicht mehr startete)
WEB_ROOT=/var/www/localhost/htdocs python3 /app/billigtanken-alterlaa.py > /dev/null 2>&1 || echo "WARNUNG: alterlaa fehlgeschlagen, überspringe"
WEB_ROOT=/var/www/localhost/htdocs python3 /app/billigtanken-innsbruck.py > /dev/null 2>&1 || echo "WARNUNG: innsbruck fehlgeschlagen, überspringe"
WEB_ROOT=/var/www/localhost/htdocs python3 /app/billigtanken-vorarlberg.py > /dev/null 2>&1 || echo "WARNUNG: vorarlberg fehlgeschlagen, überspringe"
WEB_ROOT=/var/www/localhost/htdocs python3 /app/billigtanken-schaerding.py > /dev/null 2>&1 || echo "WARNUNG: schaerding fehlgeschlagen, überspringe"
WEB_ROOT=/var/www/localhost/htdocs python3 /app/billigtanken-ffb.py > /dev/null 2>&1 || echo "WARNUNG: ffb fehlgeschlagen, überspringe"

# Cron im Hintergrund
crond

# Apache im Vordergrund (hält den Container am Leben)
exec httpd -D FOREGROUND
