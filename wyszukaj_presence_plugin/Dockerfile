FROM debian:bookworm-slim

COPY wyszukaj /wyszukaj
COPY run.sh /run.sh

RUN chmod +x /wyszukaj /run.sh
# RUN chmod +x /run.sh

CMD ["/run.sh"]
