const $ = s => document.querySelector(s), form = $('#form');
let session = null;
let savedRequest = null;
const now = new Date(), saturday = new Date(now);
saturday.setDate(now.getDate() + ((6 - now.getDay() + 7) % 7 || 7));
const localDate = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
$('#date').value = localDate(saturday);
$('#date').min = localDate(now);
const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = x => Number(x).toLocaleString('zh-CN', {maximumFractionDigits: 2});
function notice(text = '') {
  $('#notice').textContent = text;
  $('#notice').hidden = !text;
}

// Diagnostics remain in saved API results; the page presents travel information.
function visitNotes(place) {
  const notes = [];
  if (place.facts_status === 'official_regular_rules') {
    if (place.ticket_scope) notes.push(place.ticket_scope);
    if (place.reservation_note) notes.push(place.reservation_note);
    if (place.last_entry_minute != null) notes.push(`最晚入场 ${String(Math.floor(place.last_entry_minute/60)).padStart(2,'0')}:${String(place.last_entry_minute%60).padStart(2,'0')}`);
    notes.push('临时开放调整以场馆公告为准');
  }
  if (!place.open_minutes) notes.push('出发前请查看场馆当日开放时间和预约名额');
  if (place.coordinate_status && place.coordinate_status !== 'amap_exact_name') notes.push('到访位置请以地图中的场馆地址为准');
  return notes;
}
function entryDetail(entry, plan) {
  if (entry.kind === 'visit') {
    const place = plan.places.find(x => x.id === entry.id);
    if (place) return [place.address || place.area, place.indoor ? '室内游览' : '户外游览', ...visitNotes(place)].filter(Boolean).join(' · ');
  }
  if (entry.kind === 'meal') return '找一家顺路的小店，吃饭、喝水，歇一会儿。';
  return entry.detail;
}
function costRows(plan) {
  let ticketIndex = 0, routeIndex = 0;
  return plan.cost.items.map(item => {
    let label = item.label, note = '', allowance = false;
    if (item.category === '门票') {
      const place = plan.places[ticketIndex++];
      allowance = place?.ticket == null;
      note = allowance ? '门票费用预留，非实际票价；请查看场馆票价与学生优惠' : (place?.ticket_scope || '参考票价，实际以场馆为准');
    } else if (item.category === '交通') {
      const i = routeIndex++, route = plan.routes[i];
      label = i === plan.routes.length - 1 ? '返程交通' : i === 0 ? '去程交通' : '景点间交通';
      allowance = route?.fare == null;
      note = allowance ? '车费暂未查到，此处为交通预留' : '参考车费';
    } else if (item.category === '餐饮') note = '可按喜好灵活安排';
    else if (item.category === '预留') { label = '机动费用'; note = '留给临时的小开销'; }
    return {...item, label, note, allowance};
  });
}
function timeline(plan) {
  return `<div class="timeline">${plan.schedule.entries.map(e => `<div class="stop ${esc(e.kind)}"><time>${esc(e.start)}<br>— ${esc(e.end)}</time><div class="body"><h4>${esc(e.title)}</h4><p>${esc(entryDetail(e, plan))}</p></div></div>`).join('')}</div>`;
}
function officialLinks(plan) {
  const safe = u => {try {const x = new URL(u); return x.protocol === 'https:' && ['www.gdmuseum.com','www.gzlib.org.cn'].includes(x.hostname);} catch {return false;}};
  return plan.places.filter(p => p.official_sources?.length).map(p => `<details class="source-note"><summary>${esc(p.name)} · 查看场馆信息</summary><p>${esc(p.opening_basis || '常规资料需重新核对')} · 资料核对于 ${esc((p.facts_checked_at || '').slice(0,10))}</p>${p.official_sources.filter(s => safe(s.url)).map(s => `<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)} ↗</a>`).join(' · ')}<p>${esc(p.reservation_note || '请查看最新预约说明')}</p></details>`).join('');
}
function costs(plan) {
  return `<table class="cost-table"><thead><tr><th>花费安排</th><th>每人预算</th></tr></thead><tbody>${costRows(plan).map(x => `<tr><td>${esc(x.label)}<small>${esc(x.note)}</small></td><td>${x.allowance ? '<small>预留</small>' : ''}¥${money(x.amount)}</td></tr>`).join('')}</tbody></table>`;
}
function weatherText(weather) {
  if (!weather || weather.status !== 'forecast') return '天气信息暂未更新，出发当天记得再看一下天气。';
  const probability = Number.isFinite(weather.probability) ? `降雨概率 ${weather.probability}%` : '';
  return [probability, weather.rain ? '记得带伞，优先安排室内游览。' : '出发前再看一眼天气，轻装出门。'].filter(Boolean).join(' · ');
}
function planText(plan) {
  return [
    ...plan.schedule.entries.map(e => `${e.start}–${e.end}  ${e.title}\n${entryDetail(e, plan)}`),
    '', '每人花费安排',
    ...costRows(plan).map(x => `${x.label}：¥${money(x.amount)}${x.allowance ? '（预留）' : ''} · ${x.note}`),
    `合计：¥${money(plan.cost.per_person)}/人 · 预计 ${plan.schedule.return_time} 返回`,
    '交通用时为预计，已留出换乘余地。',
    ...plan.places.flatMap(p => (p.official_sources || []).map(s => `${p.name}：${s.title} ${s.url}（核对于${(p.facts_checked_at || '').slice(0,10)}）`))
  ].join('\n');
}
function downloadTrip(r) {
  const lines = ['穗游 · 我的广州周末', `${r.request.date} · ${r.request.people} 人 · 从 ${r.request.origin} 出发`, ''];
  if (r.request.mode !== 'live') lines.push('示例行程：使用模拟数据，仅供体验。', '');
  lines.push(weatherText(r.weather), '', planText(r.plan));
  if (r.rain_backup) lines.push('', '雨天安排', planText(r.rain_backup));
  const blob = new Blob(['\uFEFF' + lines.join('\n')], {type:'text/plain;charset=utf-8'});
  const url = URL.createObjectURL(blob), a = document.createElement('a');
  a.href = url; a.download = `穗游-广州周末-${r.request.date}.txt`; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function render(r) {
  savedRequest = {...r.request};
  for (const key of ['origin','date','people','budget','start','end','pace']) {
    const field = form.elements.namedItem(key);
    if (field && r.request[key] !== undefined) field.value = r.request[key];
  }
  document.querySelectorAll('input[name="interest"]').forEach(x => x.checked = (r.request.interests || []).includes(x.value));
  $('#conversation').hidden = false;
  $('#status-pill').textContent = ({draft:'行程已生成',needs_input:'补充出行信息',invalid:'调整出行条件',no_feasible_plan:'换个安排试试',suspended:'建议改期',needs_configuration:'暂时无法规划',unavailable:'暂时无法规划'})[r.status] || '请调整后重试';
  notice(r.plan && r.request.mode !== 'live' ? '这是一份示例行程，使用模拟数据，仅供体验。填写条件后可重新规划。' : '');
  if (!r.plan) {
    const messages = {
      needs_input:'再补充一点信息，就能开始规划。',
      no_feasible_plan:'这次的预算或时间有些紧，试试增加一点预算、延长出行时间，或换个出发地点。',
      suspended:'出行日可能有雷暴等恶劣天气，建议换个日期再出发。',
      needs_configuration:'出行服务暂时不可用，请稍后再试。',
      unavailable:'暂时没能获取完整的出行信息，请稍后重试，或换个日期。',
      out_of_scope:'目前支持广州本地出行，请填写广州的校区或地址。',
      rejected:'请填写出发地点、日期和出行偏好，再试一次。'
    };
    const message = messages[r.status] || (r.status === 'invalid' ? String(r.message).replace('在线模式不支持过去日期', '请选择未来的出行日期') : '请检查出行条件后重试。');
    $('#result').innerHTML = `<div class="error"><h3>把条件调整一下，再出发</h3><p>${esc(message)}</p>${(r.questions || []).map(x => `<p>${esc(x)}</p>`).join('')}</div>`;
    return;
  }
  const p = r.plan, c = p.cost, s = p.schedule, b = r.rain_backup;
  const sameBackup = b && p.places.map(x => x.id).join(',') === b.places.map(x => x.id).join(',');
  const reserve = c.items.filter(x => x.category === '预留').reduce((sum, x) => sum + x.amount, 0);
  $('#result').innerHTML = `
    <div class="trip-context"><strong>${esc(r.request.date)} · ${esc(r.request.people)} 人同行</strong><span>从 ${esc(r.request.origin)} 出发</span></div>
    <div class="weather-note">${esc(weatherText(r.weather))}</div>
    <div class="stats"><div class="stat"><small>每人预计花费</small><strong>¥${money(c.per_person)}</strong><span>预算还余 ¥${money(c.remaining)}</span></div><div class="stat"><small>预计返回</small><strong>${esc(s.return_time)}</strong><span>最晚 ${esc(s.deadline)} 返回</span></div><div class="stat"><small>同行合计</small><strong>¥${money(c.group_total)}</strong><span>含每人 ¥${money(reserve)} 机动费用</span></div></div>
    <div class="subheading"><strong>这一天，这样走</strong><small>${p.places.length} 个目的地 · 预计步行 ${esc(s.walk_minutes)} 分钟</small></div>${timeline(p)}
    <p class="route-note">交通用时为预计，已留出换乘余地。</p>${officialLinks(p)}
    <div class="subheading"><strong>每一笔，都算清楚</strong><small>按人计价</small></div>${costs(p)}
    <div class="backup"><h3>☂ ${sameBackup ? '下雨也能这样逛' : '如果下雨，换一种逛法'}</h3><p>${sameBackup ? '这条路线已以室内游览为主，往返途中记得带伞。' : b ? `${esc(b.places.map(x => x.name).join(' → '))}<br>每人预计 ¥${money(b.cost.per_person)} · ${esc(b.schedule.return_time)} 返回` : '暂时没有合适的室内安排，可以换个日期，留给晴天出发。'}</p>${b && !sameBackup ? `<details><summary>查看雨天安排</summary>${timeline(b)}${costs(b)}</details>` : ''}</div>
    <div class="actions"><button type="button" id="download">保存行程单 ↓</button><button type="button" id="print">打印行程</button></div>`;
  $('#download').onclick = () => downloadTrip(r);
  $('#print').onclick = () => window.print();
}

async function submitRequest(request) {
  $('#submit').disabled = true;
  $('#adjust').disabled = true;
  $('#reset').disabled = true;
  $('#submit').textContent = '正在安排你的周末…';
  $('#status-pill').textContent = '正在规划';
  notice('正在寻找合适的去处，安排路线和花费，请稍等片刻。');
  $('#result').setAttribute('aria-busy', 'true');
  $('#result').innerHTML = '<div class="empty"><div class="empty-icon planning">↗</div><h3>把时间留给期待</h3><p>正在为你寻找预算之内的广州周末。</p></div>';
  try {
    const response = await fetch('/api/plan', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:session,request})});
    if (!response.ok) throw new Error('服务暂时不可用');
    const r = await response.json();
    session = r.session_id; render(r);
    $('#message').value = ''; $('#followup').value = '';
    if (r.plan && /^[a-f0-9]{16}$/.test(r.run_id)) history.replaceState(null, '', `?run=${r.run_id}`);
  } catch {
    notice();
    $('#result').innerHTML = '<div class="error"><h3>这次没能安排好，请再试一次</h3><p>出行服务暂时没有响应，你填写的条件已保留，稍后点击规划即可。</p></div>';
    $('#status-pill').textContent = '请稍后重试';
  } finally {
    $('#result').removeAttribute('aria-busy');
    $('#submit').disabled = false;
    $('#adjust').disabled = false;
    $('#reset').disabled = false;
    $('#submit').innerHTML = '规划我的周末 <span>↗</span>';
  }
}
form.addEventListener('submit', e => {
  e.preventDefault();
  const f = new FormData(form), request = {mode:'live',engine:'llm',model_provider:'default',coordinates:null};
  for (const key of ['origin','date','start','end','pace','message']) request[key] = f.get(key);
  for (const key of ['people','budget']) request[key] = f.get(key) === '' ? null : Number(f.get(key));
  request.interests = f.getAll('interest');
  return submitRequest(request);
});
$('#followup-form').addEventListener('submit', e => {
  e.preventDefault();
  const message = $('#followup').value.trim();
  if (message) return submitRequest({...(!session ? savedRequest : {}), message});
});
$('#reset').onclick = () => {session=null;savedRequest=null;location.href='/';};

async function loadSavedRun() {
  const id = new URLSearchParams(location.search).get('run');
  if (!id || !/^[a-f0-9]{16}$/.test(id)) return;
  try {
    const response = await fetch(`/api/runs/${id}`);
    if (!response.ok) throw new Error('行程未找到');
    const r = await response.json();
    for (const key of ['origin','date','people','budget','start','end','pace']) {
      const field = form.elements.namedItem(key);
      if (field && r.request[key] !== undefined) field.value = r.request[key];
    }
    document.querySelectorAll('input[name="interest"]').forEach(x => x.checked = (r.request.interests || []).includes(x.value));
    render(r);
  } catch { notice('保存的行程暂时无法打开，请根据出行条件重新规划。'); }
}
loadSavedRun();
