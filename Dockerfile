FROM alpine:3.21

# py3-requests aus apk → kein pip nötig, kleineres Image
RUN apk add --no-cache \
      python3 \
      py3-requests \
      apache2 \
      dcron \
 && mkdir -p /var/www/localhost/htdocs /run/apache2 \
 && echo "ServerName localhost" >> /etc/apache2/httpd.conf

COPY billigtanken.py /app/billigtanken.py
COPY entrypoint.sh   /entrypoint.sh

# Cron: jede volle Stunde
RUN printf '0 * * * * WEB_ROOT=/var/www/localhost/htdocs python3 /app/billigtanken.py >> /var/log/billigtanken.log 2>&1\n' \
      > /etc/crontabs/root \
 && chmod +x /entrypoint.sh

EXPOSE 80

CMD ["/entrypoint.sh"]
