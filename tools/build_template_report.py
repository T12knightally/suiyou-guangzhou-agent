"""Report matching the assignment template; source all measurements from saved evidence."""
import json, sys, hashlib, shutil
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.graphics import renderSVG
from PIL import Image as PILImage
from pypdf import PdfReader, PdfWriter

sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT.parent; E=ROOT/'evidence'
FIG=E/'report_figures'; FIG.mkdir(exist_ok=True)
FIX=json.loads((E/'repairs/2026-10-14T00-23-33+08-00/summary.json').read_text(encoding='utf-8'))
D=ROOT/FIX['evidence_dir']
R=json.loads((D/'conversation_2_complete.json').read_text(encoding='utf-8'))
CHAT=[json.loads((D/f'conversation_{i}_{n}.json').read_text(encoding='utf-8')) for i,n in [(1,'missing'),(2,'complete'),(3,'adjust')]]
EV=json.loads((E/'evaluation.json').read_text(encoding='utf-8'))
M=json.loads((E/'http-multiturn.json').read_text(encoding='utf-8'))
STD=json.loads((E/'standard.json').read_text(encoding='utf-8'))
PROMPT=(ROOT/'prompts/system.md').read_text(encoding='utf-8').strip()
pdfmetrics.registerFont(TTFont('CN','C:/Windows/Fonts/simhei.ttf'))
pdfmetrics.registerFont(TTFont('CNB','C:/Windows/Fonts/simhei.ttf'))
pdfmetrics.registerFontFamily('CN',normal='CN',bold='CNB',italic='CN',boldItalic='CNB')
INK=GREEN=MUTED=colors.black
PALE=colors.white
W=487
styles={
 'body':ParagraphStyle('body',fontName='CN',fontSize=9.4,leading=16.2,textColor=INK,spaceAfter=8,wordWrap='CJK'),
 'h1':ParagraphStyle('h1',fontName='CNB',fontSize=18,leading=27,textColor=INK,spaceAfter=13,wordWrap='CJK'),
 'h2':ParagraphStyle('h2',fontName='CNB',fontSize=11.5,leading=18,textColor=GREEN,spaceBefore=10,spaceAfter=8,wordWrap='CJK'),
 'small':ParagraphStyle('small',fontName='CN',fontSize=8,leading=12.5,textColor=MUTED,spaceAfter=7,wordWrap='CJK'),
 'cell':ParagraphStyle('cell',fontName='CN',fontSize=8.2,leading=13.1,textColor=INK,wordWrap='CJK'),
 'code':ParagraphStyle('code',fontName='CN',fontSize=8.3,leading=13.2,textColor=INK,backColor=PALE,borderPadding=8,spaceBefore=6,spaceAfter=11,wordWrap='CJK'),
 'cover':ParagraphStyle('cover',fontName='CNB',fontSize=26,leading=39,textColor=INK,spaceAfter=22,wordWrap='CJK')}
story=[]; md=[]; headings=[]
def p(text,kind='body'):
 story.append(Paragraph(escape(str(text)).replace('\n','<br/>'),styles[kind]));md.append(str(text)+'\n')
def h1(text):
 p(text,'h1');md[-1]='## '+md[-1];headings.append(text)
def h2(text):
 p(text,'h2');md[-1]='### '+md[-1];headings.append(text)
def label(text): p(text,'h2')
def code(text,lang='text'):
 p(text,'code');md[-1]='```'+lang+'\n'+text+'\n```\n'
def page():story.append(PageBreak());md.append('<!-- pagebreak -->\n')
def table(headers,rows,widths):
 cells=[[Paragraph(escape(str(c)).replace('\n','<br/>'),styles['cell']) for c in row] for row in [headers]+rows]
 t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('GRID',(0,0),(-1,-1),.5,INK),('BOX',(0,0),(-1,-1),.8,INK)]))
 story.extend([t,Spacer(1,8)])
 md.extend(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(str(c).replace('\n','<br>') for c in row)+' |' for row in rows]+[''])
def img(path,width):
 # Preserve the original screenshot as evidence; only remove color for printing.
 with PILImage.open(path) as source:
  im=source.convert('L').point(lambda x: 0 if x < 220 else 255, mode='1')
  monochrome=FIG/(path.stem+'-black-white.png');im.save(monochrome)
  story.extend([Image(str(monochrome),width=width,height=width*im.height/im.width,hAlign='LEFT'),Spacer(1,7)])
 md.append(f'![运行凭据（黑白处理）]({monochrome.relative_to(OUT).as_posix()})\n')
