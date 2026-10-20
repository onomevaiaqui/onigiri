/* Navigation and presentation only; no robot connection. */
(() => {
  const main=document.querySelector('main');
  const paths={dashboard:'Dashboard',controls:'Controle remoto',maps:'Mapas e destinos',missions:'Missões',sensors:'Sensores',settings:'Configurações'};
  const icons={dashboard:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="4" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="11" width="7" height="10" rx="1"/>',controls:'<path d="M7 7h10c3 0 4 3 4 6v3c0 3-2 4-4 1l-1-1H8l-1 1c-2 3-4 2-4-1v-3c0-3 1-6 4-6Z"/><path d="M6 11h4m-2-2v4m7-2h.01m3 2h.01"/>',maps:'<path d="m3 5 6-2 6 2 6-2v16l-6 2-6-2-6 2Zm6-2v16m6-14v16"/>',missions:'<circle cx="6" cy="18" r="3"/><circle cx="18" cy="6" r="3"/><path d="M6 15V9a3 3 0 0 1 6 0v6a3 3 0 0 0 6 0V9"/>',sensors:'<circle cx="12" cy="12" r="1"/><path d="M8 8a6 6 0 0 0 0 8m8-8a6 6 0 0 1 0 8M5 5a10 10 0 0 0 0 14M19 5a10 10 0 0 1 0 14"/>',settings:'<path d="m9 3-1 3-3 1 1 3-2 2 2 2-1 3 3 1 1 3h6l1-3 3-1-1-3 2-2-2-2 1-3-3-1-1-3Z"/><circle cx="12" cy="12" r="3"/>',robot:'<rect x="5" y="7" width="14" height="13" rx="4"/><path d="M12 3v4m-4 5h1m6 0h1m-7 4h6M2 11h3m14 0h3"/>'};
  const svg=key=>`<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[key]}</svg>`;
  const shell=document.createElement('div');shell.className='operations-shell';
  const sidebar=document.createElement('nav');sidebar.className='sidebar';sidebar.setAttribute('aria-label','Navegação principal');
  const content=document.createElement('div');content.className='operations-content';
  const views={};
  Object.entries(paths).forEach(([key,title])=>{
    const button=document.createElement('button');button.type='button';button.dataset.view=key;
    const icon=document.createElement('span');icon.setAttribute('aria-hidden','true');icon.innerHTML=svg(key);
    button.append(icon,title);button.onclick=()=>navigate(key);sidebar.append(button);
    const section=document.createElement('section');section.id=`view-${key}`;section.className='operation-view';section.hidden=true;
    const h=document.createElement('h2');h.textContent=title;h.tabIndex=-1;section.append(h);views[key]=section;content.append(section);
  });
  views.dashboard.insertAdjacentHTML('beforeend',`<div class="dashboard-cards">
    <article class="summary-card"><span aria-hidden="true">♙</span><p>Robô</p><strong>Desconectado</strong></article>
    <article class="summary-card"><span aria-hidden="true">♧</span><p>Operação</p><strong>Simulação</strong></article>
    <article class="summary-card"><span aria-hidden="true">♧</span><p>Controle</p><strong id="dashboardGamepad">Não verificado</strong></article>
    <article class="summary-card"><span aria-hidden="true">◉</span><p>Sensores</p><strong>Sem telemetria</strong></article>
    </div><button class="dashboard-map" type="button"><span aria-hidden="true">▥</span>Visualização do mapa / robô<small>Carregue um mapa em Mapas e destinos</small></button>
    <div class="activity-heading">Atividades recentes <span aria-hidden="true">☷</span></div><ul id="operationActivity" class="operation-activity"><li>Painel iniciado em simulação. Nenhuma conexão com o robô.</li></ul>`);
  views.dashboard.querySelector('.dashboard-map').onclick=()=>navigate('maps');
  const intro=document.querySelector('.intro'), map=document.querySelector('.map-panel'), layout=document.querySelector('.layout');
  const destinations=document.querySelector('.destinations-panel'), right=document.querySelector('.right-column');
  const mission=right.querySelector('.panel'), settings=right.querySelector('.note');
  const destinationWorkspace=document.createElement('div');destinationWorkspace.className='destination-workbench';
  destinationWorkspace.append(map,destinations);
  views.maps.append(intro,destinationWorkspace);views.missions.append(mission);views.settings.append(settings);
  views.controls.append(document.getElementById('gamepadPanel'));
  views.sensors.insertAdjacentHTML('beforeend','<div class="panel unavailable"><span aria-hidden="true">◉</span><h3>Aguardando integração de sensores</h3><p>Não há telemetria conectada. Os dados de LiDAR, bateria e odometria aparecerão aqui quando a integração estiver disponível.</p><span class="simulation-badge">Simulação</span></div>');
  views.settings.insertAdjacentHTML('afterbegin','<p class="view-description">Revise o cadastro e restaure backups. Os perfis do controle ficam na área Controle remoto.</p>');
  layout.remove();shell.append(sidebar,content);main.replaceChildren(shell);
  // Fit the actual canvas element, preserving its bounds for click-to-map coordinates.
  const savedCanvas=document.getElementById('mapCanvas');
  const savedArea=savedCanvas.parentElement;
  function fitSavedMap(){
    if(savedCanvas.hidden || !savedCanvas.width || !savedCanvas.height)return;
    const width=savedArea.clientWidth-24,height=savedArea.clientHeight-24;
    if(width<=0||height<=0)return;
    const scale=Math.min(width/savedCanvas.width,height/savedCanvas.height);
    savedCanvas.style.width=(savedCanvas.width*scale)+'px';
    savedCanvas.style.height=(savedCanvas.height*scale)+'px';
  }
  new ResizeObserver(fitSavedMap).observe(savedArea);
  new MutationObserver(()=>queueMicrotask(fitSavedMap)).observe(savedCanvas,{attributes:true,attributeFilter:['hidden','width','height']});
  // Keep the original inputs and listeners while grouping them into clear cards.
  const controlPanel=document.getElementById('gamepadPanel');
  const controlIntro=controlPanel.querySelector('.panel-heading');
  controlIntro.querySelector('h3').textContent='Monitoramento e configuração';
  const connection=document.createElement('section');connection.className='control-connection';
  const statusEl=document.getElementById('gamepadStatus');
  const help=statusEl.nextElementSibling,device=help.nextElementSibling;
  connection.append(statusEl,help,device,controlPanel.querySelector('.panel-actions'));
  controlIntro.after(connection);
  const grid=document.createElement('div');grid.className='control-grid';
  const monitor=document.createElement('section');monitor.className='control-monitor';
  monitor.innerHTML='<h3>Monitor ao vivo</h3><p class="control-hint">Os indicadores acompanham os eixos 0–3. O mapeamento pode variar entre controles.</p><div class="stick-pair"><div><div class="stick-area" id="stickLeft"><span></span></div><p>Eixos 0 / 1</p></div><div><div class="stick-area" id="stickRight"><span></span></div><p>Eixos 2 / 3</p></div></div>';
  ['gamepadAxes','gamepadButtons'].forEach(id=>{const el=document.getElementById(id);monitor.append(el.previousElementSibling,el);});
  const profileCard=document.createElement('section');profileCard.className='control-profile';
  profileCard.append(controlPanel.querySelector('fieldset'));
  grid.append(monitor,profileCard);connection.after(grid);
  const mappingCard=document.createElement('section');mappingCard.className='control-mapping-card';
  const mappingEl=document.getElementById('gamepadMappings'),mappingHelp=mappingEl.previousElementSibling,mappingTitle=mappingHelp.previousElementSibling;
  mappingCard.append(mappingTitle,mappingHelp,mappingEl);grid.after(mappingCard);
  function resetSticks(){document.querySelectorAll('.stick-area span').forEach(dot=>{dot.style.transform='translate(0px, 0px)';});}
  window.addEventListener('onigiri:gamepad',e=>{
    ['stickLeft','stickRight'].forEach((id,i)=>{
      const axes=e.detail.axes;
      document.querySelector(`#${id} span`).style.transform=`translate(${(axes[i*2]||0)*35}px, ${(axes[i*2+1]||0)*35}px)`;
    });
  });
  new MutationObserver(()=>{if(!statusEl.textContent.startsWith('Controle detectado:'))resetSticks();}).observe(statusEl,{childList:true});


  const top=document.querySelector('.topbar');
  top.innerHTML='<div class="brand"><span class="brand-icon" aria-hidden="true">♙</span><div><h1>ONIGIRI</h1><p>Central de Operações</p></div></div><p class="simulation-badge">Simulação</p>';
  top.querySelector('.brand-icon').innerHTML=svg('robot');
  views.dashboard.querySelectorAll('.summary-card>span').forEach((el,i)=>{el.innerHTML=svg(['robot','settings','controls','sensors'][i]);});
  views.dashboard.querySelector('.dashboard-map>span').innerHTML=svg('maps');
  views.sensors.querySelector('.unavailable>span').innerHTML=svg('sensors');
  function navigate(key,focus=true){
    if(!views[key])key='dashboard';
    Object.entries(views).forEach(([id,section])=>{section.hidden=id!==key;});
    sidebar.querySelectorAll('button').forEach(b=>{if(b.dataset.view===key)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});
    if(key!=='controls' && window.onigiriGamepad?.active)window.onigiriGamepad.stop();
    history.replaceState(null,'',`#${key}`);
    if(focus)views[key].querySelector('h2').focus({preventScroll:true});
  }
  let lastActivity='';
  const status=document.getElementById('gamepadStatus');
  new MutationObserver(()=>{
    const text=status.textContent;
    document.getElementById('dashboardGamepad').textContent=text.startsWith('Controle detectado:')?'Detectado':text.includes('interrompido')?'Teste parado':'Não detectado';
    if(text!==lastActivity){
      lastActivity=text;const li=document.createElement('li');li.textContent=text;
      const list=document.getElementById('operationActivity');list.prepend(li);while(list.children.length>4)list.lastChild.remove();
    }
  }).observe(status,{childList:true,subtree:true});
  window.addEventListener('hashchange',()=>navigate(location.hash.slice(1)));
  function syncMapPreview(){
    const source=document.getElementById('mapCanvas');
    const container=views.dashboard.querySelector('.dashboard-map');
    let preview=container.querySelector('canvas');
    if(!preview){
      preview=document.createElement('canvas');preview.setAttribute('aria-label','Prévia do mapa local carregado');container.prepend(preview);
    }
    const loaded=!source.hidden && source.width>0 && source.height>0;
    preview.hidden=!loaded;container.classList.toggle('has-map',loaded);
    container.querySelector('small').textContent=loaded?'Mapa local · sem posição do robô. Clique para abrir.':'Carregue um mapa em Mapas e destinos';
    if(loaded){
      const scale=Math.min(1,900/source.width,400/source.height);
      preview.width=Math.max(1,Math.round(source.width*scale));preview.height=Math.max(1,Math.round(source.height*scale));
      const context=preview.getContext('2d');context.imageSmoothingEnabled=false;context.drawImage(source,0,0,preview.width,preview.height);
    }
  }
  // drawMap changes canvas dimensions/visibility; defer copying until drawing finishes.
  new MutationObserver(()=>queueMicrotask(syncMapPreview)).observe(document.getElementById('mapCanvas'),{attributes:true,attributeFilter:['hidden','width','height']});
  syncMapPreview();

  navigate(location.hash.slice(1)||'dashboard',false);
})();
