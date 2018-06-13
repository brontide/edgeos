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

ews = s.create_websocket()
print(ews.status)
print(ews.subscribe(subs=['interfaces','system-stats']))
while True:
    x = ews.next()
    print(x)

