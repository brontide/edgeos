import websocket
import ssl
from edgeos import edgeos_webstream, edgeos_web
from time import sleep

from secret import edgeos_url,username,password

s = edgeos_web(edgeos_url, username=username,password=password, verify=False)
s.login()
s.post(edgeos_url+'/api/auth.json', json={'username':username, 'password': password})

print("Sleeping 5 to make sure the session id {} is in the filesystem".format(s.session_id))
sleep(5)

ws = websocket.create_connection(s.wsurl, sslopt={"cert_reqs": ssl.CERT_NONE}, origin=s._endpoint, timeout=60, cookie=s.cookies_as_str())
ews = edgeos_webstream(ws,s.session_id)
print(ews.status)
print(ews.subscribe())
while True:
    x = ews.next()
    print(x)

