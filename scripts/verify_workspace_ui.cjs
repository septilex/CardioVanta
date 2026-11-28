const {chromium} = require('../.visual-tools/node_modules/playwright-core');
const fs = require('fs');
(async () => {
 const browser = await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const dir='docs/viva/evidence';fs.mkdirSync(dir,{recursive:true});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 for (const [route,name] of [['/research/workspace','workspace'],['/support','support']]) {
  await page.goto('http://localhost:3011'+route);await page.waitForLoadState('networkidle');
  await page.screenshot({path:dir+'/'+name+'-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:dir+'/'+name+'-mobile.png',fullPage:true});
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error(name+' mobile overflow');
  await page.setViewportSize({width:1440,height:1000});
 }
 // Synthetic authenticated fixtures for visual QA only; real network security is tested in pytest.
 await page.route('**/api/v1/auth/status',r=>r.fulfill({json:{enabled:true,google:true}}));
 await page.route('**/api/v1/auth/refresh',r=>r.fulfill({json:{access_token:'synthetic-visual-only',user:{id:'visual',email:'researcher@example.test',roles:['admin']}}}));
 await page.goto('http://localhost:3011/research/workspace');await page.getByRole('heading',{name:'Import evaluation metrics'}).waitFor();
 await page.screenshot({path:dir+'/workspace-authenticated-desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:dir+'/workspace-authenticated-mobile.png',fullPage:true});
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('authenticated mobile overflow');
 fs.writeFileSync(dir+'/visual-check.json',JSON.stringify({desktop:[1440,1000],mobile:[390,844],pageErrors:errors,authenticated:'Synthetic browser fixture; not live login proof',horizontalOverflow:false},null,2));
 console.log(JSON.stringify({screenshots:6,pageErrors:errors,overflow:false}));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
