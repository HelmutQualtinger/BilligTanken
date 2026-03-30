FROM alpine:3.21

# py3-requests aus apk → kein pip nötig, kleineres Image
RUN apk add --no-cache \
      python3 \
      py3-requests \
      apache2 \
      dcron \
      tzdata \
 && mkdir -p /var/www/localhost/htdocs /run/apache2 \
 && echo "ServerName localhost" >> /etc/apache2/httpd.conf

COPY index.html                 /var/www/localhost/htdocs/index.html
COPY webcam-vorarlberg.html     /var/www/localhost/htdocs/webcam-vorarlberg.html
COPY webcam-tirol.html          /var/www/localhost/htdocs/webcam-tirol.html
COPY webcam-wien.html           /var/www/localhost/htdocs/webcam-wien.html
COPY webcam-schaerding.html     /var/www/localhost/htdocs/webcam-schaerding.html
COPY billigtanken_lib.py        /app/billigtanken_lib.py
COPY billigtanken-alterlaa.py   /app/billigtanken-alterlaa.py
COPY billigtanken-innsbruck.py  /app/billigtanken-innsbruck.py
COPY billigtanken-vorarlberg.py /app/billigtanken-vorarlberg.py
COPY billigtanken-schaerding.py /app/billigtanken-schaerding.py
COPY billigtanken-ffb.py        /app/billigtanken-ffb.py
COPY entrypoint.sh   /entrypoint.sh

# Cron: each hour at :00, :15, :30, :45, :48
RUN printf ' 0 * * * * WEB_ROOT=/var/www/localhost/htdocs python3 /app/billigtanken-alterlaa.py    >> /var/log/billigtanken.log 2>&1\n' \
           '15 * * * * WEB_ROOT=/var/www/localhost/htdocs python3 /app/billigtanken-innsbruck.py   >> /var/log/billigtanken.log 2>&1\n' \
           '30 * * * * WEB_ROOT=/var/www/localhost/htdocs python3 /app/billigtanken-vorarlberg.py  >> /var/log/billigtanken.log 2>&1\n' \
           '45 * * * * WEB_ROOT=/var/www/localhost/htdocs python3 /app/billigtanken-schaerding.py  >> /var/log/billigtanken.log 2>&1\n' \
           '48 * * * * WEB_ROOT=/var/www/localhost/htdocs python3 /app/billigtanken-ffb.py         >> /var/log/billigtanken.log 2>&1\n' \
      > /etc/crontabs/root \
 && chmod +x /entrypoint.sh

ENV TZ=Europe/Vienna

EXPOSE 80

CMD ["/entrypoint.sh"]
