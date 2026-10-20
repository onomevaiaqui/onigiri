/* Offline network seed download; Wi-Fi credentials stay in this browser. */
(() => {
 const card=document.createElement('section');card.className='panel platform-panel';
 card.innerHTML=`<h3>Rede da imagem SD</h3><p>Ethernet recebe IP automaticamente. Para Wi-Fi, gere o arquivo e copie para a partição de boot do cartão antes da primeira inicialização.</p><form id="networkSeed"><label>Nome da rede Wi-Fi (SSID)<input name="ssid" required maxlength="32" autocomplete="off"></label><label>Senha da rede<input name="password" type="password" required minlength="8" maxlength="63" autocomplete="new-password"></label><button type="submit">Baixar network-config</button><p role="status"></p></form>`;
 document.getElementById('view-settings').append(card);
 card.querySelector('form').onsubmit=event=>{event.preventDefault();const fields=event.target.elements,ssid=JSON.stringify(fields.ssid.value),password=JSON.stringify(fields.password.value);
 const text=`version: 2\nethernets:\n  ethernet:\n    match:\n      name: "e*"\n    dhcp4: true\n    optional: true\nwifis:\n  wlan0:\n    dhcp4: true\n    optional: true\n    access-points:\n      ${ssid}:\n        password: ${password}\n`;
 const url=URL.createObjectURL(new Blob([text],{type:'text/yaml'}));const link=document.createElement('a');link.href=url;link.download='network-config';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);card.querySelector('[role=status]').textContent='Arquivo gerado localmente. Contém a senha do Wi-Fi; copie apenas para o cartão do seu robô.';};
})();
