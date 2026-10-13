"""Run with Python 3.10+. No third-party runtime dependency."""
import argparse, json, os, re, threading, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from agent.core import Agent
from agent.model_config import ENV_FIELDS

ROOT=Path(__file__).resolve().parent
SESSIONS={}; LOCK=threading.Lock(); SEMAPHORE=threading.BoundedSemaphore(4)

def load_env():
    p=ROOT/'.env'
    if p.exists():
        for line in p.read_text(encoding='utf-8-sig').splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                k,v=line.split('=',1)
                if k.strip() in ENV_FIELDS: os.environ.setdefault(k.strip(),v.strip().strip('"').strip("'"))

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def send(self,status,obj,kind='application/json; charset=utf-8'):
        data=json.dumps(obj,ensure_ascii=False).encode() if isinstance(obj,(dict,list)) else obj
        self.send_response(status); self.send_header('Content-Type',kind); self.send_header('Content-Length',str(len(data)))
        self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/api/health': return self.send(200,dict(ok=True,amap_configured=bool(os.getenv('AMAP_KEY')),llm_configured=all(os.getenv(k) for k in ['LLM_API_KEY','LLM_BASE_URL','LLM_MODEL'])))
        if re.fullmatch(r'/api/runs/[a-f0-9]{16}',path):
            p=ROOT/'runs'/(path.rsplit('/',1)[-1]+'.json')
            return self.send(200,p.read_bytes()) if p.exists() else self.send(404,{'error':'未找到行程'})
        allowed={'/':'index.html','/app.js':'app.js','/style.css':'style.css','/review':'review.html','/review.js':'review.js','/review.css':'review.css'}
        if path not in allowed: return self.send(404,{'error':'未找到资源'})
        mime='text/html' if path in ['/','/review'] else ('text/javascript' if path.endswith('js') else 'text/css')
        self.send(200,(ROOT/'web'/allowed[path]).read_bytes(),mime+'; charset=utf-8')
    def do_POST(self):
        if self.path!='/api/plan': return self.send(404,{'error':'未找到资源'})
        host=self.headers.get('Host','')
        if host not in [f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}']: return self.send(403,{'error':'仅接受本机访问'})
        origin=self.headers.get('Origin')
        if origin and origin not in [f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}']: return self.send(403,{'error':'跨站请求已拒绝'})
        if not SEMAPHORE.acquire(blocking=False): return self.send(429,{'error':'当前请求较多，请稍后重试'})
        try:
            length=int(self.headers.get('Content-Length',0))
            if not 0<length<=16000: return self.send(400,{'error':'请求体大小无效'})
            data=json.loads(self.rfile.read(length))
            if not isinstance(data,dict) or not isinstance(data.get('request'),dict): return self.send(400,{'error':'request 必须是对象'})
            sid=data.get('session_id') or uuid.uuid4().hex
            if not isinstance(sid,str) or not re.fullmatch('[a-f0-9]{32}',sid): return self.send(400,{'error':'会话 ID 无效'})
            with LOCK:
                if len(SESSIONS)>200: SESSIONS.clear()
                previous={k:v for k,v in SESSIONS.get(sid,{}).items() if k!='message'}
                state={**previous,**data['request']}
                allowed={'origin','date','people','budget','start','end','interests','pace','coordinates','mode','scenario','engine','model_provider','message','must_visit_ids','exclude_place_ids','indoor_only','max_stops'}
                state={k:v for k,v in state.items() if k in allowed}
            result=Agent(state).run()
            if result['status'] not in ['invalid','rejected','out_of_scope']:
                with LOCK:SESSIONS[sid]={k:v for k,v in result['request'].items() if k in allowed and k!='message'}
            result['session_id']=sid; self.send(200,result)
        except (ValueError,TypeError): self.send(400,{'error':'输入格式错误'})
        except Exception: self.send(500,{'error':'内部错误，请检查本地日志；没有生成可验证行程'})
        finally: SEMAPHORE.release()

if __name__=='__main__':
    load_env(); parser=argparse.ArgumentParser(); parser.add_argument('--port',type=int,default=8765); args=parser.parse_args()
    print(f'Suiyou ready: http://127.0.0.1:{args.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