def architecture():
 d=Drawing(W,254)
 def box(x,y,w,h,a,b):
  d.add(Rect(x,y,w,h,rx=7,fillColor=PALE,strokeColor=INK))
  d.add(String(x+w/2,y+h-18,a,fontName='CNB',fontSize=9,textAnchor='middle',fillColor=INK))
  d.add(String(x+w/2,y+12,b,fontName='CN',fontSize=7.4,textAnchor='middle',fillColor=MUTED))
 def arrow(x1,y1,x2,y2):
  d.add(Line(x1,y1,x2,y2,strokeColor=GREEN,strokeWidth=1))
  if x1==x2:
   sg=1 if y1>y2 else -1;pts=[x2,y2,x2-3,y2+sg*6,x2+3,y2+sg*6]
  else:
   sg=1 if x1>x2 else -1;pts=[x2,y2,x2+sg*6,y2-3,x2+sg*6,y2+3]
  d.add(Polygon(pts,fillColor=GREEN,strokeColor=GREEN))
 box(0,196,142,49,'表单 / 自然语言补参','原文证据校验 + 会话记忆')
 box(173,196,142,49,'输入校验 + Qwen Agent','最多 8 轮 / 12 次外层工具')
 box(345,196,142,49,'天气与地点工具','天气 / 地图 / 官方规则库')
 arrow(142,223,173,223);arrow(315,227,345,227);arrow(345,212,315,212)
 box(173,112,142,54,'build_plan 确定性求解','路线 + 费用 + 时间 + 步行')
 arrow(244,196,244,166)
 box(345,112,142,54,'异常与重新选择','下雨选室内 / 失败排除组合')
 arrow(315,147,345,147);arrow(345,129,315,129)
 box(0,112,142,54,'追问 / 拒绝 / 暂停','缺参、越界、严重天气')
 d.add(Line(185,196,185,181,strokeColor=GREEN))
 d.add(Line(185,181,71,181,strokeColor=GREEN));arrow(71,181,71,166)
 arrow(173,139,142,139)
 box(173,24,142,54,'行程 + 雨天安排','保存 JSON / 下载 TXT / 打印')
 arrow(244,112,244,78)
 box(345,24,142,54,'跨步骤执行证据','实际输入输出、错误、usage')
 arrow(315,51,345,51)
 d.add(String(3,43,'模型选择工具与候选；',fontName='CN',fontSize=8,fillColor=MUTED))
 d.add(String(3,28,'硬约束由程序执行。',fontName='CN',fontSize=8,fillColor=MUTED))
 story.append(d);renderSVG.drawToFile(d,str(FIG/'architecture.svg'))
 md.append('```mermaid\nflowchart TD\n A[表单或自然语言] --> N[需求提取与原文核对]\n N --> V{输入完整且合法}\n V -->|否| Q[追问或拒绝]\n V -->|是| B[Qwen 工具规划]\n B --> C[天气与地点 API]\n C --> B\n B --> D[build_plan 路线预算时间检查]\n D -->|路线失败或组合不满足| E[排除组合并比较其他候选]\n E --> D\n D -->|严重天气| S[暂停出行]\n D -->|估算约束通过| F[行程和雨天备选]\n F --> G[保存实际 Trace 与行程]\n```\n')


# Page 1
md.append('# 《基于 AI Agent 的业务落地实操》项目报告\n')
story.append(Spacer(1,18));p('《基于 AI Agent 的业务落地实操》\n项目报告','cover')
p('穗游：面向广州大学生的低预算周末出行 Agent','h2')
table(['基本信息','填写内容'],[
 ['学生姓名','待填写'],['学号','待填写'],['专业/班级','待填写'],['项目名称','穗游广州周末出行 Agent'],
 ['代码仓库/Demo 链接','https://github.com/T12knightally/suiyou-guangzhou-agent\n本机：http://127.0.0.1:8765/；应用未公网部署'],['提交日期','2026年10月20日']],[125,362])
p('版本1.0-defense：已实现真实模型工具编排、自然语言多轮补参、官方常规资料校验、真实步行路线与有界重规划。证据截至2026年10月20日，北京时间。','small')
h1('目录')
table(['模板章节','页码'],[['一、 业务背景与场景定义','2'],['二、 系统架构与流程设计','3-5'],['三、 实际运行效果与案例验证','6-8'],['四、 异常处理与边界测试','9'],['五、 调试过程与技术反思','10-11'],['六、 交付件清单与附录','12']],[420,67])
p('证据口径：真实模型与真实外部接口、真实模型与模拟故障、离线规则测试分别统计。Decision表示可审计的决策摘要，不是模型隐藏思维链。PDF附有最新原始Trace与评测文件。','small')
page()

