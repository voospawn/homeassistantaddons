#!/bin/sh

set -e

# cd /data

while true
do
    # echo "========================================"
    # echo "Starting network scan..."
    # echo "========================================"

    /config/custom-components/wyszukaj_presence/wyszukaj

    # echo
    # echo "Scan finished."
    # echo "Waiting 5 minutes..."
    # echo

    sleep 300
done
