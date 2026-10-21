const { chromium } = require('playwright');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const page = await browser.newPage({ baseURL: 'http://localhost:18088', viewport: { width: 1280, height: 900 } });
    await page.goto('http://localhost:18088/#settings');
    await page.getByRole('heading', { name: 'Configuração do Onigiri', exact: true }).waitFor();
    const form = page.locator('#platformForm');
    await form.locator('[name=robot_name]').fill('Onigiri da recepção');
    await form.locator('button').click();
    await page.getByText('Configuração salva. Nenhum serviço de motores foi alterado.').waitFor();
    await page.reload();
    await page.waitForFunction(() => document.querySelector('[name=robot_name]').value === 'Onigiri da recepção');
    await page.locator('[data-view=maps]').click();
    await page.getByRole('heading', { name: 'Mapa e posicionamento de destinos' }).waitFor();
    await page.locator('[data-view=controls]').click();
    await page.locator('#gamepadPanel').waitFor();
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    console.log('PASS: identidade, mapas e controle local do Onigiri');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });

