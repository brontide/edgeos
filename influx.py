from influxdb import InfluxDBClient
from edgeos import edgeos_webstream, edgeos_web
from time import sleep

from secret import edgeos_url,username,password

s = edgeos_web(edgeos_url, username=username,password=password, verify=False)
s.login()
usg_token = ""
try:
    out = s.post(edgeos_url+'/api/auth.json', json={'username':username, 'password': password})
    usg_token = out.json()['token']
except:
    pass 

print("Sleeping 5 to make sure the session id {} is in the filesystem".format(s.session_id))
sleep(5)

default_tags = None

client = InfluxDBClient('192.168.111.20', 8086)

# END EDIT

try:
    default_tags = {
        'hostname': '192.168.111.1',
    }
except:
    print("Could not generate site default tags")

client.create_database('edgeos')
client.switch_database('edgeos')

ews = s.create_websocket()
print(ews.status)
print(ews.subscribe(subs=['interfaces','system-stats','export']))

sys_stat_fields = [ 'cpu', 'mem', 'uptime' ]

def process_system_stats(x):
    json =[{
        'measurement': 'system-stats',
        'fields': dict(
            (field_name, int(x[field_name])) for field_name in sys_stat_fields
            ),
    }]
    return json

if_fields = [
    'rx_packets', 'rx_bytes', 'rx_errors', 'rx_dropped', 
    'tx_packets', 'tx_bytes', 'tx_errors', 'tx_dropped', 

]

def process_interfaces(x):
    json = []
    for interface, data in x.items():
        temp = {
            'measurement': 'interface',
            'tags': {
                'interface': interface,
            },
            'fields': dict(
                (field_name, int(data['stats'][field_name])) for field_name in if_fields
            )
        }
        json.append(temp)
    return json

ip2mac = {}
#ip2client_hostname = {}
ip2name = {}

def process_dhcp():
    leases = s.dhcp_leases()
    for lan in leases['dhcp-server-leases'].values():
        if not lan: continue
        for ip, lease in lan.items():
            ip2mac[ip] = lease['mac']
            ip2name[ip] = lease['client-hostname']
            if ip2name[ip] == "":
                ip2name[ip] = ip
    #for ip in ip2mac:
        # proper name lookup
        # 1. Noted names in unifi
        # 2. client-hostname from lease
        # 3. ipaddress


def ip_to_mac(ip):
    if ip in ip2mac:
        return ip2mac[ip]
    process_dhcp()
    if ip in ip2mac:
        return ip2mac[ip]
    return 'UNKNOWN'

def ip_to_name(ip):
    if ip in ip2name:
        return ip2name[ip]
    process_dhcp()
    if ip in ip2name:
        return ip2name[ip]
    return ip

def process_export(x):
    json = [ {
        'measurement': 'clients',
        'fields': { 'count': len(x) }
    } ]
    for ip, data in x.items():
        mac = ip_to_mac(ip)
        name = ip_to_name(ip)
        for application, stats in data.items():
            #print(application,stats)
            temp = {
               'measurement': 'dpi',
               'tags': {
                    'name': name,
                    'mac': mac,
                    'application': application,
                },
                'fields': {
                    'rx_bytes': int(stats['rx_bytes']),
                    'tx_bytes': int(stats['tx_bytes']),
                }
            }
            json.append(temp)
    return json

while True:
    x = ews.next()
    if 'system-stats' in x:
        json = process_system_stats(x['system-stats'])
        while not client.write_points(json, tags=default_tags):
            sleep(1)
        continue
    if 'interfaces' in x:
        json = process_interfaces(x['interfaces'])
        while not client.write_points(json, tags=default_tags):
            sleep(1)
        continue
    if 'export' in x:
        json = process_export(x['export'])
        while not client.write_points(json, tags=default_tags):
            sleep(1)
        continue        
    print(x)