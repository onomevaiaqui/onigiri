/* Visual markers for saved destinations; no robot localization is inferred. */
(() => {
  const area=document.querySelector('.map-workspace'),canvas=document.getElementById('mapCanvas');
  const overlay=document.createElement('div');overlay.className='map-marker-layer';area.append(overlay);
  const icons={
    point:'<path d="M20 10c0 6-8 11-8 11S4 16 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',
    destination:'<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2"/><path d="M12 2v3m0 14v3M2 12h3m14 0h3"/>',
    home:'<path d="m3 10 9-7 9 7M5 9v12h14V9M9 21v-7h6v7"/>'
  };
  function svg(type){return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[type]}</svg>`;}
  const legend=document.createElement('div');legend.className='map-marker-legend';
  [['point','Ponto selecionado'],['destination','Destino'],['home','Base']].forEach(([type,label])=>{
    const item=document.createElement('span');item.className='marker-'+type;item.innerHTML=svg(type);item.append(label);legend.append(item);
  });
  area.after(legend);
  let data=null;
  function worldFraction(map,x,y){
    const dx=x-map.origin.x,dy=y-map.origin.y,c=Math.cos(map.origin.yaw),s=Math.sin(map.origin.yaw);
    return {x:(c*dx+s*dy)/(map.width*map.resolution),y:1-(-s*dx+c*dy)/(map.height*map.resolution)};
  }
  function render(){
    overlay.replaceChildren();if(!data||canvas.hidden)return;
    const bounds=canvas.getBoundingClientRect(),parent=area.getBoundingClientRect();
    if(!bounds.width||!bounds.height)return;
    function marker(type,x,y,label,invalid=false,destination=null){
      if(!Number.isFinite(x)||!Number.isFinite(y)||x<0||x>1||y<0||y>1)return;
      const item=document.createElement(destination?'button':'span');item.className=`map-marker marker-${type}${invalid?' invalid':''}`;
      item.innerHTML=svg(type);item.title=label;item.setAttribute('aria-label',label);
      if(destination){item.type='button';item.onclick=event=>{event.stopPropagation();openEditor(destination);};}
      else item.setAttribute('role','img');
      item.style.left=(bounds.left-parent.left-area.clientLeft+x*bounds.width)+'px';
      item.style.top=(bounds.top-parent.top-area.clientTop+y*bounds.height)+'px';overlay.append(item);
    }
    data.destinations.forEach(destination=>{
      const p=worldFraction(data.map,destination.x,destination.y);
      marker(destination.is_home?'home':'destination',p.x,p.y,`${destination.is_home?'Base':'Destino'}: ${destination.name}`,false,destination);
    });
    if(data.point){const p=data.point;marker('point',(p.pixelX+.5)/data.map.width,(p.pixelY+.5)/data.map.height,p.valid?'Ponto selecionado':'Ponto fora da área livre',!p.valid);}
  }
  window.addEventListener('onigiri:map-rendered',event=>{data=event.detail;render();});
  new ResizeObserver(render).observe(canvas);
  new MutationObserver(render).observe(canvas,{attributes:true,attributeFilter:['hidden','style']});
  const list=document.getElementById('destinationList');
  function decorateList(){
    list.querySelectorAll('.destination-card h4').forEach(title=>{
      if(title.querySelector('svg'))return;
      const card=title.closest('.destination-card'),type=card.querySelector('.base-badge').hidden?'destination':'home';
      const icon=document.createElement('span');icon.className='destination-symbol marker-'+type;icon.innerHTML=svg(type);title.prepend(icon);
    });
  }
  new MutationObserver(decorateList).observe(list,{childList:true});decorateList();
  if(typeof state!=='undefined'&&state.map)drawMap();
})();
