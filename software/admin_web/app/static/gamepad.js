
"use strict";

const onigiriGamepad = {
  active: false,
  index: null,
  frame: null,

  getController() {
    const controllers = navigator.getGamepads?.() || [];
    return this.index === null
      ? Array.from(controllers).find(Boolean)
      : controllers[this.index];
  },

  start() {
    if (this.active) return;

    if (!navigator.getGamepads) {
      console.warn("Gamepad API indisponível.");
      return;
    }

    this.active = true;
    this.update();
  },

  update() {
    if (!this.active) return;

    const controller = this.getController();

    if (controller) {
      this.index = controller.index;

      const data = {
        name: controller.id,
        axes: controller.axes.map(value =>
          Number(value.toFixed(2))
        ),
        buttons: controller.buttons.map(button => ({
          pressed: button.pressed,
          value: Number(button.value.toFixed(2))
        }))
      };

      window.dispatchEvent(
        new CustomEvent("onigiri:gamepad", { detail: data })
      );
    } else {
      this.index = null;
    }

    this.frame = requestAnimationFrame(() => this.update());
  },

  stop() {
    this.active = false;
    cancelAnimationFrame(this.frame);
    this.frame = null;
    this.index = null;
  }
};

window.onigiriGamepad = onigiriGamepad;



