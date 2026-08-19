#include <linux/if_ether.h>
#include <netdb.h>
#include <arpa/inet.h>
#include <ifaddrs.h>
#include <net/if.h>
#include <netpacket/packet.h>

#include <sys/ioctl.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cstring>
#include <string>
#include <vector>
#include <set>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <unordered_map>

using namespace std;


struct urzadzenie {
    string name;
    string mac;
};

struct wyn {
    string name;
    bool isIt;
};


#pragma pack(push, 1)

struct arp_header {
    uint16_t htype;
    uint16_t ptype;
    uint8_t  hlen;
    uint8_t  plen;
    uint16_t oper;

    uint8_t sha[6];
    uint8_t spa[4];
    uint8_t tha[6];
    uint8_t tpa[4];
};

struct arp_packet {
    uint8_t dst_mac[6];
    uint8_t src_mac[6];

    uint16_t ethertype;

    arp_header arp;
};

#pragma pack(pop)


static string mac_to_string(const uint8_t* mac)
{
    char buf[18];

    snprintf(
        buf,
        sizeof(buf),
        "%02x:%02x:%02x:%02x:%02x:%02x",
        mac[0], mac[1], mac[2],
        mac[3], mac[4], mac[5]
    );

    return string(buf);
}


vector<urzadzenie> znajdz_urzadzenia()
{
    vector<urzadzenie> wynik;
    set<string> znalezione_mac;

    ifaddrs* interfaces = nullptr;

    if (getifaddrs(&interfaces) != 0)
    {
        perror("getifaddrs");
        return wynik;
    }

    for (ifaddrs* i = interfaces;
         i != nullptr;
         i = i->ifa_next)
    {
        if (!i->ifa_addr || !i->ifa_netmask)
            continue;

        // Tylko IPv4
        if (i->ifa_addr->sa_family != AF_INET)
            continue;

        // Interfejs musi być aktywny
        if (!(i->ifa_flags & IFF_UP))
            continue;

        // Pomijamy loopback
        if (i->ifa_flags & IFF_LOOPBACK)
            continue;

        string interface_name = i->ifa_name;

        sockaddr_in* addr =
            reinterpret_cast<sockaddr_in*>(i->ifa_addr);

        sockaddr_in* mask =
            reinterpret_cast<sockaddr_in*>(i->ifa_netmask);

        uint32_t local_ip =
            addr->sin_addr.s_addr;

        uint32_t netmask =
            mask->sin_addr.s_addr;

        char ip_buffer[INET_ADDRSTRLEN];

        if (!inet_ntop(
                AF_INET,
                &local_ip,
                ip_buffer,
                sizeof(ip_buffer)))
        {
            continue;
        }

        // cout << "\n====================================\n";
        // cout << "Interfejs: " << interface_name << '\n';
        // cout << "Lokalne IP: " << ip_buffer << '\n';


        // --------------------------------------------------------
        // RAW SOCKET
        // --------------------------------------------------------

        int sock = socket(
            AF_PACKET,
            SOCK_RAW,
            htons(ETH_P_ARP)
        );

        if (sock < 0)
        {
            perror("socket");
            continue;
        }


        // --------------------------------------------------------
        // Pobierz MAC interfejsu
        // --------------------------------------------------------

        ifreq ifr {};

        strncpy(
            ifr.ifr_name,
            interface_name.c_str(),
            IFNAMSIZ - 1
        );

        if (ioctl(sock, SIOCGIFHWADDR, &ifr) < 0)
        {
            perror("SIOCGIFHWADDR");
            close(sock);
            continue;
        }

        uint8_t local_mac[6];

        memcpy(
            local_mac,
            ifr.ifr_hwaddr.sa_data,
            6
        );


        // --------------------------------------------------------
        // Pobierz indeks interfejsu
        // --------------------------------------------------------

        ifreq ifindex_req {};

        strncpy(
            ifindex_req.ifr_name,
            interface_name.c_str(),
            IFNAMSIZ - 1
        );

        if (ioctl(
                sock,
                SIOCGIFINDEX,
                &ifindex_req) < 0)
        {
            perror("SIOCGIFINDEX");
            close(sock);
            continue;
        }

        int ifindex =
            ifindex_req.ifr_ifindex;


        // --------------------------------------------------------
        // Oblicz sieć
        // --------------------------------------------------------

        uint32_t network =
            local_ip & netmask;

        uint32_t broadcast =
            network | ~netmask;

        uint32_t first_host =
            ntohl(network) + 1;

        uint32_t last_host =
            ntohl(broadcast) - 1;


        char network_buffer[INET_ADDRSTRLEN];

        inet_ntop(
            AF_INET,
            &network,
            network_buffer,
            sizeof(network_buffer)
        );

        cout << "Skanowana siec: "
             << network_buffer
             << '\n';


        // --------------------------------------------------------
        // Wyślij ARP request
        // --------------------------------------------------------

        for (
            uint32_t host = first_host;
            host <= last_host;
            ++host)
        {
            uint32_t target_ip =
                htonl(host);

            arp_packet packet {};


            // Ethernet

            memset(
                packet.dst_mac,
                0xff,
                6
            );

            memcpy(
                packet.src_mac,
                local_mac,
                6
            );

            packet.ethertype =
                htons(ETH_P_ARP);


            // ARP

            packet.arp.htype =
                htons(1);

            packet.arp.ptype =
                htons(ETH_P_IP);

            packet.arp.hlen = 6;
            packet.arp.plen = 4;

            packet.arp.oper =
                htons(1);


            memcpy(
                packet.arp.sha,
                local_mac,
                6
            );

            memcpy(
                packet.arp.spa,
                &local_ip,
                4
            );

            memset(
                packet.arp.tha,
                0,
                6
            );

            memcpy(
                packet.arp.tpa,
                &target_ip,
                4
            );


            sockaddr_ll destination {};

            destination.sll_family =
                AF_PACKET;

            destination.sll_ifindex =
                ifindex;

            destination.sll_halen =
                6;

            memset(
                destination.sll_addr,
                0xff,
                6
            );


            if (sendto(
                    sock,
                    &packet,
                    sizeof(packet),
                    0,
                    reinterpret_cast<sockaddr*>(&destination),
                    sizeof(destination)
                ) < 0)
            {
                perror("sendto");
            }
        }


        // --------------------------------------------------------
        // Czekamy na odpowiedzi
        // --------------------------------------------------------

        timeval timeout {};

        timeout.tv_sec = 2;
        timeout.tv_usec = 0;

        setsockopt(
            sock,
            SOL_SOCKET,
            SO_RCVTIMEO,
            &timeout,
            sizeof(timeout)
        );


        while (true)
        {
            arp_packet packet {};

            ssize_t size =
                recv(
                    sock,
                    &packet,
                    sizeof(packet),
                    0
                );

            if (size < 0)
                break;

            if (size <
                static_cast<ssize_t>(
                    sizeof(arp_packet)))
            {
                continue;
            }


            if (ntohs(packet.ethertype) !=
                ETH_P_ARP)
            {
                continue;
            }


            if (ntohs(packet.arp.oper) != 2)
                continue;


            string mac =
                mac_to_string(packet.arp.sha);


            // Nie dodawaj tego samego urządzenia
            // znalezionego na kilku interfejsach.

            if (znalezione_mac.contains(mac))
                continue;

            znalezione_mac.insert(mac);


            // ----------------------------------------------------
            // Reverse DNS
            // ----------------------------------------------------

            string name = mac;

            sockaddr_in addr {};

            addr.sin_family =
                AF_INET;

            memcpy(
                &addr.sin_addr,
                packet.arp.spa,
                4
            );


            char hostname[NI_MAXHOST];


            if (getnameinfo(
                    reinterpret_cast<sockaddr*>(&addr),
                    sizeof(addr),
                    hostname,
                    sizeof(hostname),
                    nullptr,
                    0,
                    NI_NAMEREQD
                ) == 0)
            {
                name = hostname;
            }


            cout << "Znaleziono: "
                 << name
                 << " "
                 << mac
                 << '\n';


            wynik.push_back({
                name,
                mac
            });
        }


        close(sock);
    }

    freeifaddrs(interfaces);

    return wynik;
}


