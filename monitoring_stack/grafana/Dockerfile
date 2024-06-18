FROM grafana/grafana:latest

COPY ./grafana.ini /etc/grafana/grafana.ini

COPY ./entrypoint.sh .

RUN rm -rf /var/lib/grafana/.init

ENTRYPOINT ["sh", "./entrypoint.sh"]