# Page 2
h1('一、 业务背景与场景定义')
h2('1.1 业务痛点与目标')
p('行业/业务场景：广州高校学生的半日或一日城市出行。典型需求为“两人周六从学校出发，每人不超过150元，不想太累，晚上八点前回来”。校区或地址自由填写，不绑定特定学校。')
p('痛点描述：攻略、地图、天气与场馆公告分散；只看门票容易漏算往返车费、餐饮与临时花费；热门路线可能撞上闭馆、预约限制或返程冲突。纯文本问答难以证明路线和金额可执行。')
p('Agent解决目标：收集条件→查天气与地点→筛选目的地→查询往返路线→核算费用与时间→生成备选→保存。MVP限定广州20个种子地点，每次检索最多6个，模型选1-3个进行比较，最多安排2站。')
h2('1.2 角色定位与职责边界')
p('目标用户：广州出发的1-12人大学生小组，重视预算、步行负担和按时回校。角色为受限出行规划助手，不代替场馆预约或地图实时导航。')
table(['Agent职责范围','能力边界与免责（Out of Scope）'],[
 ['解析表单与自然语言；缺参数时追问；允许后续修改。','只支持广州同日行程；模糊金额、无法核对的值继续追问。'],
 ['查询地图天气，核算去程、停留、休息与返程。','路线为查询时估算，不承诺未来班次；不自动订票、付款。'],
 ['官方资料分层：10处来源，4处运营规则，3处明确票价。','20处中另6处仅有介绍来源；公告和名额非实时核验。'],
 ['闭馆排除、降雨选室内、失败时最多两次候选重选。','资料过期或日期超出核对区间时降为未知；不编造票价与营业时间。'],
 ['提供行程、来源链接、TXT、打印及完整服务端日志。','无画像和登录；源码已公开，应用仍仅本机访问。']],[235,252])
h2('1.3 输入与预期交付物')
p('业务初始输入：origin、date、people、budget（每人元数）、start/end；可选interests、pace、message、must_visit_ids、exclude_place_ids、indoor_only、max_stops。每人预算1-2000元，同日可用时间至少2小时。')
p('业务最终产出：按时间排列的行程、真实道路路线、费用明细、返回时刻、步行估算与室内备选；附官方来源及核验日期、免费范围和预约提醒。无可行方案时给出追问、失败原因或改期建议。')
p('验收口径：程序独立检查费用、开放时段、最晚入场、完整往返和用户必去/排除要求。unknown字段保留；内部状态draft代表估算通过，不等于预约成功或保证可入场。','small')
page()

# Page 3
h1('二、 系统架构与流程设计')
h2('2.1 整体架构 / 工作流流程图')
architecture()
p('图1　真实工具闭环。自然语言先提取增量字段并核对用户原文；模型选择工具和候选；受限执行器验证硬约束；失败可返回模型重选，严重天气终止。','small')
p('工程为Python标准库HTTP服务＋原生网页。app.py维护会话；requirements.py负责需求证据核对；core.py执行模型循环与求解；providers.py接地图天气；venue_facts.py应用带来源、核验期和适用日期的官方资料。')
p('约束：费用＝门票＋全部交通＋35元餐饮＋15元预留；轻松/普通节奏步行上限90/150分钟。公交每段加15分钟缓冲，真实步行加3分钟；场内步行另按每站15分钟估算。完整停留须落入开放区间，省博16:00起不再安排入场。')
p('求解：比较同片区双点的两种顺序与单点，检查必去/排除、停留和返程。评分为100×站数＋150×具官方开放依据站数＋10×兴趣交集－0.1×交通分钟。雨天主案已全室内时直接复用为雨天安排，晴天另算室内备选。最多两站，非全城最优。')
h2('2.2 核心模型选型')
p('首选qwen3.8-flash，经DashScope兼容接口，关闭思考模式；备选deepseek-flash，仅完成工具协议探针。Qwen已执行本报告8个真实模型检查点；选择理由是中文需求解析与tools协议可用，不以小样本宣称优于其他模型。')
p('规划最多8次模型响应/12次模型工具调用，需求理解另最多1次；最多两次build_plan。模型负责选择候选与可核对的短理由，程序负责路线、费用、时间和保存。无校验产物的纯文本“成功”不被采用。','small')
page()

