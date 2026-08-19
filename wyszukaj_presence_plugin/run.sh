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


int main(){
    vector<urzadzenie> telefony = odczytaj_json("/config/custom_components/wyszukaj_presence/devices.json"), urzadzenia = znajdz_urzadzenia();

    int n = telefony.size();

    unordered_map<string, bool> czyJest;
    czyJest.reserve(2 * n + 1);

    for(const urzadzenie& i : telefony){
        czyJest[i.name] = false;
        czyJest[i.mac] = false;

        // cout << i.name << ' ' << i.mac << endl;
    }

    for(const urzadzenie& i : urzadzenia){
        if(czyJest.contains(i.name)){
            czyJest[i.name] = true;
        }else if(czyJest.contains(i.mac)){
            czyJest[i.mac] = true;
        }

        // cout << i.name << ' ' << i.mac << endl;
    }

    vector<wyn> wynik(n);

    for(int i = 0; i < n; i++){
        wynik[i].name = telefony[i].name;

        wynik[i].isIt = (czyJest[telefony[i].name] or czyJest[telefony[i].mac]);
    }

    zapisz_wyniki("/config/custom_components/wyszukaj_presence/wynik.json", wynik);
}
