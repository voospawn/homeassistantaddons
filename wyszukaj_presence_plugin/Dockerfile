FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# COPY wyszukaj /wyszukaj
COPY run.sh /run.sh

RUN g++ -O2 /wyszukaj.cpp -o /wyszukaj
RUN chmod +x /wyszukaj /run.sh && \
    rm /wyszukaj.cpp

CMD ["/run.sh"]
