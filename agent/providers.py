import json, math, os, socket, time, threading
from datetime import datetime, date, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import URLError, HTTPError
from .data import SEEDS, ORIGINS
from .venue_facts import apply_facts

_AMAP_LOCK=threading.Lock()
_AMAP_NEXT=0.0

class ProviderError(Exception): pass

def now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')

def fetch_json(url, params=None, payload=None, headers=None, timeout=6, attempts=2, deadline=None):
    if params: url += '?' + urlencode(params)
    data = None if payload is None else json.dumps(payload).encode()
    req = Request(url, data=data, headers={'Content-Type':'application/json', **(headers or {})})
    # Never put URLs (which may contain a key) or raw provider errors in logs.
    for attempt in range(attempts):
        remaining=deadline-time.monotonic() if deadline else timeout
        if remaining<=0: raise ProviderError('本次规划达到总时限，请缩小需求后重试')
        try:
            with urlopen(req, timeout=min(timeout,remaining)) as response:
                obj=json.loads(response.read(2_000_000))
                if not isinstance(obj,dict): raise ValueError()
                return obj
        except HTTPError as e:
            # Never echo provider body, request URL, headers or a supplied key.
            hints={400:'请求参数或模型配置不兼容',401:'鉴权失败，请核对 Key、地域与 Base URL',402:'账户余额或计费状态不满足要求',403:'账户或接口权限不足',404:'接口地址或模型不可用',429:'请求限流或配额不足'}
            if e.code<500 or attempt==attempts-1:
                raise ProviderError(f'外部服务 HTTP {e.code}：'+hints.get(e.code,'服务暂不可用')) from None
        except (URLError, socket.timeout, TimeoutError, ValueError):
            if attempt==attempts-1: raise ProviderError('外部服务连接失败、超时或响应格式异常') from None
        time.sleep(.15)
    raise ProviderError('外部服务不可用')

def distance(a,b):
    x,y = map(math.radians, [a[1],b[1]])
    dx = math.radians(b[0]-a[0])
    h = math.sin((y-x)/2)**2 + math.cos(x)*math.cos(y)*math.sin(dx/2)**2
    return 6371*2*math.asin(min(1, math.sqrt(h)))

