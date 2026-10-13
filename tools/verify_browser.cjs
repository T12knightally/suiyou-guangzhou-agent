// Actual Chromium browser. Screenshots replay real archived results; no model API called.
const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const root=path.resolve(__dirname,'..'),out=path.join(root,'evidence/browser');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1100}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base='http://127.0.0.1:8765',id='85fb96702ab84d8d';
 const r=await (await page.request.get(`${base}/api/runs/${id}`)).json();
 await page.goto(`${base}/?run=${id}`);await page.waitForSelector('#download');
 const text=await page.locator('body').innerText();
 assert(text.includes('14:48'));assert(text.includes('实名分时预约'));
 assert(!/LLM|function calling|qwen3|不订票|不付款/.test(text));
 await page.screenshot({path:path.join(out,'desktop.png'),fullPage:true});
 const downloadPromise=page.waitForEvent('download');await page.locator('#download').click();const download=await downloadPromise;
 const txt=fs.readFileSync(await download.path(),'utf8');assert(txt.includes('实名分时预约') && txt.includes('https://www.gdmuseum.com'));
 await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 await page.screenshot({path:path.join(out,'mobile.png'),fullPage:true});
 await page.setViewportSize({width:1440,height:1100});
 await page.goto(`${base}/review?run=${id}`);await page.waitForSelector('#events section:nth-child(24)');
 assert((await page.locator('#summary').innerText()).includes(id));
 await page.locator('#events section').nth(5).scrollIntoViewIfNeeded();
 await page.screenshot({path:path.join(out,'trace-browser.png')});
 await page.locator('#events section').nth(5).screenshot({path:path.join(out,'model-tool-call.png')});
 await page.locator('#events section').nth(7).screenshot({path:path.join(out,'weather-observation.png')});
 // Submission behavior uses explicit mocked HTTP responses; screenshots above do not.
 await page.goto(base);let posted;
 await page.route('**/api/plan',async route=>{posted=route.request().postDataJSON();await route.fulfill({json:{...r,session_id:'a'.repeat(32)}})});
 await page.locator('#submit').click();await page.waitForSelector('#download');assert.equal(posted.request.mode,'live');
 await page.locator('#followup').fill('每人80元，不去省博');await page.locator('#adjust').click();await page.waitForSelector('#download');
 assert.deepEqual(Object.keys(posted.request),['message']);assert.equal(posted.session_id,'a'.repeat(32));
 await page.unroute('**/api/plan');await page.route('**/api/plan',route=>route.fulfill({status:503,json:{error:'fixture'}}));
 await page.locator('#adjust').click(); // empty text is blocked by native form validation
 await page.locator('#followup').fill('每人80元');await page.locator('#adjust').click();await page.waitForSelector('.error');
 assert.equal(await page.locator('#adjust').isDisabled(),false);assert.deepEqual(errors,[]);
 fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify({passed:true,at:new Date().toISOString(),scope:'Actual Chromium; screenshot data replayed from genuine historical run; submit/error tests explicitly mocked',run_id:id,checks:['desktop rendering','mobile width','official booking reminder','TXT download','real archived model/tool observation rendering','live default request','message-only follow-up','HTTP failure recovery','no page errors'],api_calls:0},null,2));
 await browser.close();console.log('Browser checks passed; screenshots saved.');
})().catch(e=>{console.error(e);process.exitCode=1});
