const {chromium}=require('playwright');const assert=require('node:assert/strict');
(async()=>{
  assert.ok(process.env.POINTS_TEST_URL,'Use um servidor FastAPI de teste com banco temporário.');
  const browser=await chromium.launch({headless:true,...(process.env.GAMEPAD_BROWSER_CHANNEL?{channel:process.env.GAMEPAD_BROWSER_CHANNEL}:{})});
  try{
    const page=await browser.newPage({viewport:{width:1400,height:950}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(process.env.POINTS_TEST_URL+'/#maps');
    const originalHome=(await (await page.request.get(process.env.POINTS_TEST_URL+'/api/destinations')).json()).find(d=>d.is_home);
    await page.setInputFiles('#mapYamlFile',{name:'a.yaml',mimeType:'text/yaml',buffer:Buffer.from('resolution: 0.05\norigin: [0, 0, 0]\n')});
    await page.setInputFiles('#mapPgmFile',{name:'a.pgm',mimeType:'image/x-portable-graymap',buffer:Buffer.from('P2\n2 2\n255\n255 255 255 255\n')});
    await page.locator('#mapCanvas').waitFor({state:'visible'});
    await page.locator('#mapCanvas').click({position:{x:100,y:100}});
    await page.selectOption('#newPointType','destination');await page.click('#newDestinationAtPoint');
    const name='ponto-e2e-'+Date.now();await page.fill('#name',name);await page.locator('#destinationForm button[type=submit]').click();
    await page.locator('#destinationDialog').waitFor({state:'hidden'});
    let marker=page.getByRole('button',{name:'Destino: '+name,exact:true});await marker.click();
    assert.equal(await page.inputValue('#pointType'),'destination');
    await page.fill('#name',name+'-editado');await page.locator('#destinationForm button[type=submit]').click();
    await page.locator('#destinationDialog').waitFor({state:'hidden'});
    marker=page.getByRole('button',{name:'Destino: '+name+'-editado',exact:true});await marker.click();
    await page.click('#deletePoint');await page.click('#confirmDeletePoint');
    await page.locator('#destinationDialog').waitFor({state:'hidden'});assert.equal(await marker.count(),0);
    assert.equal(await page.locator('.map-marker.marker-point').count(),0);
    await page.locator('#mapCanvas').click({position:{x:100,y:100}});
    await page.click('#newDestinationAtPoint');await page.selectOption('#pointType','base');await page.fill('#name',name+'-base');
    await page.locator('#destinationForm button[type=submit]').click();await page.locator('#destinationDialog').waitFor({state:'hidden'});
    const items=await (await page.request.get(process.env.POINTS_TEST_URL+'/api/destinations')).json();
    assert.equal(items.filter(d=>d.is_home).length,1);assert.equal(items.find(d=>d.is_home).name,name+'-base');
    assert.equal(items.find(d=>d.id===originalHome.id).is_home,false);
    await page.getByRole('button',{name:'Base: '+name+'-base',exact:true}).click();assert.equal(await page.inputValue('#pointType'),'base');
    await page.click('#deletePoint');await page.click('#confirmDeletePoint');
    assert.match(await page.textContent('#deletePointError'),/base substituta/);
    await page.selectOption('#replacementBase',String(originalHome.id));await page.click('#confirmDeletePoint');
    await page.locator('#destinationDialog').waitFor({state:'hidden'});
    const remaining=await (await page.request.get(process.env.POINTS_TEST_URL+'/api/destinations')).json();
    assert.equal(remaining.some(p=>p.name===name+'-base'),false);assert.equal(remaining.find(p=>p.id===originalHome.id).is_home,true);
    assert.deepEqual(errors,[]);console.log('PASS: real API create/edit/delete via markers, fractional coordinates, choose base, previous base demoted.');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
