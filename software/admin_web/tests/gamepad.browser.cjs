// Run with Node and Playwright installed: node software/admin_web/tests/gamepad.browser.cjs
const {chromium}=require('playwright');
const http=require('node:http');
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../app/static');
(async()=>{
  const server=http.createServer((req,res)=>{
    if(req.url==='/api/mapping' || req.url==='/api/maps'){
      res.setHeader('Content-Type','application/json');return res.end(JSON.stringify(req.url==='/api/maps'?[]:{enabled:false,running:false,detail:'Captura indisponível no teste.'}));
    }
    if(req.url==='/api/destinations' || req.url==='/api/readiness'){
      res.setHeader('Content-Type','application/json');
      return res.end(JSON.stringify(req.url==='/api/destinations'?[
        {id:1,name:'Base',aliases:[],phrases:[],is_home:true,x:.025,y:.075,yaw:0},
        {id:2,name:'Sala',aliases:[],phrases:[],is_home:false,x:.075,y:.025,yaw:0}
      ]:{without_phrases:[],without_map_position:[],phrase_conflicts:[]}));
    }
    const name=req.url==='/'?'index.html':req.url.replace('/static/','');
    if(!['index.html','app.js','style.css','gamepad.js','gamepad.css','operations.js','operations.css','mapping.js','mapping.css','map-markers.js','map-markers.css'].includes(name)){res.writeHead(404);return res.end();}
    res.setHeader('Content-Type',name.endsWith('.js')?'text/javascript':name.endsWith('.css')?'text/css':'text/html');
    res.end(fs.readFileSync(path.join(root,name)));
  });
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  let browser;
  try{
    browser=await chromium.launch({headless:true, ...(process.env.GAMEPAD_BROWSER_CHANNEL ? {channel:process.env.GAMEPAD_BROWSER_CHANNEL} : {})});const page=await browser.newPage();
    const errors=[];page.on('pageerror',e=>errors.push(e.stack));
    let requests=0;
    await page.route('**/*',route=>{
      if(route.request().url().includes('/static/app.js') && !process.env.FULL_PANEL)return route.fulfill({body:'',contentType:'text/javascript'});
      requests++;return route.continue();
    });
    await page.addInitScript(()=>{
      window.pad={index:0,id:'Simulado',axes:[0,0],buttons:[{pressed:false,value:0}]};
      navigator.getGamepads=()=>window.pad?[window.pad]:[];
    });
    await page.goto(`http://127.0.0.1:${server.address().port}`);
    assert.equal(await page.locator('#view-dashboard').isVisible(),true);
    if(process.env.VISUAL_OUTPUT){await page.setViewportSize({width:960,height:760});await page.screenshot({path:process.env.VISUAL_OUTPUT,fullPage:true});}
    await page.click('[data-view="maps"]');assert.equal(await page.locator('#mapYamlFile').isVisible(),true);
    if(process.env.FULL_PANEL){
      await page.setInputFiles('#mapYamlFile',{name:'test.yaml',mimeType:'text/yaml',buffer:Buffer.from('resolution: 0.05\norigin: [0, 0, 0]\n')});
      await page.setInputFiles('#mapPgmFile',{name:'test.pgm',mimeType:'image/x-portable-graymap',buffer:Buffer.from('P2\n2 2\n255\n255 0 128 255\n')});
      await page.waitForFunction(()=>!document.querySelector('.dashboard-map canvas').hidden);
      await page.locator('#mapCanvas').scrollIntoViewIfNeeded();
      const mapBounds=await page.locator('#mapCanvas').boundingBox();
      await page.mouse.click(mapBounds.x+mapBounds.width*.4,mapBounds.y+mapBounds.height*.4);
      assert.match(await page.textContent('#mapPoint'),/X 0.025, Y 0.075/);
      assert.equal(await page.locator('.map-marker.marker-home').count(),1);
      assert.equal(await page.locator('.map-marker.marker-destination').count(),1);
      assert.equal(await page.locator('.map-marker.marker-point').count(),1);
      await page.locator('.map-marker.marker-home').click();
      assert.equal(await page.inputValue('#pointType'),'base');
      assert.equal(await page.locator('#deletePoint').isVisible(),true);
      await page.click('#closeDialog');
      await page.locator('.map-marker.marker-destination').click();
      assert.equal(await page.inputValue('#pointType'),'destination');
      await page.click('#closeDialog');
      await page.selectOption('#newPointType','base');await page.click('#newDestinationAtPoint');
      assert.equal(await page.inputValue('#pointType'),'base');
      assert.equal(await page.locator('#deletePoint').isVisible(),false);
      await page.click('#closeDialog');
      await page.click('[data-view="dashboard"]');
      assert.equal(await page.locator('.dashboard-map canvas').isVisible(),true);
      assert.equal(await page.locator('.dashboard-map canvas').getAttribute('width'),'2');
      await page.click('.dashboard-map');assert.equal(await page.locator('#view-maps').isVisible(),true);
      await page.setInputFiles('#mapYamlFile',{name:'rotated.yaml',mimeType:'text/yaml',buffer:Buffer.from('resolution: 0.05\norigin: [0, 0, 1.5707963267948966]\n')});
      await page.waitForTimeout(80);await page.locator('#mapCanvas').scrollIntoViewIfNeeded();
      const rotated=await page.locator('#mapCanvas').boundingBox();
      await page.mouse.click(rotated.x+rotated.width*.25,rotated.y+rotated.height*.25);
      assert.match(await page.textContent('#mapPoint'),/X -0.075, Y 0.025/);
      await page.setInputFiles('#mapPgmFile',{name:'invalid.pgm',mimeType:'image/x-portable-graymap',buffer:Buffer.from('invalid')});
      await page.waitForFunction(()=>document.querySelector('.dashboard-map canvas').hidden);
    }
    await page.click('[data-view="missions"]');assert.equal(await page.locator('#testForm').isVisible(),true);
    await page.click('[data-view="settings"]');assert.equal(await page.locator('#restoreFile').isVisible(),true);
    await page.click('[data-view="controls"]');
    if(process.env.CONTROL_OUTPUT)await page.screenshot({path:process.env.CONTROL_OUTPUT,fullPage:true});
    await page.click('#gamepadStart');await page.waitForFunction(()=>document.getElementById('gamepadStatus').textContent.includes('Simulado'));
    const initialRequests=requests;
    await page.locator('#gamepadMappings button').first().click();
    await page.waitForTimeout(80);
    await page.evaluate(()=>{pad.axes[0]=.9;});
    await page.waitForFunction(()=>document.getElementById('gamepadNotice').textContent.includes('capturado'));
    await page.fill('#gamepadProfileName','Teste persistente');await page.click('#gamepadSave');
    await page.reload();
    assert.equal(await page.inputValue('#gamepadProfileName'),'Teste persistente');
    assert.match(await page.textContent('#gamepadMappings'),/Eixo 0 \+/);
    await page.click('#gamepadStart');await page.waitForTimeout(80);
    await page.locator('#gamepadMappings button').nth(2).click();
    await page.waitForTimeout(80);await page.evaluate(()=>{pad.axes[0]=.9;});
    await page.waitForFunction(()=>document.getElementById('gamepadNotice').textContent.includes('já usada'));
    await page.evaluate(()=>{pad.axes=[0,0];});
    await page.locator('#gamepadMappings button').nth(2).click();await page.waitForTimeout(80);
    await page.evaluate(()=>{pad.buttons[0]={pressed:true,value:1};});
    await page.waitForFunction(()=>document.getElementById('gamepadNotice').textContent.includes('capturado'));
    await page.evaluate(()=>{pad.buttons[0]={pressed:false,value:0};});
    await page.evaluate(()=>{pad.axes=[.05,-.03];});await page.click('#gamepadCalibrate');
    await page.waitForFunction(()=>document.getElementById('gamepadNotice').textContent.includes('Centro calibrado'));
    await page.click('#gamepadSave');
    const centers=await page.evaluate(()=>{const s=JSON.parse(localStorage.getItem('onigiri.gamepad.profiles.v1'));return s.profiles[s.selected].centers;});
    assert.ok(Math.abs(centers[0]-.05)<.001);
    await page.click('#gamepadNew');await page.fill('#gamepadProfileName','Segundo');await page.click('#gamepadSave');
    await page.selectOption('#gamepadProfile','default');assert.equal(await page.inputValue('#gamepadProfileName'),'Teste persistente');
    await page.evaluate(()=>{pad=null;});
    await page.waitForFunction(()=>document.getElementById('gamepadAxes').textContent==='Sem leitura.');
    await page.click('#gamepadStop');assert.equal(await page.evaluate(()=>onigiriGamepad.active),false);
    await page.evaluate(()=>{pad={index:0,id:'Simulado',axes:[.05,0],buttons:[]};});
    await page.click('#gamepadStart');await page.waitForTimeout(80);
    assert.match(await page.textContent('#gamepadAxes'),/→ 0.00/);
    await page.click('#gamepadStop');
    await page.click('[data-view="dashboard"]');
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    await page.click('[data-view="controls"]');
    assert.equal(await page.locator('#gamepadStart').isVisible(),true);
    assert.deepEqual(errors,[]);
    // Only reload fetched resources; all input/configuration stays inside browser.
    assert.ok(requests<=initialRequests*2);
    console.log('PASS: capture, calibration, profiles/reload, disconnect, stop, no command traffic');
  }finally{if(browser)await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
