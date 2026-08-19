#!/bin/sh

set -e

# cd /data

while true
do
    # echo "========================================"
    # echo "Starting network scan..."
    # echo "========================================"

    rm /devices.json
    cp /config/custom_components/wyszukaj_presence/devices.json /devices.json

    /wyszukaj

    rm /config/custom_components/wyszukaj_presence/wynik.json
    cp /wynik.json /config/custom_components/wyszukaj_presence/wynik.json

    # echo
    # echo "Scan finished."
    # echo "Waiting 5 minutes..."
    # echo

    sleep 300
done
