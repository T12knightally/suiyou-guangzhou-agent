// DOM unit harness, not a browser/rendering test. No paid API calls.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),path=require('path');
const root=path.resolve(__dirname,'..');
const summary=JSON.parse(fs.readFileSync(path.join(root,'evidence/repairs/latest.json'),'utf8'));
const saved=JSON.parse(fs.readFileSync(path.join(root,summary.evidence_dir,'conversation_2_complete.json'),'utf8'));
const nodes={};
function node(s){return nodes[s] ||= {textContent:'',innerHTML:'',value:'',hidden:true,disabled:false,setAttribute(){},removeAttribute(){},addEventListener(event,fn){this[event]=fn}};}
const fields=Object.fromEntries(Object.entries(saved.request).map(([k,v])=>[k,{value:v}]));fields.message={value:''};
node('#form').elements={namedItem:k=>fields[k]};
let posted,download;
const Url=class extends URL{};Url.createObjectURL=blob=>{download=blob;return 'blob:test'};Url.revokeObjectURL=()=>{};
const context={console,Date,Number,String,Blob,setTimeout:()=>{},URL:Url,URLSearchParams,location:{search:''},history:{replaceState(){}},window:{print(){}},document:{querySelector:node,querySelectorAll:()=>[],createElement:()=>({click(){}})},FormData:class{get(k){return fields[k]?.value}getAll(){return ['文化']}},fetch:async(url,options)=>{posted=JSON.parse(options.body);return {ok:true,json:async()=>({...saved,session_id:'a'.repeat(32),request:{...saved.request,...posted.request}})}}};
vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(root,'web/app.js'),'utf8'),context);
(async()=>{
 context.render(saved);
 assert(!/LLM|qwen3|function calling|草案|不订票|不付款|执行记录/.test(node('#result').innerHTML));
 assert(node('#result').innerHTML.includes('https://www.gdmuseum.com'));
 assert(node('#result').innerHTML.includes('实名分时预约'));
 assert(node('#result').innerHTML.includes('最晚入场 16:00'));
 assert(node('#result').innerHTML.includes('不含另行收费的特展'));
 node('#download').onclick();const txt=await download.text();assert(txt.includes('https://www.gdmuseum.com'));assert(txt.includes('实名分时预约'));assert(!txt.includes('tool_calls'));
 await node('#form').submit({preventDefault(){}});
 assert.equal(posted.request.mode,'live');assert.equal(posted.request.engine,'llm');
 node('#followup').value='每人80元，不去省博';await node('#followup-form').submit({preventDefault(){}});
 assert.deepEqual(Object.keys(posted.request),['message']);assert.equal(posted.session_id,'a'.repeat(32));
 assert.equal(node('#submit').disabled,false);assert.equal(node('#adjust').disabled,false);
 const malicious=JSON.parse(JSON.stringify(saved));malicious.plan.places[0].official_sources.push({title:'bad',url:'javascript:alert(1)'});malicious.plan.places[0].name='<img src=x onerror=alert(1)>';
 context.render(malicious);assert(!node('#result').innerHTML.includes('href="javascript:'));assert(!node('#result').innerHTML.includes('<img src=x'));
 context.render({status:'needs_input',request:saved.request,questions:['请补充出发时间']});assert(node('#result').innerHTML.includes('请补充出发时间'));assert.equal(node('#conversation').hidden,false);
 context.fetch=async()=>{throw Error('network')};await node('#form').submit({preventDefault(){}});assert.equal(node('#submit').disabled,false);assert(node('#result').innerHTML.includes('条件已保留'));
 const result={passed:true,scope:'DOM单元测试，非真实浏览器渲染',checks:['consumer wording','official links','booking and admission scope','TXT export','live submission','message-only follow-up','HTML/URL escaping','follow-up questions','network recovery'],browser_render_verified:false};
 fs.writeFileSync(path.join(root,'evidence/ui-checks.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
})().catch(e=>{console.error(e);process.exitCode=1});