class Provider:
    def __init__(self, mode='demo', scenario='sunny'):
        self.mode, self.scenario, self.calls = mode, scenario, 0
        self.cache = {}
        self.deadline=None
        self.day=None

    def amap(self, endpoint, **params):
        global _AMAP_NEXT
        key = os.getenv('AMAP_KEY','')
        if not key: raise ProviderError('尚未配置 AMAP_KEY；在线模式不可伪装为演示模式')
        # One shared pace across all concurrent requests, not one limiter per user.
        with _AMAP_LOCK:
            wait=max(0,_AMAP_NEXT-time.monotonic())
            if self.deadline and time.monotonic()+wait>=self.deadline:
                raise ProviderError('本次规划达到总时限，请稍后重试')
            if wait: time.sleep(wait)
            _AMAP_NEXT=time.monotonic()+.45
        if self.calls >= 40: raise ProviderError('达到本轮地图请求上限 40 次')
        self.calls += 1
        obj = fetch_json('https://restapi.amap.com/'+endpoint, {'key':key, **params},deadline=self.deadline)
        if obj.get('status') != '1':
            code=str(obj.get('infocode',''))
            safe_code=code if code.isdigit() and len(code)<=8 else 'unknown'
            raise ProviderError(f'地图服务拒绝请求（infocode={safe_code}），请检查 Key、配额和服务权限')
        return obj

    def origin(self, name, coordinates=None):
        if self.mode == 'demo':
            if coordinates: return tuple(coordinates)
            if name in ORIGINS: return ORIGINS[name]
            raise ProviderError('离线演示不认识此出发地，请补充广州范围内的经纬度；在线模式支持自由地址定位')
        rows = self.amap('v3/geocode/geo', address=name, city='广州').get('geocodes',[])
        if len(rows) != 1: raise ProviderError('地址不唯一或未找到，请填写具体校区及区名')
        row=rows[0]
        if not str(row.get('adcode','')).startswith('4401'): raise ProviderError('仅支持广州市范围内的出发地')
        return tuple(map(float,row['location'].split(',')))

    def weather(self, day, origin):
        self.day=day
        if self.mode == 'demo':
            if self.scenario == 'weather_timeout':
                return dict(status='unknown', rain=None, severe=False, source='故障注入：天气超时', fetched_at=now())
            return dict(status='synthetic',rain=self.scenario in ['rain','storm'], severe=self.scenario=='storm',
                        summary='合成雷暴预警' if self.scenario=='storm' else ('合成降雨场景' if self.scenario=='rain' else '合成晴天场景'),
                        source='离线合成测试夹具；不是出行日天气预报',date=day,fetched_at=now())
        today=datetime.now(timezone(timedelta(hours=8))).date()
        if not 0 <= (date.fromisoformat(day)-today).days <= 15:
            return dict(status='unknown',rain=None,severe=False,source='日期超出 16 天天气窗口',fetched_at=now())
        self.calls += 1
        try:
            r=fetch_json('https://api.open-meteo.com/v1/forecast',dict(latitude=origin[1],longitude=origin[0],daily='weather_code,precipitation_probability_max',timezone='Asia/Shanghai',start_date=day,end_date=day),deadline=self.deadline)
            d=r['daily']; code=d['weather_code'][0]; probability=d['precipitation_probability_max'][0]
            if code is None or probability is None: raise ValueError()
            return dict(status='forecast',rain=probability>=50 or code>=51,severe=code>=95,
                        probability=probability,weather_code=code,source='Open-Meteo forecast',date=day,fetched_at=now())
        except (ProviderError,KeyError,IndexError,TypeError,ValueError):
            return dict(status='unknown',rain=None,severe=False,source='天气查询不可用',fetched_at=now())

    def places(self, interests, indoor=False):
        rows=[dict(p) for p in SEEDS if (not indoor or p['indoor']) and p['id'] not in getattr(self,'exclude_ids',[])]
        rows.sort(key=lambda p: (p['id'] not in getattr(self,'preferred_ids',[]),-len(set(p['tags']) & set(interests))))
        # A compact local index narrows expensive remote lookups to six candidates.
        rows=rows[:6]
        for p in rows:
            p['fetched_at']=now()
            if self.mode=='demo':
                p.update(open_minutes=[540,1080],ticket=0 if p['id'] not in ['science','chen','sun'] else 30,
                         closed=self.scenario=='closure' and p['id']=='gd_museum',
                         source='synthetic_fixture',factual_status='synthetic',
                         notice='门票与 09:00-18:00 开放区间均为测试数据，预约政策未知')
            else:
                p.update(open_minutes=None,ticket=None,closed=False,source='unverified_seed',notice='票价、日期对应开放时间及预约要求待官方核实')
                try:
                    key=('poi',p['id'])
                    if key not in self.cache:
                        self.cache[key]=self.amap('v5/place/text',keywords=p['name'],region='440100',city_limit='true',show_fields='business',page_size=3)
                    pois=self.cache[key].get('pois',[])
                    exact=[x for x in pois if x.get('name')==p['name'] and str(x.get('adcode','')).startswith('4401')]
                    if exact:
                        q=exact[0]; p['lon'],p['lat']=map(float,q['location'].split(','))
                        p['coordinate_status']='amap_exact_name'; p['source']='高德 v5/place/text'
                        p['address']=q.get('address',''); p['provider_opening_text']=str(q.get('business',{}).get('opentime_week','未知'))[:300]
                    else: p['notice']+='；名称未精确匹配，坐标仍为候选种子'
                except (ProviderError,ValueError,KeyError): p['notice']+='；地点接口不可用'
                apply_facts(p,self.day or now()[:10],now()[:10])
        return rows

    def route(self, start, end, day):
        key=('route',tuple(start),tuple(end),day)
        if key in self.cache: return self.cache[key]
        if self.scenario=='route_timeout' and self.mode=='demo': raise ProviderError('故障注入：路线接口超时')
        km=distance(start,end)
        if self.mode=='demo':
            walking=km < 1.1
            r=dict(minutes=max(10,math.ceil(km*1.4/4*60)) if walking else math.ceil(25+km*3),
                   fare=0 if walking else 8,walk_minutes=max(10,math.ceil(km*1.4/4*60)) if walking else 16,
                   summary='模拟步行' if walking else '模拟公共交通（非真实班次）',source='synthetic_distance_formula',estimated=True)
        else:
            # Walking routes are queried, never extrapolated from straight-line distance.
            if km<=1.5:
                try:
                    r=self.walking_route(start,end)
                    r.update(fetched_at=now(),query_date=day)
                    self.cache[key]=r
                    return r
                except ProviderError:
                    if self.deadline and time.monotonic()>=self.deadline: raise
            r0=self.amap('v3/direction/transit/integrated',origin=','.join(map(str,start)),destination=','.join(map(str,end)),city='广州',cityd='广州',strategy=0,extensions='all')
            ts=r0.get('route',{}).get('transits',[])
            if not ts: raise ProviderError('未查到公交路线，无法验证往返时间')
            t=ts[0]
            try:
                duration=float(t['duration']); walk=float(t['walking_distance'])
                fare=float(t['cost']) if isinstance(t.get('cost'),(str,int,float)) and t['cost']!='' else None
                if not math.isfinite(duration) or duration<=0 or not math.isfinite(walk) or walk<0 or (fare is not None and (not math.isfinite(fare) or fare<0)): raise ValueError()
                names=[]
                for s in t.get('segments',[]):
                    for line in s.get('bus',{}).get('buslines',[]): names.append(line.get('name','公交'))
                r=dict(minutes=math.ceil(duration/60)+15,fare=fare,walk_minutes=math.ceil(walk/65),
                       summary=' → '.join(names) or '高德公共交通路线',source='高德 v3 公交路线 + 15 分钟缓冲',estimated=True,
                       notice='查询时路线估算，非指定日期班次承诺')
            except (ValueError,KeyError,TypeError): raise ProviderError('路线字段不完整，不能验证时间与预算')
        r.update(fetched_at=now(),query_date=day)
        self.cache[key]=r
        return r

    def walking_route(self,start,end):
        obj=self.amap('v3/direction/walking',origin=','.join(map(str,start)),destination=','.join(map(str,end)))
        try:
            path=obj['route']['paths'][0]
            duration=float(path['duration']); meters=float(path['distance'])
            if not math.isfinite(duration) or not math.isfinite(meters) or duration<=0 or meters<=0: raise ValueError()
            minutes=math.ceil(duration/60)
            steps=[s.get('instruction','') for s in path.get('steps',[]) if isinstance(s,dict)]
            return dict(minutes=minutes+3,fare=0,walk_minutes=minutes,mode='walking',distance_m=round(meters),
                        summary=f'步行约{minutes}分钟（{round(meters)}米）',instructions=steps,
                        source='高德 v3 步行路线 + 3 分钟缓冲',estimated=True,notice='以实际道路通行情况为准')
        except (KeyError,IndexError,TypeError,ValueError):raise ProviderError('未获得有效步行路线，不能用直线距离代替道路') from None
