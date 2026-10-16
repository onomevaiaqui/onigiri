const state = { destinations: [], lastText: "" };

const element = (id) => document.getElementById(id);
const dialog = element("destinationDialog");

function lines(value) {
  return value.split("\n").map((item) => item.trim()).filter(Boolean);
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

element("exportButton").addEventListener("click", async () => {
  const result = await api("/api/export", { method: "POST" });
  alert(`Configuração atualizada em:\n${result.path}`);
});

loadDestinations().catch((error) => { element("destinationList").textContent = error.message; });