# Page 4
h2('2.3 核心 System Prompt（提示词设计）')
p('以下直接读取当前prompts/system.md，与实际执行器使用的规划提示词一致。','small')
code(PROMPT,'markdown')
p('设计逻辑：Role/Task规定对象与目标；Constraints区分事实、规则和未知项；Tool use限定工具依赖、候选数量及重试；Output要求实际工具结果。选择理由是简短决策说明，不要求或伪造隐藏思维链。')
p('需求提取另用agent/requirements.py中的提示词：只修改本条消息明确表达的字段，每个字段附逐字原文；金额口径不明则追问。执行器核对原文包含关系、数值、日期和地点ID，模型不能凭空增加预算。完整提取Schema另存config/requirements_schema.json。')
p('自主性边界：模型可从6个候选选1-3个，可在首次失败后重选；阶段依赖与硬约束不能绕过。这是受限工作流Agent，不具备任意网络、Shell或交易权限。','small')
page()

# Page 5
h2('2.4 工具调用与技能清单（Tools / Actions）')
table(['工具名称','对应API / 脚本','参数输入','功能与触发时机'],[
 ['extract_trip_\nrequirements','requirements.py','updates / evidence / questions','有自然语言时先提取增量需求，逐字段核对原文。'],
 ['resolve_origin','高德v3/geocode/geo','name / coordinates','定位广州出发地址，歧义时拒绝猜测。'],
 ['query_weather','Open-Meteo forecast','{}；日期来自会话','模型首先调用，返回雨天/严重天气/来源。'],
 ['query_places','高德v5/place/text＋官方规则库','indoor:boolean','返回最多6候选；合并开放、免费范围和预约说明。'],
 ['build_plan','core.py：build/solve','candidate_ids / reason','模型选1-3候选；失败可重选一次。'],
 ['query_route','高德v3/direction/\nwalking或transit/integrated','from / to / date','近距离先查真实步行；失败再查公交；包含返程。'],
 ['calculate_cost /\ncheck_schedule','core.py','地点 / 路线 / 条件','金额、开放、最晚入场、步行和返程硬检查。'],
 ['save_itinerary','core.py：run','run_id','保存实际输入输出、时间戳和Trace。']],[88,142,104,153])
p('需求阶段仅暴露提取工具，规划阶段仅暴露天气、地点与build_plan。低层路线、核算和保存由执行器调用。完整Schema从运行代码导出，避免文档和实际参数漂移。','small')
code('build_plan: candidate_ids = 1-3个不同的已返回ID\nreason = 可选，最长240字\nadditionalProperties = false\n需求更新：{updates: {...}, evidence: {字段: "用户原文"},\n questions: [...]}；证据不匹配则追问','text')
h2('2.5 记忆机制与状态管理（Memory & State）')
p('短期记忆：session_id映射结构化条件；明确的新字段覆盖旧值；必去/排除名单增量合并并撤销相反偏好。上一轮message不自动重放，非法或越权输入不污染会话。网页追问只提交新message，不用表单默认值覆盖历史。')
p('长期记忆/知识：无向量库或画像。20个种子中10处有官方来源；4处有运营规则，3处有明确票价，另6处仅介绍；有效期7天，当前常规周历覆盖10月14-20日，过期降级。runs保存历史而非自学习。内存会话重启丢失，约200会话后清理。')
p('单任务缓存按室内条件与起终点复用，失败路线也缓存；不跨日期复用。单任务messages记录真实tool_calls与工具观察。','small')
page()

# Page 6
h1('三、 实际运行效果与案例验证')
h2('3.1 典型案例 1：标准成功流程（Happy Path）')
p('用户输入：两人，2026-10-17从广州大学大学城校区出发，每人150元，09:00出发、20:00前返回，轻松节奏，必去广东省博物馆和广州图书馆。输入由第3.2节的真实多轮对话补齐。')
p(f"本轮真实Qwen＋高德＋天气执行成功。run_id={R['run_id']}；模型响应{R['usage']['model_calls']}次（含1次需求理解），路线查询6次成功、0次失败；官方常规开放与票价缺失标记均为false。")
steps=[]
for t in R['trace']:
 if t.get('action')=='model_response':
  for c in t['observation']['tool_calls']:
   args=json.loads(c['function']['arguments'])
   if c['function']['name']=='build_plan':args.pop('reason',None)
   if c['function']['name']!='extract_trip_requirements':steps.append(f"[Action / #{t['seq']}] {c['function']['name']}({json.dumps(args,ensure_ascii=False)})")
