import time
from http.client import RemoteDisconnected
from urllib.error import URLError
from urllib.request import urlopen


def wait_for_odoo(base='http://127.0.0.1:8069'):
    for attempt in range(30):
        try:
            with urlopen(base + '/web/login', timeout=3) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError, ConnectionError, RemoteDisconnected):
            pass
        time.sleep(1)
    raise RuntimeError('Odoo did not become ready within the browser test startup window')
