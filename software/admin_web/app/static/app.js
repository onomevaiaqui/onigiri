const state = { destinations: [], lastText: "", map: null, selectedMapPoint: null };

const element = (id) => document.getElementById(id);
const dialog = element("destinationDialog");

function lines(value) {
  return value.split("\n").map((item) => item.trim()).filter(Boolean);
}

function normalizedKey(value) {
  return value.toLocaleLowerCase("pt-BR").normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim();
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Não foi possível concluir a operação.");
  }
  return response.status === 204 ? null : response.json();
}

function resetForm() {
  element("destinationForm").reset();
  element("destinationId").value = "";
  element("dialogTitle").textContent = "Novo destino";
  element("formError").textContent = "";
  ["name", "aliases", "phrases", "arrivalMessage"].forEach((id) => { element(id).value = ""; });
  element("returnToBase").checked = true;
  ["x", "y", "yaw"].forEach((id) => { element(id).value = "0"; });
  element("waitSeconds").value = "15";
}

function openEditor(destination = null, mapPoint = null, kind = "destination") {
  resetForm();
  element("pointType").value = destination?.is_home ? "base" : kind;
  element("destinationMap").value = destination?.map_name || state.map?.savedName || "";
  element("deletePoint").hidden = !destination;
  if (destination) {
    element("dialogTitle").textContent = `Editar: ${destination.name}`;
    element("destinationId").value = destination.id;
    element("name").value = destination.name;
    element("aliases").value = destination.aliases.join("\n");
    element("phrases").value = destination.phrases.join("\n");
    element("arrivalMessage").value = destination.arrival_message;
    ["x", "y", "yaw"].forEach((key) => { element(key).value = destination[key]; });
    element("waitSeconds").value = destination.wait_seconds;
    element("returnToBase").checked = destination.return_to_base;
  } else if (mapPoint) {
    element("x").value = mapPoint.x.toFixed(3);
    element("y").value = mapPoint.y.toFixed(3);
  }
  dialog.showModal();
}

