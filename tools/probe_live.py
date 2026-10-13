"""Explicit bounded live checks; writes only redacted evidence, never credentials."""
import json, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app import load_env
from agent.model_config import model_config,redact
from agent.providers import Provider,ProviderError,fetch_json,now

def main():
    load_env(); checks=[]
    def check(name,fn):
        t=time.perf_counter()
        try: row=dict(name=name,ok=True,result=fn())
        except ProviderError as e: row=dict(name=name,ok=False,error=str(e))
        except Exception as e: row=dict(name=name,ok=False,error='响应格式异常：'+type(e).__name__)
        row['duration_ms']=round((time.perf_counter()-t)*1000,2);checks.append(redact(row))
        print(json.dumps(redact(row),ensure_ascii=False),flush=True)
    def model_probe(choice):
        c=model_config(choice)
        tool={'type':'function','function':{'name':'record_probe','description':'记录连通性测试完成','parameters':{'type':'object','properties':{'ok':{'type':'boolean'}},'required':['ok'],'additionalProperties':False}}}
        r=fetch_json(c['base']+'/chat/completions',payload=dict(model=c['model'],messages=[{'role':'user','content':'请调用 record_probe 工具，参数 ok=true。'}],tools=[tool],tool_choice='auto',max_tokens=128,**c['extra']),headers={'Authorization':'Bearer '+c['key']},timeout=45,attempts=1)
        calls=r['choices'][0]['message'].get('tool_calls') or []
        valid=any(t.get('function',{}).get('name')=='record_probe' and json.loads(t['function']['arguments']).get('ok') is True for t in calls)
        return dict(provider=c['provider'],model=c['model'],tool_call_valid=valid,tool_calls=redact(calls),usage=r.get('usage'),response_id=r.get('id'))
    check('qwen_tool_call',lambda:model_probe('default'))
    check('deepseek_tool_call',lambda:model_probe('deepseek'))
    p=Provider('live');origin=[]
    def geo():
        v=p.origin('广州大学大学城校区');origin.extend(v);return {'coordinates':v}
    check('amap_geocode',geo)
    def poi():
        r=p.amap('v5/place/text',keywords='广东省博物馆',region='440100',city_limit='true',show_fields='business',page_size=3)
        return {'count':r.get('count'),'pois':[{k:v.get(k) for k in ['name','location','adcode']} for v in r.get('pois',[])]}
    check('amap_poi',poi)
    if origin:
        check('amap_transit',lambda:p.route(origin,(113.321,23.118),now()[:10]))
        check('open_meteo',lambda:p.weather(now()[:10],origin))
    report=redact(dict(checked_at=now(),checks=checks,note='真实接口的小规模连通性与工具协议测试，不代表全流程行程验收；网络请求不自动重试模型。'))
    (ROOT/'evidence'/'live-connectivity.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
