"""One real end-to-end Qwen + Guangzhou map/weather execution."""
import json,sys
from pathlib import Path
from datetime import date,timedelta
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app import load_env
from agent.core import Agent
from agent.providers import now

load_env()
today=date.fromisoformat(now()[:10]); day=today+timedelta(days=(5-today.weekday())%7 or 7)
request=dict(origin='广州大学大学城校区',date=day.isoformat(),people=2,budget=150,start='09:00',end='20:00',interests=['文化','拍照'],pace='relaxed',mode='live',engine='llm',model_provider='default')
result=Agent(request,ROOT/'evidence'/'live_runs').run()
(ROOT/'evidence'/'live-qwen-standard.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(status=result['status'],message=result.get('message'),run_id=result['run_id'],model=result['model_info'],usage=result['usage'],duration_ms=result['duration_ms'],external_calls=result['external_calls'],weather=result.get('weather'),plan=None if not result.get('plan') else dict(places=[p['name'] for p in result['plan']['places']],coordinate_status=[p['coordinate_status'] for p in result['plan']['places']],cost=result['plan']['cost'],schedule={k:v for k,v in result['plan']['schedule'].items() if k!='entries'}),backup_available=bool(result.get('rain_backup'))),ensure_ascii=False,indent=2),flush=True)
