const id=new URLSearchParams(location.search).get('run');
document.querySelector('#print').onclick=()=>window.print();
(async()=>{
 if(!/^[a-f0-9]{16}$/.test(id || ''))throw Error('请提供有效的运行ID');
 const response=await fetch(`/api/runs/${id}`);if(!response.ok)throw Error('运行记录未找到');
 const r=await response.json();
 document.querySelector('#summary').textContent=`运行 ${r.run_id} | ${r.status} | ${r.request.mode === 'live' ? '真实外部接口' : '合成外部数据'} | ${r.usage.model_calls} 次模型响应 | ${r.duration_ms} ms | ${r.trace.length} 个事件`;
 document.querySelector('#raw').href=`/api/runs/${id}`;document.querySelector('#trip').href=`/?run=${id}`;
 for(const t of r.trace){
  const section=document.createElement('section'),title=document.createElement('h2'),body=document.createElement('pre');
  title.textContent=`#${t.seq} ${t.type === 'Tool' ? t.action : 'Decision'}${t.type === 'Tool' ? (t.ok ? ' · 成功' : ' · 失败') : ''}`;
  body.textContent=t.type === 'Tool' ? JSON.stringify({at:t.at,arguments:t.arguments,observation:t.observation,duration_ms:t.duration_ms},null,2) : t.summary;
  section.append(title,body);document.querySelector('#events').append(section);
 }
})().catch(e=>{document.querySelector('#summary').textContent=e.message});
