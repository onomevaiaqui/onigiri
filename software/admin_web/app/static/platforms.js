/* Onigiri hardware profile. Saving is deliberately configuration-only. */
(() => {
  const host = document.getElementById('view-settings');
  const card = document.createElement('section');
  card.className = 'panel platform-panel';
  card.innerHTML = `<h3>Hardware do Onigiri</h3>
    <p>Escolha os componentes instalados neste robô. Salvar só grava o perfil: não inicia serviços nem movimenta motores.</p>
    <form id="platformForm">
      <div class="profile-basic">
        <label>Nome do robô<input name="robot_name" maxlength="80" placeholder="Ex.: Onigiri recepção"><small>Usado somente para organização.</small></label>
        <label>Raspberry Pi<select name="computer"><option value="raspberry4">Raspberry Pi 4</option><option value="raspberry5">Raspberry Pi 5</option></select></label>
        <label>Frame<select name="chassis"></select><small id="chassisDescription"></small></label>
        <label>Driver dos motores<select name="motor_driver"></select><small id="driverStatus"></small></label>
        <label>Conexão do driver<input id="motorConnection" readonly></label>
        <label>Porta do driver (quando USB/serial)<input name="serial_port" maxlength="240" placeholder="/dev/serial/by-id/…"></label>
      </div>
      <details class="profile-advanced"><summary>LiDAR, webcam e áudio</summary>
        <label>LiDAR 2D rotativo<select name="lidar_model"></select><small id="lidarStatus"></small></label>
        <label>Porta do LiDAR<input name="lidar_port" maxlength="240" placeholder="/dev/serial/by-id/…"></label>
        <label>Webcam e microfone<select name="camera"></select></label>
        <label>Dispositivo da webcam<input name="camera_device" maxlength="240" placeholder="/dev/video0"></label>
        <label>Dispositivo do microfone<input name="microphone_device" maxlength="120" placeholder="default"></label>
        <label>Dispositivo do alto-falante<input name="speaker_device" maxlength="120" placeholder="default"></label>
      </details>
      <p id="platformNotice">Perfis de driver marcados como “integração pendente” não são acionados pelo Onigiri até receberem o adaptador e a validação elétrica.</p>
      <button type="submit">Salvar configuração</button><p id="platformStatus" role="status" aria-live="polite"></p>
    </form>`;
  host.querySelector('h2').after(card);

  const form = card.querySelector('form');
  const status = card.querySelector('#platformStatus');
  const option = (item) => Object.assign(document.createElement('option'), {value:item.id, textContent:item.name});
  let data;

  function fill(select, items) {
    select.replaceChildren(...items.map(option));
  }
  function renderDetails() {
    const driver = data.drivers.find(item => item.id === form.elements.motor_driver.value);
    const chassis = data.catalog.find(item => item.id === form.elements.chassis.value);
    const lidar = data.lidars.find(item => item.id === form.elements.lidar_model.value);
    form.querySelector('#motorConnection').value = driver ? ({
      i2c:'I²C', usb:'USB direto', usb_ttl:'USB/TTL serial', gpio_pwm_dir:'GPIO PWM/DIR'
    }[driver.connection] || driver.connection) : '';
    form.elements.motor_connection.value = driver?.connection || '';
    form.querySelector('#driverStatus').textContent = driver?.operational
      ? 'Adaptador validado no software atual.' : 'Integração elétrica e de software pendente.';
    form.querySelector('#chassisDescription').textContent = chassis?.description || '';
    form.querySelector('#lidarStatus').textContent = lidar?.operational
      ? `Driver: ${lidar.driver}.` : `Requer instalação do driver ${lidar?.driver || ''}.`;
  }
  async function load() {
    const response = await fetch('/api/platform');
    if (!response.ok) throw Error('Configuração indisponível');
    data = await response.json();
    fill(form.elements.chassis, data.catalog);
    fill(form.elements.motor_driver, data.drivers);
    fill(form.elements.lidar_model, data.lidars);
    fill(form.elements.camera, data.cameras);
    const config = data.config;
    for (const [name, value] of Object.entries(config)) if (form.elements[name]) form.elements[name].value = value;
    form.insertAdjacentHTML('beforeend', '<input name="motor_connection" type="hidden">');
    renderDetails();
  }
  ['motor_driver','chassis','lidar_model'].forEach(name => form.elements[name].addEventListener('change', renderDetails));
  form.onsubmit = async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(form));
    try {
      const response = await fetch('/api/platform', {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
      const body = await response.json();
      if (!response.ok) throw Error(body.detail || 'Não foi possível salvar');
      status.textContent = 'Configuração salva. O perfil não envia comandos aos motores.';
    } catch (error) {
      status.textContent = error.message;
    }
  };
  load().catch(error => status.textContent = error.message);
})();
