
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
        self._buf = StringIO()

    def _buf_len(self):
        curpos = self._buf.tell()
        self._buf.seek(0,2)
        end = self._buf.tell()
        self._buf.seek(curpos)
        if end == curpos:
            # if the buffer is "empty" reset
            self._buf = StringIO()
            return 0
        else:
            return end-curpos

    def _buf_add(self):
        # Add another packet to the buffer by recording posistion
        # seeking to end, writing data, and then seeking back
        curpos = self._buf.tell()
        self._buf.seek(0,2)
        self._buf.write(self._ws.recv())
        self._buf.seek(curpos)

    def send(self, data):
        foo = json.dumps(data,separators=(',', ':'))
        foo2 =  "{}\n{}".format(len(foo), foo)
        self._ws.send(foo2)

    def subscribe(self, subs=["export", "discover","interfaces","system-stats","num-routes","config-change", "users"]):
        data = {'SUBSCRIBE': [{'name': x} for x in subs], 'UNSUBSCRIBE': [], 'SESSION_ID': self._session.session_id }
        self.send(data)

    @property
    def status(self):
        return self._ws.status

    def next(self):
        # read and return the next record from the stream
        if self._session.heartbeat():
            self._ws.send('{"CLIENT_PING"}')
        while True:
            # In case there is a problem attempting to get thee paylaod
            # length just keep trying to resync to the next packet
            if self._buf_len() < 4:
                self._buf_add()
            try:
                payload_len = int(self._buf.readline())
                break
            except:
                pass
        # Collect enough packets to decode the next message
        while self._buf_len() < payload_len:
            self._buf_add()
        payload = self._buf.read(payload_len)
        try:
            return json.loads(payload)
        except:
            return {'x_invalid': payload }

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
        if 'X-CSRF-TOKEN' in self.cookies:
            self.headers = { 'X-CSRF-TOKEN': self.cookies['X-CSRF-TOKEN'] }
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

    def create_websocket(self, timeout=30):
        # Spawn a websockt on this connection
        print(self.wsurl, self._endpoint, self.cookies_as_str())
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

    def batch(self, payload):
        out = self.post(self._endpoint+'/api/edge/batch.json', json=payload)
        return out
        #out.raise_for_status()
        #try:
        #    ret = out.json()
        #    if ret['success'] == False:
        #        raise Exception(ret)
        #    return ret
        #except:
        #    raise

    def config(self):
        out = self.get(self._endpoint+'/api/edge/get.json')
        out.raise_for_status()
        return out.json()

    def heartbeat(self, max_age=120):
        ts = datetime.now()
        if ( datetime.now() - self._last_valid ) > timedelta(seconds=max_age):
            #print('heartbeat')
            out = self.get(self._endpoint + '/api/edge/heartbeat.json?_=' + str(int(ts.timestamp())))
            out.raise_for_status()
            out = self.sys_info()
            self._last_valid = ts
            return True
        return False
