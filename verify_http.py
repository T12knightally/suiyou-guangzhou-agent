import json
from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from urllib.error import HTTPError
from tests.test_agent import BASE

def post(obj,origin=None):
    headers={'Content-Type':'application/json'}
    if origin: headers['Origin']=origin
    request=Request('http://127.0.0.1:8765/api/plan',data=json.dumps(obj).encode(),headers=headers)
    try:
        with build_opener(ProxyHandler({})).open(request,timeout=15) as response: return response.status,json.load(response)
    except HTTPError as e: return e.code,json.load(e)

first_status,first=post({'request':{'origin':'广州大学大学城校区'}})
assert first_status==200 and first['status']=='needs_input'
second_status,second=post({'session_id':first['session_id'],'request':{k:v for k,v in BASE.items() if k!='origin'}})
assert second_status==200 and second['status']=='draft' and second['request']['origin']=='广州大学大学城校区'
bad_status,bad=post({'request':BASE},origin='https://unexpected.invalid')
assert bad_status==403
_,invalid=post({'session_id':second['session_id'],'request':{'budget':-1}})
assert invalid['status']=='invalid'
_,after_invalid=post({'session_id':second['session_id'],'request':{}})
assert after_invalid['status']=='draft' and after_invalid['request']['budget']==150
out=Path(__file__).resolve().parent/'evidence'/'http-multiturn.json'
out.write_text(json.dumps({'first':first,'second':second,'cross_site':{'http_status':bad_status,'response':bad},'invalid':invalid,'after_invalid':after_invalid},ensure_ascii=False,indent=2),encoding='utf-8')
print('HTTP checks: 5 passed; session recovery after rejected input verified.')
