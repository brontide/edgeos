import websocket
import ssl
from edgeos import edgeos_webstream, edgeos_web

from secret import edgeos_url,username,password

s = edgeos_web(edgeos_url, username=username,password=password, verify=False)
s.login()

session_id = s.session_id
print(session_id)

ws = websocket.create_connection(s.wsurl, sslopt={"cert_reqs": ssl.CERT_NONE}, origin=s._endpoint, timeout=20)
ews = edgeos_webstream(ws,s.session_id)
print(ews.status)
print(ews.subscribe())
while True:
    x = ews.next()
    print(x)