// ================================================================
// ODCZYT JSON
// ================================================================

vector<urzadzenie> odczytaj_json(const string& sciezka)
{
    ifstream plik(sciezka);


    if (!plik)
        throw runtime_error(
            "Nie mozna otworzyc pliku: " + sciezka
        );


    string json(
        (istreambuf_iterator<char>(plik)),
        istreambuf_iterator<char>()
    );


    vector<urzadzenie> wynik;

    size_t pos = 0;


    while (true)
    {
        size_t name_pos =
            json.find("\"name\"", pos);


        if (name_pos == string::npos)
            break;


        size_t name_colon =
            json.find(':', name_pos);


        if (name_colon == string::npos)
            throw runtime_error(
                "Niepoprawny JSON: name"
            );


        size_t name_start =
            json.find('"', name_colon);


        if (name_start == string::npos)
            throw runtime_error(
                "Niepoprawny JSON: name"
            );


        size_t name_end =
            json.find('"', name_start + 1);


        if (name_end == string::npos)
            throw runtime_error(
                "Niepoprawny JSON: name"
            );


        string name =
            json.substr(
                name_start + 1,
                name_end - name_start - 1
            );


        size_t mac_pos =
            json.find("\"mac\"", name_end);


        if (mac_pos == string::npos)
            throw runtime_error(
                "Niepoprawny JSON: mac"
            );


        size_t mac_colon =
            json.find(':', mac_pos);


        if (mac_colon == string::npos)
            throw runtime_error(
                "Niepoprawny JSON: mac"
            );


        size_t mac_start =
            json.find('"', mac_colon);


        if (mac_start == string::npos)
            throw runtime_error(
                "Niepoprawny JSON: mac"
            );


        size_t mac_end =
            json.find('"', mac_start + 1);


        if (mac_end == string::npos)
            throw runtime_error(
                "Niepoprawny JSON: mac"
            );


        string mac =
            json.substr(
                mac_start + 1,
                mac_end - mac_start - 1
            );


        wynik.push_back({
            name,
            mac
        });


        pos = mac_end + 1;
    }


    return wynik;
}


// ================================================================
// ZAPIS WYNIKÓW
// ================================================================

void zapisz_wyniki(
    const string& sciezka,
    const vector<wyn>& wyniki
)
{
    ofstream plik(sciezka);


    if (!plik)
        throw runtime_error(
            "Nie mozna otworzyc pliku do zapisu: " + sciezka
        );


    plik << "[\n";


    for (size_t i = 0; i < wyniki.size(); ++i)
    {
        plik
            << "    { \"name\": \""
            << wyniki[i].name
            << "\", \"athome\": "
            << (wyniki[i].isIt ? 1 : 0)
            << " }";


        if (i + 1 < wyniki.size())
            plik << ",";

        plik << "\n";
    }


    plik << "]\n";
}

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