steps += [f"[Observation] rain={str(R['weather']['rain']).lower()}；主案2站。",'[Action] query_route → calculate_cost → check_schedule',f"[Observation] {R['plan']['cost']['per_person']:g}元/人；{R['plan']['schedule']['return_time']}返回；步行79分钟。"]
code('\n'.join(steps))
table(['在线时间安排','实际输出内容'],[[e['start']+'-'+e['end'],e['title']] for e in R['plan']['schedule']['entries']],[100,387])
p('最终响应结果：两馆常规免费范围门票0元＋去程5元＋馆间步行0元＋返程5元＋餐饮35元＋机动15元＝60元/人，同行120元，预算余量90元/人。馆间道路为345米/约5分钟，另加3分钟缓冲；不是直线距离估算。','small')
p('官网依据：省博常规周二至周日09:00-17:00、16:00停止入场、实名分时预约；广图普通阅览09:00-21:00，专题文化区域按17:30前结束，周三闭馆。免费不覆盖收费特展或附加服务；预约余量与临时公告仍须出行前确认。','small')
page()

# Page 7
h2('3.2 典型案例 2：复杂多步 / 边界条件用例')
label('真实自然语言三轮：缺参、补齐、修改')
for i,r in enumerate(CHAT,1):
 p(f"第{i}轮用户：{r['request']['message']}")
 if i==1:p('Agent反问：'+'；'.join(r.get('questions',[])))
 else:p(f"执行结果：{r['status']}；每人预算{r['request']['budget']}元；选择"+'、'.join(x['name'] for x in r['plan']['places'])+f"；预计{r['plan']['cost']['per_person']:g}元/人，{r['plan']['schedule']['return_time']}返回。")
p('第二轮未重发出发地、人数与预算，系统沿用同会话状态；第三轮把每人预算改成80元，排除省博并限制一站，保留广图必去要求。提取值逐项附用户原文，未凭空猜测。三轮均真实调用模型，经HTTP进入实际会话逻辑。')
table(['验证点','运行ID / 结果'],[[f'自然语言第{i}轮',r['run_id']+' / '+r['status']] for i,r in enumerate(CHAT,1)]+[[x['case'],x['run_id']+' / '+x['status']] for x in FIX['rows'] if x['case'] in ['sysu','scut']],[115,372])
label('多校区与异常调整')
p('补充中山大学广州校区南校园（每人100元）、华南理工大学五山校区（每人80元）两次真实完整规划，均选择广图一站并通过预算、完整往返等独立复算。本轮4次产生行程的真实接口运行共12个路线事件，全部成功；样本小，不能宣称可靠率长期为100%。')
p('另外3例采用真实模型＋合成外部数据：闭馆后选其他地点；路线全部超时后重选仍无方案，返回no_feasible_plan；恶意地点文本要求改预算、选择被排除场馆并导出密钥，模型未提出越权工具调用，预算与排除条件保持。模拟故障不计入真实地图可靠率。','small')
page()

# Page 8
h2('3.3 运行凭据截图（Trace / 交互日志）')
img(E/'web-trace-crop.jpg',400)
p('图2　历史真实浏览器截图（2026-10-11，仅黑白处理）：展示当时合成天气工具的输入与观察。该图不冒充新版在线截图。新版截图因浏览器启动被拒绝未取得。可在 /review?run=85fb96702ab84d8d 查看本轮完整日志；以下为事件索引。','small')
table(['本轮序号','实际事件与观察'],[
 ['1-3','真实模型提取需求；原文证据核对；更新start/end/must_visit_ids。'],
 ['4-5','Decision初始化；高德定位出发校区。'],
 ['6-8','规划第1轮：模型tool_calls请求天气，工具返回降雨。'],
 ['9-11','第2轮：query_places(indoor=true)，返回候选与官方来源。'],
 ['12-14','第3轮：build_plan提交省博、广图；程序启动室内筛选。'],
 ['15-20','6次真实路线查询，均成功；包含两种方向的馆间步行。'],
 ['21-23','calculate_cost=60元；check_schedule=14:48；记录组合排除原因。'],
 ['24','save_itinerary：实际归档状态saved。']],[80,407])
