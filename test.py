from edgeos import edgeos_webstream, edgeos_web
from time import sleep
from websocket._exceptions import WebSocketProtocolException

from secret import edgeos_url,username,password

s = edgeos_web(edgeos_url, username=username,password=password, verify=False)

#print(s.dhcp_leases())
s.login()
#usg_token = ""
#try:
#    out = s.post(edgeos_url+'/api/auth.json', json={'username':username, 'password': password})
#    usg_token = out.json()['token']
#except:
#    pass 

#print("Sleeping 5 to make sure the session id {} is in the filesystem".format(s.session_id))
#sleep(5)

while True:
    try:
        x = ews.next()
        #print("I")
    except (WebSocketProtocolException, NameError) as e:
        if not s.sys_info():
            s.login()
        print(type(e))
        ews = s.create_websocket()
        print(ews.status)
        print(ews.subscribe(subs=['system-stats', 'interfaces']))

