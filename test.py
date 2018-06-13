import websocket
import ssl
from edgeos import edgeos_webstream, edgeos_web

from secret import edgeos_url,username,password

s = edgeos_web(edgeos_url, username=username,password=password, verify=False)
s.login()
s.post(edgeos_url+'/api/auth.json', json={'username':username, 'password': password})

session_id = s.session_id
print(session_id)

ws = websocket.create_connection(s.wsurl, sslopt={"cert_reqs": ssl.CERT_NONE}, origin=s._endpoint, timeout=60, cookie=s.cookies_as_str())
ews = edgeos_webstream(ws,s.session_id)
print(ews.status)
print(ews.subscribe())
while True:
    x = ews.next()
    print(x)