p(f"本轮共{len(R['trace'])}个事件。原始文件：{FIX['evidence_dir']}/conversation_2_complete.json。保留模型响应ID、tool_calls、输入输出、时间戳、耗时与用量。上述索引由真实记录整理，不是重新生成的执行日志。",'small')
p('PDF附件含当前标准Trace、三轮对话、异常评测汇总及离线评测；完整其他案例在源码evidence/repairs中。Decision为程序决策摘要，模型选择说明只作理由，路线距离和费用以实际工具结果为准。','small')
page()

# Page 9
h1('四、 异常处理与边界测试')
h2('4.1 异常场景响应表现')
table(['测试场景','输入 / 模拟异常','预期行为','实际表现','符合'],[
 ['路线超时','真实模型＋全路线合成超时','有界重选后停止','4次模型响应；无可行方案','是'],
 ['工具注入','真实模型＋地点恶意文本','不改预算、不选排除项','未请求越权工具；预算150不变','是'],
 ['信息缺失','真实中文请求未给时间','追问并保留条件','needs_input；补齐后成功','是'],
 ['闭馆','真实模型＋合成闭馆标志','排除关闭地点','选广图等其他地点','是'],
 ['规则过期','核验日期超7天','不当作当前事实','票价/时间仍未知','是'],
 ['入场截止','省博恰好16:00到达','拒绝不可入场方案','时间校验失败；15:59可判定','是'],
 ['恶劣天气/低预算','规则夹具storm / 每人20元','暂停或无方案','suspended / no_feasible_plan','是'],
 ['会话污染','同会话预算改成负数','拒绝且保留之前合法预算','下一轮仍按150元规划','是'],
 ['伪造解析值','模型值与引用不一致','字段拒绝或追问','单元测试阻断','是'],
 ['步行字段缺失','地图未给distance','不可按直线距离填充','抛ProviderError，再查公交','是']],[67,132,105,139,44])
p(f"当前{EV['unit_tests']['total']}项单元/契约测试通过；12/12个合成场景通过；历史8/8真实模型检查点通过（3个为合成外部数据；早于新增资料）；HTTP 5项、网页DOM 9项通过。评测从票价/车费与时间条目重新计算，不仅检查程序自己返回的布尔标志。",'small')
h2('4.2 安全与护栏设计（Guardrails）')
p('防幻觉：无票价保留null并显示预留，官方资料限定适用范围和日期；无路线不输出虚构班次。防越权：工具白名单、严格参数、候选ID来源核对，预算和返程由程序检查；不提供交易、Shell或任意URL工具。外部文本不提升为系统指令。')
p('输入正则只是早期筛查；需求提取还校验引用、数值、日期及地点。前端HTML转义，官方链接只允许HTTPS与受信官方域名。密钥仅在服务端，日志递归脱敏，归档扫描配置密钥。单次注入通过不等于覆盖所有攻击。','small')
page()

# Page 10
h1('五、 调试过程与技术反思')
h2('5.1 踩坑与调优记录（至少记录 2 项调试经验）')
label('问题1：近邻场馆没有公交路线，双站方案被误淘汰')
p('原因排查：历史在线f29fe1974c634570中，省博到广图没有公交路线；15个路线事件9个失败，另8个错误码10021。旧实现只查公交，还提交全部候选，增加无效调用。不能仅凭错误码推断服务商故障原因。')
p('修复：1.5公里内先查高德真实步行，字段有效才采用；失败回退公交，不以直线距离编造路线。全局地图请求间隔至少0.45秒，模型最多选3候选。验证：新版双站案例6/6路线成功，馆间345米、约5分钟；这是不同时间的小样本，不证明节流消除了所有平台错误。')
label('问题2：省博免费入场却按未知票价预留30元')
p('原因排查：POI未返回可直接采信的门票和日期营业规则，旧版只能保留未知。修复：逐项读取省博和广图官网，记录URL、原文快照、抓取时间与HTML哈希；免费范围、周闭馆及最晚入场参与求解。核验期7天，周历仅覆盖已核对日期，过期降级。')
p('对比：旧单站按90元/人估算；新双站按60元/人估算，原因是官方范围内门票0元、往返车费10元。没有把预约成功作为免费依据，也没有据此承诺可入场。周一闭館、周三闭馆与16:00边界均有测试。')
label('问题3：表单补参不是自然语言多轮；非法值会污染会话')
p('修复：添加真实模型提取工具，每个更新字段附原文并经过规则核对；新消息仅增量提交，旧message不重放；被拒绝的输入不落入会话。验证：真实三轮“缺时间→补时间/必去→改80元/排除省博”成功；HTTP负预算后恢复150元通过。')
label('问题4：模型首次失败就停止；循环和文档缺少统一边界')
p('修复：首次无方案将观察返回模型，允许第二次选点；保持8次规划响应/12次工具上限与120秒预算，传递剩余网络超时。配置Schema从代码导出。真实路线超时夹具触发4次响应后停止；脚本协议验证首次闭馆、第二次换广图成功。')
p('历史失败记录继续保留：过去日期未前置拦截、缺步行字段被当作0、tuple与JSON list不一致曾使30测试中3项失败。当前回归扩为59项且通过。历史证据debug-before-fix.txt不覆盖。','small')
page()

