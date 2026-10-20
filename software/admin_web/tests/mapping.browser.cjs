const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
  const browser=await chromium.launch({headless:true,...(process.env.GAMEPAD_BROWSER_CHANNEL?{channel:process.env.GAMEPAD_BROWSER_CHANNEL}:{})});
  try{
    const page=await browser.newPage({viewport:{width:1280,height:900}});const errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    const url=process.env.MAPPING_TEST_URL;
    assert.ok(url,'Defina MAPPING_TEST_URL para um FastAPI de teste com banco e diretório de mapas temporários.');
    await page.goto(url+'/#maps');
    await page.waitForFunction(()=>document.getElementById('mappingMode').textContent==='Captura indisponível');
    assert.equal(await page.isDisabled('#mappingStart'),true);
    const name='mapa-teste-'+Date.now();
    await page.fill('#mappingName',name);
    await page.click('.mapping-import summary');
    await page.setInputFiles('#mapYamlFile',{name:'test.yaml',mimeType:'text/yaml',buffer:Buffer.from('resolution: 0.05\norigin: [0, 0, 0]\n')});
    await page.setInputFiles('#mapPgmFile',{name:'test.pgm',mimeType:'image/x-portable-graymap',buffer:Buffer.from('P2\n2 2\n255\n255 0 128 255\n')});
    await page.click('#mappingImport');
    await page.waitForFunction(()=>document.getElementById('mappingNotice').textContent.includes('salvo.'));
    await page.click('#mappingImport');
    await page.waitForFunction(()=>document.getElementById('mappingNotice').textContent.includes('Já existe'));
    await page.reload();
    await page.selectOption('#mappingLibrary',name);await page.click('#mappingOpen');
    await page.waitForFunction(()=>!document.getElementById('mapCanvas').hidden);
    await page.click('[data-view="dashboard"]');assert.equal(await page.locator('.dashboard-map canvas').isVisible(),true);
    await page.click('[data-view="maps"]');
    if(process.env.MAPPING_SCREENSHOT)await page.screenshot({path:process.env.MAPPING_SCREENSHOT,fullPage:true});
    await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    assert.deepEqual(errors,[]);
    console.log('PASS: actual FastAPI, disabled ROS, import, conflict, persistence/reload, reopen, dashboard, mobile.');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