function parseMapMetadata(contents) {
  const resolution = Number((contents.match(/^\s*resolution\s*:\s*([^#\s]+)/m) || [])[1]);
  const originMatch = contents.match(/^\s*origin\s*:\s*\[\s*([^,]+),\s*([^,]+),\s*([^\]]+)\s*\]/m);
  if (!Number.isFinite(resolution) || resolution <= 0 || !originMatch) {
    throw new Error("O YAML não contém resolução e origem compatíveis com um mapa ROS 2.");
  }
  const origin = originMatch.slice(1).map(Number);
  if (origin.some((value) => !Number.isFinite(value))) {
    throw new Error("A origem do mapa no YAML não é válida.");
  }
  return { resolution, origin: { x: origin[0], y: origin[1], yaw: origin[2] } };
}

function isWhitespace(value) { return value === 9 || value === 10 || value === 13 || value === 32; }

function pgmToken(bytes, start) {
  let index = start;
  while (index < bytes.length) {
    if (bytes[index] === 35) { while (index < bytes.length && bytes[index] !== 10) index += 1; }
    else if (isWhitespace(bytes[index])) index += 1;
    else break;
  }
  const tokenStart = index;
  while (index < bytes.length && !isWhitespace(bytes[index]) && bytes[index] !== 35) index += 1;
  return { value: new TextDecoder().decode(bytes.slice(tokenStart, index)), next: index };
}

function parsePgm(buffer) {
  const bytes = new Uint8Array(buffer);
  const magic = pgmToken(bytes, 0);
  if (magic.value !== "P2" && magic.value !== "P5") throw new Error("A imagem precisa estar no formato PGM P2 ou P5.");
  const widthToken = pgmToken(bytes, magic.next);
  const width = Number(widthToken.value);
  const heightToken = pgmToken(bytes, widthToken.next);
  const height = Number(heightToken.value);
  const maxToken = pgmToken(bytes, heightToken.next);
  const max = Number(maxToken.value);
  if (!Number.isInteger(width) || !Number.isInteger(height) || width < 1 || height < 1 || max < 1 || max > 255) {
    throw new Error("Dimensões ou escala PGM não suportadas.");
  }
  const expected = width * height;
  const pixels = new Uint8ClampedArray(expected);
  if (magic.value === "P2") {
    let cursor = maxToken.next;
    for (let index = 0; index < expected; index += 1) {
      const token = pgmToken(bytes, cursor);
      const value = Number(token.value);
      if (!Number.isFinite(value)) throw new Error("Imagem PGM incompleta.");
      pixels[index] = Math.round((value / max) * 255);
      cursor = token.next;
    }
  } else {
    let cursor = maxToken.next;
    if (bytes[cursor] === 13 && bytes[cursor + 1] === 10) cursor += 2;
    else if (isWhitespace(bytes[cursor])) cursor += 1;
    if (bytes.length - cursor < expected) throw new Error("Imagem PGM incompleta.");
    for (let index = 0; index < expected; index += 1) pixels[index] = Math.round((bytes[cursor + index] / max) * 255);
  }
  return { width, height, pixels };
}

function drawMap() {
  const canvas = element("mapCanvas");
  const empty = element("mapEmpty");
  const context = canvas.getContext("2d");
  canvas.width = state.map.width;
  canvas.height = state.map.height;
  const image = context.createImageData(state.map.width, state.map.height);
  state.map.pixels.forEach((value, index) => {
    const offset = index * 4;
    image.data[offset] = value; image.data[offset + 1] = value; image.data[offset + 2] = value; image.data[offset + 3] = 255;
  });
  context.putImageData(image, 0, 0);
  canvas.hidden = false;
  empty.hidden = true;
  window.dispatchEvent(new CustomEvent("onigiri:map-rendered", {detail: {map: state.map, point: state.selectedMapPoint, destinations: state.destinations}}));
}

async function loadMapFiles() {
  const yaml = element("mapYamlFile").files[0];
  const pgm = element("mapPgmFile").files[0];
  if (!yaml || !pgm) {
    element("mapStatus").textContent = "Selecione os dois arquivos do mapa: .yaml e .pgm.";
    return;
  }
  try {
    const metadata = parseMapMetadata(await yaml.text());
    const image = parsePgm(await pgm.arrayBuffer());
    state.map = { ...metadata, ...image, savedName: element("mapPgmFile").dataset.savedMapName || null, label: `${yaml.name} + ${pgm.name}` };
    state.selectedMapPoint = null;
    element("mapPoint").textContent = "Nenhum ponto selecionado.";
    element("newDestinationAtPoint").disabled = true;
    element("mapStatus").textContent = `Mapa carregado: ${image.width} × ${image.height} células, resolução de ${metadata.resolution} m/célula.`;
    drawMap();
  } catch (error) {
    state.map = null;
    element("mapCanvas").hidden = true;
    element("mapEmpty").hidden = false;
    element("mapStatus").textContent = `Não foi possível carregar o mapa: ${error.message}`;
  }
}

function selectMapPoint(event) {
  if (!state.map) return;
  const canvas = element("mapCanvas");
  const bounds = canvas.getBoundingClientRect();
  const pixelX = Math.min(state.map.width - 1, Math.max(0, Math.floor((event.clientX - bounds.left) * state.map.width / bounds.width)));
  const pixelY = Math.min(state.map.height - 1, Math.max(0, Math.floor((event.clientY - bounds.top) * state.map.height / bounds.height)));
  const occupancy = state.map.pixels[pixelY * state.map.width + pixelX];
  const localX = (pixelX + 0.5) * state.map.resolution;
  const localY = (state.map.height - pixelY - 0.5) * state.map.resolution;
  const c = Math.cos(state.map.origin.yaw), s = Math.sin(state.map.origin.yaw);
  const point = {
    x: state.map.origin.x + c * localX - s * localY,
    y: state.map.origin.y + s * localX + c * localY,
    pixelX,
    pixelY,
    valid: occupancy >= 245,
  };
  state.selectedMapPoint = point;
  drawMap();
  if (!point.valid) {
    element("mapPoint").textContent = "Este ponto não é uma área livre mapeada. Selecione uma região branca.";
    element("newDestinationAtPoint").disabled = true;
    return;
  }
  element("mapPoint").textContent = `Ponto livre: X ${point.x.toFixed(3)}, Y ${point.y.toFixed(3)} m`;
  element("newDestinationAtPoint").disabled = false;
}

function renderDestinations() {
  const list = element("destinationList");
  list.replaceChildren();
  state.destinations.forEach((destination) => {
    const item = element("destinationTemplate").content.cloneNode(true);
    item.querySelector("h4").textContent = destination.name;
    item.querySelector(".base-badge").hidden = !destination.is_home;
    const labels = [...destination.aliases, ...destination.phrases];
    item.querySelector(".aliases").textContent = labels.length ? `Reconhece: ${labels.join(" · ")}` : "Sem variações cadastradas";
    item.querySelector(".coordinates").textContent = `Mapa: x ${destination.x}, y ${destination.y}, yaw ${destination.yaw}`;
    item.querySelector(".edit").addEventListener("click", () => openEditor(destination));
    item.querySelector(".home").disabled = destination.is_home;
    item.querySelector(".home").addEventListener("click", () => setHome(destination));
    item.querySelector(".delete").addEventListener("click", () => removeDestination(destination));
    list.appendChild(item);
  });
}

async function loadDestinations() {
  state.destinations = await api("/api/destinations");
  renderDestinations();
  if (state.map) drawMap();
  await loadReadiness();
}

async function loadReadiness() {
  const report = await api("/api/readiness");
  const issues = [];
  if (report.without_phrases.length) issues.push(`Sem frases ou sinônimos: ${report.without_phrases.join(", ")}.`);
  if (report.without_map_position.length) issues.push(`Ainda sem posição no mapa: ${report.without_map_position.join(", ")}.`);
  report.phrase_conflicts.forEach((conflict) => issues.push(`A expressão “${conflict.phrase}” aparece em: ${conflict.destinations.join(" e ")}.`));
  element("readinessSummary").textContent = issues.length
    ? "Há itens a revisar antes de integrar ao Raspberry Pi."
    : "Cadastro consistente para a próxima etapa de integração.";
  const list = element("readinessList");
  list.replaceChildren();
  (issues.length ? issues : [`${report.destination_count} destinos cadastrados; base: ${report.home || "não definida"}.`]).forEach((message) => {
    const item = document.createElement("li");
    item.textContent = message;
    list.appendChild(item);
  });
}

async function setHome(destination) {
  await api(`/api/destinations/${destination.id}/home`, { method: "POST" });
  await loadDestinations();
}

function clearMapSelection() {
  state.selectedMapPoint = null;
  element("mapPoint").textContent = "Nenhum ponto selecionado.";
  element("newDestinationAtPoint").disabled = true;
}

async function removeDestination(destination) {
  const box = element("deletePointDialog"), yes = element("confirmDeletePoint"), no = element("cancelDeletePoint");
  const replacement = element("replacementBase");
  element("deletePointName").textContent = `Excluir “${destination.name}”?`;
  element("deletePointError").textContent = "";
  element("replacementBaseField").hidden = !destination.is_home;
  replacement.replaceChildren(new Option("Escolha a nova base", ""), ...state.destinations.filter(d => d.id !== destination.id).map(d => new Option(d.name, String(d.id))));
  yes.disabled = false; no.disabled = false;
  box.showModal();
  return new Promise(resolve => {
    const cancel = () => { box.close(); resolve(false); };
    no.onclick = cancel;
    box.oncancel = event => { event.preventDefault(); if (!yes.disabled) cancel(); };
    yes.onclick = async () => {
      if (destination.is_home && !replacement.value) {
        element("deletePointError").textContent = "Escolha a base substituta antes de confirmar.";
        return;
      }
      yes.disabled = true; no.disabled = true;
      try {
        const suffix = destination.is_home ? `?replacement_id=${encodeURIComponent(replacement.value)}` : "";
        await api(`/api/destinations/${destination.id}${suffix}`, {method: "DELETE"});
        clearMapSelection();
        await loadDestinations();
        box.close(); resolve(true);
      } catch (error) {
        element("deletePointError").textContent = error.message;
      } finally { yes.disabled = false; no.disabled = false; }
    };
  });
}

function renderInterpretation(result) {
  const box = element("testResult");
  const simulate = element("simulateButton");
  box.className = `result ${result.recognized ? "success" : "failure"}`;
  box.replaceChildren();
  if (result.recognized) {
    const headline = document.createElement("strong");
    headline.textContent = result.message;
    box.append(headline, document.createElement("br"), document.createTextNode(`Trecho correspondente: “${result.matched_phrase}”`));
    simulate.disabled = false;
  } else {
    box.textContent = result.message;
    simulate.disabled = true;
  }
}

function renderSimulation(result) {
  const timeline = element("simulation");
  timeline.replaceChildren();
  result.events.forEach((event) => {
    const item = document.createElement("li");
    const title = document.createElement("strong");
    title.textContent = event.state;
    const detail = document.createElement("span");
    detail.textContent = event.detail;
    item.append(title, detail);
    timeline.appendChild(item);
  });
}

element("newDestination").addEventListener("click", () => openEditor());
element("mapYamlFile").addEventListener("change", event=>{if(event.isTrusted)delete element("mapPgmFile").dataset.savedMapName;loadMapFiles();});
element("mapPgmFile").addEventListener("change", event=>{if(event.isTrusted)delete element("mapPgmFile").dataset.savedMapName;loadMapFiles();});
element("mapCanvas").addEventListener("click", selectMapPoint);
element("clearMapSelection").addEventListener("click", () => { clearMapSelection(); if (state.map) drawMap(); });
element("newDestinationAtPoint").addEventListener("click", () => openEditor(null, state.selectedMapPoint, element("newPointType").value));
element("deletePoint").addEventListener("click", async () => {
  const destination = state.destinations.find(item => String(item.id) === element("destinationId").value);
  if (destination && await removeDestination(destination)) dialog.close();
});
element("closeDialog").addEventListener("click", () => dialog.close());
element("cancelDialog").addEventListener("click", () => dialog.close());
element("suggestPhrases").addEventListener("click", () => {
  const name = element("name").value.trim();
  if (!name) {
    element("formError").textContent = "Informe o nome do destino antes de gerar sugestões.";
    return;
  }
  const suggestions = [
    `me leve para ${name}`,
    `onde fica ${name}`,
    `quero ir para ${name}`,
    `como chego em ${name}`,
  ];
  const existing = lines(element("phrases").value);
  const known = new Set(existing.map(normalizedKey));
  const merged = [...existing, ...suggestions.filter((phrase) => !known.has(normalizedKey(phrase)))];
  element("phrases").value = merged.join("\n");
  element("formError").textContent = "";
});

element("destinationForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    name: element("name").value,
    aliases: lines(element("aliases").value),
    phrases: lines(element("phrases").value),
    x: Number(element("x").value), y: Number(element("y").value), yaw: Number(element("yaw").value),
    arrival_message: element("arrivalMessage").value,
    wait_seconds: Number(element("waitSeconds").value),
    return_to_base: element("returnToBase").checked,
    is_home: element("pointType").value === "base",
    map_name: element("destinationMap").value.trim() || null,
  };
  const id = element("destinationId").value;
  try {
    await api(id ? `/api/destinations/${id}` : "/api/destinations", {
      method: id ? "PUT" : "POST", body: JSON.stringify(payload),
    });
    clearMapSelection();
    dialog.close();
    await loadDestinations();
  } catch (error) {
    element("formError").textContent = error.message;
  }
});

element("testForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  state.lastText = element("testText").value.trim();
  const result = await api("/api/interpret", { method: "POST", body: JSON.stringify({ text: state.lastText }) });
  renderInterpretation(result);
  element("simulation").replaceChildren();
});

element("simulateButton").addEventListener("click", async () => {
  const result = await api("/api/simulate", { method: "POST", body: JSON.stringify({ text: state.lastText }) });
  renderSimulation(result);
});

element("batchButton").addEventListener("click", async () => {
  const texts = lines(element("batchText").value);
  const results = element("batchResults");
  results.replaceChildren();
  if (!texts.length) {
    results.textContent = "Digite ao menos uma frase para testar.";
    return;
  }
  try {
    const response = await api("/api/interpret/batch", { method: "POST", body: JSON.stringify({ texts }) });
    response.results.forEach((result) => {
      const item = document.createElement("li");
      item.className = result.recognized ? "recognized" : "not-recognized";
      item.textContent = result.recognized
        ? `✓ “${result.request}” → ${result.destination.name}`
        : `× “${result.request}” → não reconhecida`;
      results.appendChild(item);
    });
  } catch (error) {
    results.textContent = error.message;
  }
});

element("exportButton").addEventListener("click", async () => {
  const result = await api("/api/export", { method: "POST" });
  alert(`Configuração atualizada em:\n${result.path}`);
});

element("backupButton").addEventListener("click", async () => {
  const backup = await api("/api/backup");
  const file = new Blob([JSON.stringify(backup, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(file);
  link.download = "onigiri-destinos-backup.json";
  link.click();
  URL.revokeObjectURL(link.href);
});

element("restoreFile").addEventListener("change", async (event) => {
  const [file] = event.target.files;
  if (!file) return;
  try {
    const backup = JSON.parse(await file.text());
    await api("/api/backup/restore", { method: "POST", body: JSON.stringify(backup) });
    await loadDestinations();
    alert("Backup restaurado com sucesso.");
  } catch (error) {
    alert(`Não foi possível restaurar o backup: ${error.message}`);
  } finally {
    event.target.value = "";
  }
});

loadDestinations().catch((error) => { element("destinationList").textContent = error.message; });