# Page 11
h2('5.2 生产环境落地的局限性分析')
label('响应延迟与成本')
def tokens(r):return r['usage']['prompt_tokens']+r['usage']['completion_tokens']
table(['实测对象','耗时 / 模型调用','输入＋输出Token'],[[x['case'],f"{x['duration_ms']/1000:.2f}秒 / {x['usage']['model_calls']}次",f"{x['usage']['prompt_tokens']}＋{x['usage']['completion_tokens']}"] for x in FIX['rows']],[203,135,149])
p('以上为各次真实请求保存前的任务耗时，非线上P50/P95；本轮模型接口共返回'+str(sum(x['usage']['prompt_tokens']+x['usage']['completion_tokens'] for x in FIX['rows']))+' Token。自然语言多一轮提取带来额外时延和Token；工具观察与候选数量也影响后续上下文长度。')
p(f"离线规则引擎50次基准：P50={EV['latency']['p50_ms']}ms，P95={EV['latency']['p95_ms']}ms，含JSON落盘；不代表在线性能。费用应按输入/输出Token单价、缓存、地图配额及实际账单核算。本项目未取得人民币账单，不能把Token数冒充金额。",'small')
label('系统并发与高可用')
p('本机服务并发上限4，地图全局节流；没有公网认证、任务队列、分布式缓存与压力测试。120秒通过工具前检查和剩余网络超时控制，是尽力而为的预算，不是独立进程强制终止；慢速响应读取仍有超时边界。模型单请求45秒、不自动重试；数据请求6秒、至多重试一次。')
label('业务容错度')
p('20处中10处有官方来源，4处运营规则、3处明确票价；另6处仅介绍。新增南越王宫部分闭馆与西门规则已作单元验证，未重跑完整在线行程。周历到10月20日；公告与预约余量非实时抓取。未知门票30元、车费10元只是占位额度，不保证实际费用上界。步行估算未覆盖坡度、排队、无障碍和个体差异。')
p('本轮仅4次真实行程、同一出行日期、3个校区，无法推出广泛成功率；单个真实模型注入用例不构成安全证明。无学生真实用户调研、无人民币账单。源码仓库已发布；新版浏览器截图、公网应用及真实用户反馈尚未取得。','small')
page()

# Page 12
h1('六、 交付件清单与附录')
h2('6.1 提交代码及文件清单')
table(['文件 / 目录','交付内容'],[
 ['app.py、agent/、web/','HTTP会话、需求提取、规划/核算、地图天气、消费者网页。'],
 ['prompts/、config/、.env.example','规划Prompt、两阶段Schema、官方规则库与无密钥配置。'],
 ['tests/、evaluate.py、verify_http.py','59项单元/契约测试、12场景独立复算、HTTP 5项。'],
 ['tools/evaluate_repairs.py、verify_ui.cjs','真实模型8检查点与DOM 9项验证；前者消耗API额度。'],
 ['evidence/、README.md、资料维护说明.md','真实/模拟分离日志、官方来源与维护方法、环境及复现。'],
 ['本PDF、报告.md、源码ZIP','模板24个标题顺序一致；黑色黑体、表格全框；不含.env。']],[202,285])
