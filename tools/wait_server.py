import time
from urllib.request import build_opener,ProxyHandler
for _ in range(20):
    try:
        with build_opener(ProxyHandler({})).open('http://127.0.0.1:8765/api/health',timeout=1) as r:
            if r.status==200:break
    except OSError:time.sleep(.5)
else:raise SystemExit('Server did not become ready')
