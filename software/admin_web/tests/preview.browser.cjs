const {chromium}=require('playwright');
const fs=require('node:fs'),http=require('node:http'),path=require('node:path'),assert=require('node:assert/strict');
const root=process.env.PREVIEW_STATIC_DIR||path.resolve(__dirname,'../app/static');
let preview={state:'waiting',detail:'Aguardando /map.'},previewRequests=0;
const server=http.createServer((req,res)=>{
  const api={
    '/api/mapping':{enabled:true,running:true,profile:'experimental-default',detail:'SLAM experimental.'},
    '/api/maps':[], '/api/destinations':[],
    '/api/readiness':{without_phrases:[],without_map_position:[],phrase_conflicts:[]}
  };
  if(req.url.startsWith('/api/mapping/preview')){
    previewRequests++;const payload={...preview};
    if(new URL(req.url,'http://localhost').searchParams.get('after')===String(preview.changed_at??preview.received_at))delete payload.png_base64;
    res.setHeader('Content-Type','application/json');return res.end(JSON.stringify(payload));
  }
  if(api[req.url]){res.setHeader('Content-Type','application/json');return res.end(JSON.stringify(api[req.url]));}
  const name=req.url==='/'?'index.html':req.url.replace('/static/','');
  if(!/^[a-z.-]+\.(js|css|html)$/.test(name)){res.writeHead(404);return res.end();}
  res.setHeader('Content-Type',name.endsWith('.js')?'text/javascript':name.endsWith('.css')?'text/css':'text/html');res.end(fs.readFileSync(path.join(root,name)));
});
(async()=>{
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  const browser=await chromium.launch({headless:true,...(process.env.GAMEPAD_BROWSER_CHANNEL?{channel:process.env.GAMEPAD_BROWSER_CHANNEL}:{})});
  try{
    const page=await browser.newPage({viewport:{width:1280,height:950}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(`http://127.0.0.1:${server.address().port}/#maps`);
    await page.waitForFunction(()=>document.getElementById('liveMapBadge').textContent==='Aguardando mapa');
    preview={state:'live',detail:'Recebendo mapa do SLAM.',width:2,height:2,resolution:.05,received_at:1,age_seconds:0,...JSON.parse(fs.readFileSync(path.join(__dirname,'preview-fixture.json')))};
    await page.waitForFunction(()=>!document.getElementById('liveMapCanvas').hidden);
    const pixels=await page.evaluate(()=>Array.from(document.getElementById('liveMapCanvas').getContext('2d').getImageData(0,0,2,2).data));
    assert.equal(pixels[0],205);assert.equal(pixels[8],255);assert.equal(pixels[12],0);
    await page.click('#liveMapZoomIn');assert.equal(await page.textContent('#liveMapZoom'),'125%');
    const viewport=page.locator('#liveMapViewport'),box=await viewport.boundingBox();
    await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2+50,box.y+box.height/2+20);await page.mouse.up();
    assert.match(await page.locator('#liveMapCanvas').getAttribute('style'),/translate\(50px, 20px\)/);
    const originalStyle=await page.locator('#liveMapCanvas').getAttribute('style');
    preview={...preview,received_at:2};await page.waitForTimeout(1800);
    assert.equal(await page.locator('#liveMapCanvas').getAttribute('style'),originalStyle);
    await page.mouse.wheel(0,-100);assert.notEqual(await page.textContent('#liveMapZoom'),'125%');
    await page.click('#liveMapFit');assert.equal(await page.textContent('#liveMapZoom'),'100%');
    assert.match(await page.locator('#liveMapCanvas').getAttribute('style'),/translate\(0px, 0px\)/);
    await viewport.focus();await page.keyboard.press('+');assert.equal(await page.textContent('#liveMapZoom'),'125%');
    await page.keyboard.press('0');assert.equal(await page.textContent('#liveMapZoom'),'100%');
    if(process.env.PREVIEW_SCREENSHOT)await page.screenshot({path:process.env.PREVIEW_SCREENSHOT,fullPage:true});
    preview={...preview,state:'stale',detail:'Sem atualização recente.',age_seconds:30};
    await page.waitForFunction(()=>document.getElementById('liveMapBadge').textContent==='Sem atualização');
    assert.equal(await page.locator('#liveMapCanvas').isVisible(),true);
    preview={state:'idle',detail:'Inicie o mapeamento.'};
    await page.waitForFunction(()=>document.getElementById('liveMapCanvas').hidden);
    await page.click('[data-view="dashboard"]');await page.waitForTimeout(200);const count=previewRequests;
    await page.waitForTimeout(1700);assert.equal(previewRequests,count);
    await page.setViewportSize({width:390,height:844});await page.click('[data-view="maps"]');
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    let startPayload=null;
    await page.route('**/api/mapping',route=>route.fulfill({json:{enabled:true,running:false,profile:'configured',detail:'Pronto.'}}));
    await page.route('**/api/mapping/start',route=>{startPayload=route.request().postDataJSON();return route.fulfill({json:{running:true,profile:'stationary-preview'}});});
    await page.waitForFunction(()=>!document.getElementById('mappingStationary').disabled);
    await page.click('.mapping-options summary');
    await page.check('#mappingStationary');
    assert.equal(await page.isChecked('#mappingExperimental'),true);
    assert.equal(await page.locator('#stationaryNotice').isVisible(),true);
    await page.click('#mappingStart');
    await page.waitForFunction(()=>document.getElementById('mappingNotice').textContent.includes('Início solicitado'));
    assert.deepEqual(startPayload,{experimental:true,stationary:true,lidar_odometry:false});
    await page.route('**/api/mapping',route=>route.fulfill({json:{enabled:true,running:false,lidar_odometry_enabled:true,profile:'configured',detail:'Pronto.'}}));
    await page.waitForFunction(()=>!document.getElementById('mappingLidarOdometry').disabled);
    await page.check('#mappingLidarOdometry');assert.equal(await page.isChecked('#mappingStationary'),false);
    await page.click('#mappingStart');
    await page.waitForTimeout(100);
    assert.deepEqual(startPayload,{experimental:true,stationary:false,lidar_odometry:true});
    assert.deepEqual(errors,[]);console.log('PASS: live PNG, pixel orientation, stale, stop, hidden view polling, mobile.');
  }finally{await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;server.close();});