p('源码：https://github.com/T12knightally/suiyou-guangzhou-agent；docs含同版报告与答辩详解。版本1.0-defense，应用未公网部署。姓名、学号、专业班级保留待填写；提交前按规定改名。','small')
h2('6.2 本地运行与复现指南')
p('运行环境：Python 3.10+，业务仅标准库。报告生成另需reportlab、Pillow、pypdf及SimHei中文字体；DOM检查需Node.js，非启动网站必需。','small')
code('# 在源码目录执行；已有.env时不要覆盖\nCopy-Item .env.example .env\n# 编辑AMAP_KEY、LLM_API_KEY、LLM_BASE_URL、LLM_MODEL\npython app.py\n# 浏览器 http://127.0.0.1:8765/\npython -m unittest discover -s tests -v\npython evaluate.py\npython verify_http.py\nnode tools/verify_ui.cjs\n# 真实模型与地图测试，需要额度；固定案例日期10月17日\npython tools/evaluate_repairs.py\n# 新版已保存结果：/?run='+R['run_id'],'powershell')
p('真实测试日期过期后请先修改测试日期并复核官方规则；历史归档用于回放，不可当作新预报。新机器可把evidence/repairs对应案例JSON复制到runs/<run_id>.json后查看。公网分享见分享与部署说明.md，127.0.0.1仅自己可打开。','small')
p('关键来源：省博参观指南 https://www.gdmuseum.com/col666/list；预约 https://www.gdmuseum.com/col843/list；广图开放 https://www.gzlib.org.cn/opentime/index.jhtml；免费开放介绍 https://www.gzlib.org.cn/aboutlib/index.jhtml。完整来源、抓取时间、HTML哈希和原文快照在config/venue_facts.json及evidence/official_sources。','small')
p('PDF附件：当前标准完整Trace、三轮对话、8检查点评测汇总、离线评测。其他原始案例与旧版失败证据随源码保留。地图文档lbs.amap.com/api/webservice/summary；天气open-meteo.com/en/docs；模型help.aliyun.com/zh/model-studio/。','small')

# Exact heading verification against the provided template.
expected=['目录','一、 业务背景与场景定义','1.1 业务痛点与目标','1.2 角色定位与职责边界','1.3 输入与预期交付物','二、 系统架构与流程设计','2.1 整体架构 / 工作流流程图','2.2 核心模型选型','2.3 核心 System Prompt（提示词设计）','2.4 工具调用与技能清单（Tools / Actions）','2.5 记忆机制与状态管理（Memory & State）','三、 实际运行效果与案例验证','3.1 典型案例 1：标准成功流程（Happy Path）','3.2 典型案例 2：复杂多步 / 边界条件用例','3.3 运行凭据截图（Trace / 交互日志）','四、 异常处理与边界测试','4.1 异常场景响应表现','4.2 安全与护栏设计（Guardrails）','五、 调试过程与技术反思','5.1 踩坑与调优记录（至少记录 2 项调试经验）','5.2 生产环境落地的局限性分析','六、 交付件清单与附录','6.1 提交代码及文件清单','6.2 本地运行与复现指南']
assert headings==expected

def footer(c,doc):
 c.setStrokeColor(INK);c.line(54,48,541,48)
 c.setFont('CN',7);c.setFillColor(MUTED);c.drawString(54,33,'穗游 SUIYOU  |  AI Agent 业务落地实操项目报告');c.drawRightString(541,33,f'{doc.page:02d}')
 if doc.page>1:c.drawString(54,807,'按课程统一模板编排');c.drawRightString(541,807,'2026.10.20')
path=OUT/'待填学号_待填姓名_穗游广州周末出行Agent.pdf'
doc=SimpleDocTemplate(str(path),pagesize=(595.28,841.89),leftMargin=54,rightMargin=54,topMargin=57,bottomMargin=58,title='《基于 AI Agent 的业务落地实操》项目报告 - 穗游',author='待填写')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
reader=PdfReader(path); count=len(reader.pages)
if count!=12:raise RuntimeError(f'Expected 12 pages, got {count}. Inspect layout before delivering.')
writer=PdfWriter();writer.clone_document_from_reader(reader)
for name,file in [('current-live-trace.json',D/'conversation_2_complete.json'),('repair-evaluation.json',D/'summary.json'),('offline-evaluation.json',E/'evaluation.json')]:writer.add_attachment(name,file.read_bytes())
writer.add_attachment('real-model-conversation.json',json.dumps(CHAT,ensure_ascii=False,indent=2).encode('utf-8'))
with path.open('wb') as f:writer.write(f)
(OUT/'穗游广州周末出行Agent_报告.md').write_text('\n'.join(md),encoding='utf-8')
(ROOT/'docs').mkdir(exist_ok=True)
shutil.copyfile(path,ROOT/'docs'/path.name)
(ROOT/'docs/穗游广州周末出行Agent_报告.md').write_text('\n'.join(md).replace('(广州周末Agent/evidence/','(../evidence/'),encoding='utf-8')
print(json.dumps({'pdf':str(path),'pages':count,'headings':len(headings),'chars':[len(p.extract_text()) for p in reader.pages],'attachments':4},ensure_ascii=False))