// Local configuration only. Never sends input to the robot.
(() => {
  const $ = id => document.getElementById(id);
  const actions = ['Avançar', 'Recuar', 'Esquerda', 'Direita', 'Parar'];
  const key = 'onigiri.gamepad.profiles.v1';
  const fresh = () => ({name:'Padrão', deadzone:0.12, centers:[], mappings:{}});
  const copy = p => JSON.parse(JSON.stringify(p));
  let state = {selected:'default', profiles:{default:fresh()}};
  let profile, latest = null, capture = null, calibration = null;
  const notice = message => { $('gamepadNotice').textContent = message; };
  try {
    const s = JSON.parse(localStorage.getItem(key));
    if (s && s.profiles && Object.hasOwn(s.profiles,s.selected) && Object.values(s.profiles).every(p =>
      typeof p.name === 'string' && Number.isFinite(p.deadzone) && p.deadzone >= 0 && p.deadzone <= .5 &&
      Array.isArray(p.centers) && p.centers.every(v => Number.isFinite(v) && Math.abs(v)<=1) &&
      p.mappings && typeof p.mappings === 'object' && Object.values(p.mappings).every(m => m &&
        ['axis','button'].includes(m.type) && Number.isInteger(m.index) && m.index>=0 && [-1,1].includes(m.sign)))) state=s;
  } catch { notice('Dados locais indisponíveis ou inválidos; usando padrão.'); }
  profile=copy(state.profiles[state.selected]);
  function persist() {
    try { localStorage.setItem(key,JSON.stringify(state)); return true; }
    catch { notice('Não foi possível salvar neste navegador.'); return false; }
  }
  function normalize(raw, center, dz) {
    const v=Math.max(-1,Math.min(1,(raw-center)/Math.max(.01,raw>=center?1-center:1+center)));
    return Math.abs(v)<=dz?0:Math.sign(v)*(Math.abs(v)-dz)/(1-dz);
  }
  function mappings() {
    $('gamepadMappings').replaceChildren(...actions.map(action => {
      const row=document.createElement('div'); row.className='gp-mapping';
      const text=document.createElement('span'), m=profile.mappings[action];
      text.textContent=`${action}: ${m ? `${m.type==='axis'?'Eixo':'Botão'} ${m.index}${m.type==='axis'?(m.sign>0?' +':' −'):''}`:'Não mapeado'}`;
      const value=document.createElement('output'); value.dataset.action=action; value.textContent='0.00';
      const button=document.createElement('button'); button.type='button'; button.textContent=`Capturar ${action}`;
      button.onclick=()=>{
        if (!onigiriGamepad.active || !latest) return notice('Inicie o teste com um controle conectado.');
        calibration=null; capture={action,armed:false,until:performance.now()+10000};
        notice(`Capturando ${action}: solte os controles, depois acione a entrada (10 segundos).`);
      };
      const clear=document.createElement('button'); clear.type='button'; clear.textContent='Limpar';
      clear.onclick=()=>{delete profile.mappings[action]; mappings();};
      row.append(text,value,button,clear); return row;
    }));
  }
  function ui() {
    capture=calibration=null;
    $('gamepadProfile').replaceChildren(...Object.entries(state.profiles).map(([id,p])=>new Option(p.name,id)));
    $('gamepadProfile').value=state.selected;
    $('gamepadProfileName').value=profile.name;
    $('gamepadDeadzone').value=profile.deadzone;
    $('gamepadDeadzoneValue').textContent=profile.deadzone.toFixed(2); mappings();
  }
  function reset(message) {
    latest=null; capture=calibration=null;
    $('gamepadStatus').textContent=message;
    $('gamepadAxes').textContent='Sem leitura.'; $('gamepadButtons').textContent='Sem leitura.';
    document.querySelectorAll('#gamepadMappings output').forEach(el=>{el.textContent='0.00';});
  }
  // Retain the original public monitor object and onigiri:gamepad event.
  onigiriGamepad.start=function() {
    if(this.active)return;
    if(!navigator.getGamepads || !window.isSecureContext)return reset('Gamepad API indisponível. Abra pelo localhost ou HTTPS.');
    this.active=true; this.update();
  };
  onigiriGamepad.update=function() {
    if(!this.active)return;
    try {
      const pads=Array.from(navigator.getGamepads()).filter(Boolean), select=$('gamepadDevice');
      const signature=JSON.stringify(pads.map(p=>[p.index,p.id]));
      if(select.dataset.signature!==signature){
        select.replaceChildren(...pads.map(p=>new Option(`${p.index}: ${p.id}`,String(p.index))));
        select.dataset.signature=signature;
      }
      const controller=this.getController();
      if(controller){
        this.index=controller.index; select.value=String(this.index);
        window.dispatchEvent(new CustomEvent('onigiri:gamepad',{detail:{name:controller.id,axes:Array.from(controller.axes),buttons:controller.buttons.map(b=>({pressed:b.pressed,value:b.value}))}}));
      }else{this.index=null;reset('Aguardando controle. Pressione um botão para detectar.');}
    }catch{this.stop();reset('Não foi possível ler o controle. Verifique as permissões do navegador.');}
    if(this.active)this.frame=requestAnimationFrame(()=>this.update());
  };
  const originalStop=onigiriGamepad.stop.bind(onigiriGamepad);
  onigiriGamepad.stop=function(){originalStop();reset('Teste interrompido.');};
  $('gamepadStart').onclick=()=>onigiriGamepad.start();
  $('gamepadStop').onclick=()=>onigiriGamepad.stop();
  $('gamepadDevice').onchange=e=>{onigiriGamepad.index=Number(e.target.value);reset('Controle selecionado.');};
  $('gamepadProfile').onchange=e=>{state.selected=e.target.value;profile=copy(state.profiles[state.selected]);persist();ui();};
  $('gamepadSave').onclick=()=>{
    profile.name=$('gamepadProfileName').value.trim().slice(0,60);
    if(!profile.name)return notice('Informe um nome.');
    state.profiles[state.selected]=copy(profile); if(persist())notice('Perfil salvo neste navegador.');ui();
  };
  $('gamepadNew').onclick=()=>{
    state.selected=crypto.randomUUID();profile=fresh();profile.name='Novo perfil';
    state.profiles[state.selected]=copy(profile);persist();ui();
  };
  $('gamepadDelete').onclick=()=>{
    if(Object.keys(state.profiles).length===1)return notice('Mantenha pelo menos um perfil.');
    delete state.profiles[state.selected];state.selected=Object.keys(state.profiles)[0];
    profile=copy(state.profiles[state.selected]);persist();ui();
  };
  $('gamepadDeadzone').oninput=e=>{profile.deadzone=Number(e.target.value);$('gamepadDeadzoneValue').textContent=profile.deadzone.toFixed(2);};
  $('gamepadCalibrate').onclick=()=>{
    if(!latest || !onigiriGamepad.active)return notice('Inicie o teste com um controle conectado.');
    capture=null;calibration={samples:[],until:performance.now()+1500};notice('Mantenha os analógicos soltos por 1,5 segundo.');
  };
  $('gamepadReset').onclick=()=>{calibration=null;profile.centers=[];notice('Calibração removida. Salve o perfil.');};
  window.addEventListener('keydown',e=>{if(e.key==='Escape'){capture=calibration=null;notice('Captura/calibração cancelada.');}});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)onigiriGamepad.stop();});
  window.addEventListener('pagehide',()=>onigiriGamepad.stop());
  window.addEventListener('onigiri:gamepad',event=>{
    const data=latest=event.detail;
    $('gamepadStatus').textContent=`Controle detectado: ${data.name}`;
    if(calibration){
      calibration.samples.push(data.axes.slice());
      if(performance.now()>=calibration.until){
        const samples=calibration.samples;
        if(samples.every(s=>s.length===data.axes.length) && data.axes.every((_,i)=>Math.max(...samples.map(s=>s[i]))-Math.min(...samples.map(s=>s[i]))<.08)){
          profile.centers=data.axes.map((_,i)=>samples.reduce((sum,s)=>sum+s[i],0)/samples.length);
          notice('Centro calibrado. Salve o perfil.');
        }else notice('Controle se moveu durante a calibração. Tente novamente.');
        calibration=null;
      }
    }
    const values=data.axes.map((v,i)=>normalize(v,profile.centers[i]||0,profile.deadzone));
    $('gamepadAxes').replaceChildren(...values.map((v,i)=>{
      const row=document.createElement('label');row.className='gp-axis';
      const meter=document.createElement('meter');meter.min=-1;meter.max=1;meter.value=v;
      row.append(`Eixo ${i}: bruto ${data.axes[i].toFixed(2)} → ${v.toFixed(2)} `,meter);return row;
    }));
    $('gamepadButtons').replaceChildren(...data.buttons.map((b,i)=>{
      const badge=document.createElement('span');badge.className=`gp-button ${b.pressed?'pressed':''}`;
      badge.textContent=`B${i}: ${b.value.toFixed(2)}`;return badge;
    }));
    if(capture){
      if(performance.now()>capture.until){capture=null;notice('Tempo de captura esgotado.');}
      else if(!capture.armed)capture.armed=values.every(v=>Math.abs(v)<.25)&&data.buttons.every(b=>b.value<.25);
      else{
        const b=data.buttons.findIndex(b=>b.value>.6),a=values.findIndex(v=>Math.abs(v)>.6);
        if(b>=0 || a>=0){
          const binding=b>=0?{type:'button',index:b,sign:1}:{type:'axis',index:a,sign:Math.sign(values[a])};
          const conflict=actions.find(action=>action!==capture.action && JSON.stringify(profile.mappings[action])===JSON.stringify(binding));
          if(conflict)notice(`Entrada já usada por ${conflict}. Limpe esse mapeamento primeiro.`);
          else{profile.mappings[capture.action]=binding;notice('Mapeamento capturado. Salve o perfil.');mappings();}
          capture=null;
        }
      }
    }
    document.querySelectorAll('#gamepadMappings output').forEach(el=>{
      const m=profile.mappings[el.dataset.action];
      el.textContent=(m?m.type==='axis'?Math.max(0,(values[m.index]||0)*m.sign):data.buttons[m.index]?.value||0:0).toFixed(2);
    });
  });
  ui();
})();
