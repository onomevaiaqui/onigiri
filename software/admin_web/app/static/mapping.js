/* Mapping controls: server-side map library and explicitly configured ROS capture. */
(() => {
  const view=document.getElementById('view-maps');
  const panel=document.createElement('section');panel.className='panel mapping-panel';
  panel.innerHTML=`<div class="panel-heading"><div><h3>Mapear ambiente</h3><p>Controle a captura e guarde seu mapa.</p></div><span id="mappingMode" class="simulation-badge">Verificando</span></div>
    <p id="mappingStatus" role="status">Consultando serviço…</p>
    <div class="mapping-actions"><button id="mappingStart" type="button" class="primary" disabled>Iniciar mapeamento</button><button id="mappingStop" type="button" class="secondary" disabled>Encerrar</button></div>
    <details class="mapping-options"><summary>Modo de captura</summary>
      <label class="mapping-experimental"><input id="mappingExperimental" type="checkbox" />Parâmetros padrão — experimental</label>
      <label class="mapping-experimental"><input id="mappingStationary" type="checkbox" />Teste parado — sem odometria</label>
      <label class="mapping-experimental"><input id="mappingLidarOdometry" type="checkbox" disabled />Odometria pelo LiDAR — experimental</label>
      <p id="lidarOdometryHelp" class="mapping-help">Requer a instalação opcional do RF2O no Raspberry.</p>
      <p class="mapping-help">Para mapear em movimento, use TF e odometria reais.</p>
    </details>
    <p id="stationaryNotice" class="mapping-caution" hidden>Teste parado ativo. Mantenha o robô imóvel; este mapa não serve para navegação.</p>
    <div class="mapping-save-section"><h4>Salvar mapa</h4>
      <form id="mappingSaveForm"><label>Nome<input id="mappingName" required maxlength="60" pattern="[a-zA-Z0-9][a-zA-Z0-9_-]{0,59}" placeholder="Ex.: casa-terreo" /></label><button id="mappingSave" type="submit" class="primary" disabled>Salvar mapa</button></form>
      <p id="mappingNotice" role="status"></p>
    </div>
    <div class="mapping-saved-section"><h4>Mapas salvos</h4><div class="mapping-library"><label class="sr-label" for="mappingLibrary">Escolher mapa</label><select id="mappingLibrary"><option value="">Carregando…</option></select><button id="mappingOpen" type="button" class="secondary">Abrir</button></div></div>
    <details class="mapping-import"><summary>Importar mapa existente</summary><p class="mapping-help">Selecione os arquivos YAML e PGM na área abaixo e preencha o nome acima.</p><button id="mappingImport" type="button" class="secondary">Guardar arquivos selecionados</button></details>`;
  view.querySelector('.intro').after(panel);
  const live=document.createElement('section');live.className='panel mapping-live';
  live.innerHTML='<div class="panel-heading"><div><h3>Prévia do mapeamento</h3><p>Branco: livre · preto: ocupado · cinza: desconhecido. Sem posição do robô.</p></div><span id="liveMapBadge">Aguardando</span></div><p id="liveMapStatus" role="status">Inicie o mapeamento para visualizar.</p><div class="live-map-toolbar" aria-label="Controles da prévia"><button id="liveMapZoomOut" type="button" class="secondary" aria-label="Reduzir zoom">−</button><output id="liveMapZoom">100%</output><button id="liveMapZoomIn" type="button" class="secondary" aria-label="Ampliar zoom">+</button><button id="liveMapFit" type="button" class="secondary">Ajustar à área</button></div><div class="live-map-workspace" id="liveMapViewport" tabindex="0" role="region" aria-label="Prévia interativa: arraste para mover, use a roda para zoom"><canvas id="liveMapCanvas" hidden aria-label="Mapa publicado ao vivo pelo SLAM"></canvas><p id="liveMapEmpty">Nenhum mapa recebido.</p></div><p class="live-map-hint">Arraste para mover · roda do mouse ou pinça para zoom · clique duplo para ajustar</p><p id="liveMapInfo"></p>';
  const workspace=document.createElement('div');workspace.className='mapping-workbench';
  panel.before(workspace);workspace.append(panel,live);
  const $=id=>document.getElementById(id);
  let busy=false, timer=null;
  let liveVersion=null, liveRequest=false;
  let zoom=1,panX=0,panY=0;
  const viewport=$('liveMapViewport'),previewCanvas=$('liveMapCanvas');
  function renderView(){
    previewCanvas.style.transform=`translate(${panX}px, ${panY}px) scale(${zoom})`;
    $('liveMapZoom').textContent=Math.round(zoom*100)+'%';
  }
  function resetView(){zoom=1;panX=panY=0;renderView();}
  function zoomAt(factor,x=0,y=0){
    if(previewCanvas.hidden)return;
    const next=Math.max(.25,Math.min(12,zoom*factor)),ratio=next/zoom;
    panX=x-(x-panX)*ratio;panY=y-(y-panY)*ratio;zoom=next;renderView();
  }
  $('liveMapZoomIn').onclick=()=>zoomAt(1.25);
  $('liveMapZoomOut').onclick=()=>zoomAt(.8);
  $('liveMapFit').onclick=resetView;
  viewport.addEventListener('wheel',event=>{
    if(previewCanvas.hidden)return;
    event.preventDefault();const bounds=viewport.getBoundingClientRect();
    zoomAt(Math.exp(-Math.max(-200,Math.min(200,event.deltaY))*.003),event.clientX-bounds.left-bounds.width/2,event.clientY-bounds.top-bounds.height/2);
  },{passive:false});
  const pointers=new Map();let pinchDistance=null;
  viewport.addEventListener('pointerdown',event=>{
    if(previewCanvas.hidden||event.button!==0)return;
    event.preventDefault();viewport.focus({preventScroll:true});viewport.setPointerCapture(event.pointerId);
    pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});viewport.classList.add('dragging');
    if(pointers.size===2){const [a,b]=[...pointers.values()];pinchDistance=Math.hypot(a.x-b.x,a.y-b.y);}
  });
  viewport.addEventListener('pointermove',event=>{
    const old=pointers.get(event.pointerId);if(!old)return;
    pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});
    if(pointers.size===1){panX+=event.clientX-old.x;panY+=event.clientY-old.y;renderView();}
    else if(pointers.size===2){
      const [a,b]=[...pointers.values()],distance=Math.hypot(a.x-b.x,a.y-b.y),bounds=viewport.getBoundingClientRect();
      if(pinchDistance>0)zoomAt(distance/pinchDistance,(a.x+b.x)/2-bounds.left-bounds.width/2,(a.y+b.y)/2-bounds.top-bounds.height/2);
      pinchDistance=distance;
    }
  });
  function release(event){pointers.delete(event.pointerId);pinchDistance=null;if(!pointers.size)viewport.classList.remove('dragging');}
  viewport.addEventListener('pointerup',release);viewport.addEventListener('pointercancel',release);viewport.addEventListener('lostpointercapture',release);
  viewport.addEventListener('dblclick',resetView);
  viewport.addEventListener('keydown',event=>{
    if(previewCanvas.hidden)return;
    if(['+','=','-','0','ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key))event.preventDefault();
    if(event.key==='+'||event.key==='=')zoomAt(1.25);
    else if(event.key==='-')zoomAt(.8);
    else if(event.key==='0')resetView();
    else {const delta={ArrowLeft:[40,0],ArrowRight:[-40,0],ArrowUp:[0,40],ArrowDown:[0,-40]}[event.key];if(delta){panX+=delta[0];panY+=delta[1];renderView();}}
  });
  renderView();

  const notice=text=>{$('mappingNotice').textContent=text;};
  async function request(url,options={}){
    const response=await fetch(url,{headers:{'Content-Type':'application/json'},...options});
    const body=await response.json();if(!response.ok)throw new Error(body.detail||'Operação indisponível.');return body;
  }
  async function refresh(){
    try{
      const status=await request('/api/mapping');
      $('mappingStatus').textContent=status.running ? (status.profile==='lidar-odometry'?'Captura ativa · odometria LiDAR':status.profile==='stationary-preview'?'Captura ativa · teste parado':status.profile==='experimental-default'?'Captura ativa · experimental':'Captura ativa') : status.detail;
      $('mappingMode').textContent=status.enabled?'Captura ROS':'Captura indisponível';
      $('mappingMode').dataset.enabled=String(status.enabled);
      $('mappingStart').disabled=busy||!status.enabled||status.running;
      $('mappingStop').disabled=busy||!status.running;
      $('mappingSave').disabled=busy||!status.running;
      $('mappingExperimental').disabled=busy||status.running;
      $('mappingStationary').disabled=busy||status.running;
      $('mappingLidarOdometry').disabled=busy||status.running||!status.lidar_odometry_enabled;
      $('lidarOdometryHelp').textContent=status.lidar_odometry_enabled?'Rastreia o movimento do sensor. Mantenha o LiDAR nivelado e fixo ao robô; ainda não valida navegação.':'Requer instalar RF2O no Raspberry com o instalador opcional de odometria.';
      if(status.running){
        $('mappingExperimental').checked=['experimental-default','stationary-preview','lidar-odometry'].includes(status.profile);
        $('mappingStationary').checked=status.profile==='stationary-preview';
        $('mappingLidarOdometry').checked=status.profile==='lidar-odometry';
      }
      $('stationaryNotice').hidden=!$('mappingStationary').checked;
    }catch(error){$('mappingStatus').textContent=error.message;['mappingStart','mappingStop','mappingSave'].forEach(id=>{$(id).disabled=true;});}
  }
  async function library(){
    const selected=$('mappingLibrary').value;
    const maps=await request('/api/maps');
    $('mappingLibrary').replaceChildren(new Option(maps.length?'Selecione um mapa':'Nenhum mapa salvo',''),...maps.map(m=>new Option(`${m.name} · ${m.profile==='lidar-odometry'?'odometria LiDAR':m.profile==='stationary-preview'?'teste parado':m.profile==='experimental-default'?'experimental':m.source==='ros'?'ROS':'importado'}`,m.name)));
    if(maps.some(m=>m.name===selected))$('mappingLibrary').value=selected;
  }
  async function refreshPreview(){
    if(liveRequest)return;liveRequest=true;
    const canvas=$('liveMapCanvas');
    try{
      const data=await request('/api/mapping/preview'+(liveVersion===null?'':'?after='+encodeURIComponent(liveVersion)));
      $('liveMapStatus').textContent=data.detail;
      const labels={live:'Ao vivo',stale:'Sem atualização',waiting:'Aguardando mapa',idle:'Parado',disabled:'Indisponível',error:'Erro na prévia'};
      $('liveMapBadge').textContent=labels[data.state]||'Aguardando';
      $('liveMapBadge').dataset.state=data.state;
      if(!['live','stale'].includes(data.state)){
        canvas.hidden=true;$('liveMapEmpty').hidden=false;$('liveMapInfo').textContent='';liveVersion=null;resetView();return;
      }
      const version=data.changed_at??data.received_at;
      if(data.png_base64 && liveVersion!==version){
        const image=new Image();image.src='data:image/png;base64,'+data.png_base64;
        await image.decode();canvas.width=data.width;canvas.height=data.height;
        canvas.getContext('2d').drawImage(image,0,0);liveVersion=version;
      }
      canvas.hidden=false;$('liveMapEmpty').hidden=true;
      if(data.state==='live'&&data.changed_age_seconds>15)$('liveMapStatus').textContent='Recebendo mensagens; o conteúdo do mapa permanece igual. No Teste parado, o deslocamento físico não é medido.';
      $('liveMapInfo').textContent=`${data.width} × ${data.height} células · ${Number(data.resolution.toFixed(3))} m/célula · mensagem há ${data.age_seconds}s${data.changed_age_seconds!==undefined?` · alteração há ${data.changed_age_seconds}s`:""}`;
    }catch(error){
      $('liveMapStatus').textContent='Conexão da prévia indisponível. '+error.message;
      $('liveMapBadge').textContent='Sem conexão';$('liveMapBadge').dataset.state='error';
    }finally{liveRequest=false;}
  }
  async function run(task){
    if(busy)return;busy=true;
    panel.querySelectorAll('button').forEach(button=>{button.disabled=true;});
    notice('Processando…');
    try{await task();}catch(error){notice(error.message);}
    finally{busy=false;panel.querySelectorAll('button').forEach(button=>{button.disabled=false;});await refresh();}
  }
  $('mappingStationary').onchange=()=>{
    $('stationaryNotice').hidden=!$('mappingStationary').checked;
    if($('mappingStationary').checked){$('mappingExperimental').checked=true;$('mappingLidarOdometry').checked=false;}
  };
  $('mappingLidarOdometry').onchange=()=>{
    if($('mappingLidarOdometry').checked){$('mappingStationary').checked=false;$('mappingExperimental').checked=true;$('stationaryNotice').hidden=true;}
  };
  $('mappingStart').onclick=()=>run(async()=>{await request('/api/mapping/start',{method:'POST',body:JSON.stringify({experimental:$('mappingExperimental').checked,stationary:$('mappingStationary').checked,lidar_odometry:$('mappingLidarOdometry').checked})});notice('Início solicitado. Verifique o estado da captura.');});
  $('mappingStop').onclick=()=>run(async()=>{await request('/api/mapping/stop',{method:'POST'});notice('Mapeamento encerrado. Os mapas salvos foram mantidos.');});
  async function save(imported){
    if(!$('mappingName').reportValidity())return;
    const data={name:$('mappingName').value};
    if(imported){
      const yaml=$('mapYamlFile').files[0],pgm=$('mapPgmFile').files[0];
      if(!yaml||!pgm)throw new Error('Selecione os dois arquivos YAML e PGM na área de mapa abaixo.');
      if(pgm.size>12000000||yaml.size>100000)throw new Error('Limite: PGM de 12 MB e YAML de 100 KB.');
      data.yaml=await yaml.text();
      const bytes=new Uint8Array(await pgm.arrayBuffer());let binary='';
      for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));
      data.pgm_base64=btoa(binary);
    }
    await request('/api/maps',{method:'POST',body:JSON.stringify(data)});
    await library();$('mappingLibrary').value=data.name;
    notice(`Mapa “${data.name}” salvo. Use Abrir mapa para visualizar.`);
  }
  $('mappingSaveForm').onsubmit=event=>{event.preventDefault();run(()=>save(false));};
  $('mappingImport').onclick=()=>run(()=>save(true));
  $('mappingOpen').onclick=()=>run(async()=>{
    const name=$('mappingLibrary').value;if(!name)throw new Error('Selecione um mapa salvo.');
    const map=await request(`/api/maps/${encodeURIComponent(name)}`);
    const bytes=Uint8Array.from(atob(map.pgm_base64),c=>c.charCodeAt(0));
    const yaml=new DataTransfer(),pgm=new DataTransfer();
    yaml.items.add(new File([map.yaml],`${name}.yaml`,{type:'text/yaml'}));
    pgm.items.add(new File([bytes],`${name}.pgm`,{type:'image/x-portable-graymap'}));
    $('mapYamlFile').files=yaml.files;$('mapPgmFile').files=pgm.files;
    $('mapPgmFile').dataset.savedMapName=name;
    $('mapPgmFile').dispatchEvent(new Event('change',{bubbles:true}));
    notice(`Mapa “${name}” aberto. ${map.profile==='lidar-odometry'?'Mapa experimental com odometria do sensor, não validado para navegação. ':map.profile==='stationary-preview'?'Teste parado com TF fixas, não usar para navegação. ':map.profile==='experimental-default'?'Mapa experimental, não validado para navegação. ':''}A posição do robô não está conectada.`);
  });
  let statusCheckedAt=0,statusRefreshing=false;
  function poll(){
    clearTimeout(timer);if(view.hidden)return;
    if(!statusRefreshing&&Date.now()-statusCheckedAt>2000){
      statusCheckedAt=Date.now();statusRefreshing=true;refresh().finally(()=>{statusRefreshing=false;});
    }
    refreshPreview().finally(()=>{if(!view.hidden)timer=setTimeout(poll,400);});
  }
  new MutationObserver(()=>{if(!view.hidden)poll();else clearTimeout(timer);}).observe(view,{attributes:true,attributeFilter:['hidden']});
  refresh();library().catch(error=>notice(error.message));if(!view.hidden)poll();
})();
