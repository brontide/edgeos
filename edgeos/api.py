
#
# BEGIN py2 compatibility section
#

# print function
from __future__ import print_function



# Make input() work the same
try:
    input = raw_input
except NameError:
    pass

# urllib
from future.standard_library import install_aliases
install_aliases()

#
# END py2 compatibility cruft
#

import websocket
import ssl
import requests
from datetime import datetime, timedelta
from io import StringIO
import json
from urllib.parse import urlparse,quote


def quiet():
    ''' This function turns off InsecureRequestWarnings '''
    try:
        # old vendored packages
        requests.packages.urllib3.disable_warnings() #pylint: disable=E1101
    except:
        # New way
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class edgeos_webstream:

    def __init__(self, ws, session):
        self._ws = ws
        self._session = session

    def send(self, data):
        foo = json.dumps(data,separators=(',', ':'))
        foo2 =  "{}\n{}".format(len(foo), foo)
        self._ws.send(foo2)

    def subscribe(self, subs=["export", "discover","interfaces","system-stats","num-routes","config-change", "users", "pon-stats"]):
        data = {'SUBSCRIBE': [{'name': x} for x in subs], 'UNSUBSCRIBE': [], 'SESSION_ID': self._session.session_id }
        self.send(data)

    @property
    def status(self):
        return self._ws.status

    def next(self):
        # read and return the next record from the stream
        self._session.heartbeat()
        buf = StringIO(self._ws.recv())
        payload_len = int(buf.readline())
        payload = StringIO(buf.read())
        payload.seek(0, 2)
        while payload.tell() < payload_len:
            payload.write(self._ws.recv())
            payload.seek(0, 2)
        payload.seek(0)
        try:
            return json.loads(payload.getvalue())
        except:
            return {'x_invalid': payload.getvalue() }

class edgeos_web(requests.Session):

    def __init__(self, endpoint, username, password, verify=False):
        requests.Session.__init__(self)
        self.verify = verify
        self._endpoint = endpoint
        self._username = username
        self._password = password
        self._last_valid = datetime.fromtimestamp(100000)
        if not verify:
            # suppress warnings
            quiet()

    def login(self):
        out = self.post(self._endpoint, data={'username':self._username, 'password': self._password})
        out.raise_for_status()
        return out

    @property
    def session_id(self):
        return self.cookies['PHPSESSID']

    @property
    def wsurl(self):
        p = urlparse(self._endpoint)
        return 'wss://{}/ws/stats'.format(p.netloc)

    def cookies_as_str(self):
        return '; '.join(["{}={}".format(*x) for x in self.cookies.items()])

    def create_websocket(self, timeout=60):
        # Spawn a websockt on this connection
        if self.verify:
            ws = websocket.create_connection(self.wsurl, origin=self._endpoint, timeout=timeout, cookie=self.cookies_as_str())
        else:
            ws = websocket.create_connection(self.wsurl, sslopt={"cert_reqs": ssl.CERT_NONE}, origin=self._endpoint, timeout=timeout, cookie=self.cookies_as_str())            
        return edgeos_webstream(ws,self)

    def _data(self, item):
        out = self.get(self._endpoint+'/api/edge/data.json?data='+item)
        out.raise_for_status()
        try:
            data = out.json()
            if data['success'] == 0:
                raise Exception(data['error'])
            return data['output']
        except:
            raise

    def dhcp_leases(self):
        return self._data('dhcp_leases')

    def dhcp_stats(self):
        return self._data('dhcp_stats')

    def routes(self):
        return self._data('routes')

    def sys_info(self):
        return self._data('sys_info')

    def heartbeat(self, max_age=15):
        ts = datetime.now()
        if ( datetime.now() - self._last_valid ) > timedelta(seconds=max_age):
            out = self.get(self._endpoint + '/api/edge/heartbeat.json?t=' + str(int(ts.timestamp())))
            out.raise_for_status()
            self._last_valid = ts
