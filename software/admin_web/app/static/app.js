const state = { destinations: [], lastText: "" };

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
  element("returnToBase").checked = true;
  ["x", "y", "yaw"].forEach((id) => { element(id).value = "0"; });
  element("waitSeconds").value = "15";
}

function openEditor(destination = null) {
  resetForm();
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
  }
  dialog.showModal();
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

async function removeDestination(destination) {
  if (!confirm(`Excluir o destino “${destination.name}”?`)) return;
  try {
    await api(`/api/destinations/${destination.id}`, { method: "DELETE" });
    await loadDestinations();
  } catch (error) {
    alert(error.message);
  }
}

function renderInterpretation(result) {
  const box = element("testResult");
  const simulate = element("simulateButton");
  box.className = `result ${result.recognized ? "success" : "failure"}`;
  if (result.recognized) {
    box.innerHTML = `<strong>${result.message}</strong><br>Trecho correspondente: “${result.matched_phrase}”`;
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
    item.innerHTML = `<strong>${event.state}</strong><span>${event.detail}</span>`;
    timeline.appendChild(item);
  });
}

element("newDestination").addEventListener("click", () => openEditor());
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
  };
  const id = element("destinationId").value;
  try {
    await api(id ? `/api/destinations/${id}` : "/api/destinations", {
      method: id ? "PUT" : "POST", body: JSON.stringify(payload),
    });
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
