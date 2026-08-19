FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY wyszukaj /wyszukaj
COPY run.sh /run.sh

RUN g++ -O3 /wyszukaj.cpp -o /wyszukaj && \
    chmod +x /wyszukaj /run.sh && \
    rm /wyszukaj.cpp

# RUN chmod +x /wyszukaj /run.sh
# RUN chmod +x /run.sh

RUN apt-get purge -y g++ build-essential && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

CMD ["/run.sh"]
