let CATALOG = null;
let lines = [];

const el = (id) => document.getElementById(id);

async function loadCatalog() {
  const res = await fetch("/api/catalog");
  CATALOG = await res.json();

  const regionSelect = el("region");
  CATALOG.regions.forEach((r) => {
    const opt = document.createElement("option");
    opt.value = r.id;
    opt.textContent = r.label;
    regionSelect.appendChild(opt);
  });

  const currencySelect = el("currency");
  CATALOG.currencies.forEach((c) => {
    const opt = document.createElement("option");
    opt.value = c;
    opt.textContent = c;
    currencySelect.appendChild(opt);
  });

  const serviceSelect = el("service");
  Object.entries(CATALOG.services).forEach(([key, def]) => {
    const opt = document.createElement("option");
    opt.value = key;
    opt.textContent = def.label;
    serviceSelect.appendChild(opt);
  });

  renderDynamicFields();
}

function fieldLabel(text, inputHtml) {
  const wrapper = document.createElement("label");
  wrapper.innerHTML = `${text}${inputHtml}`;
  return wrapper;
}

function optionsHtml(items, valueKey = "id", labelKey = "label") {
  return items.map((i) => `<option value="${i[valueKey]}">${i[labelKey]}</option>`).join("");
}

function renderDynamicFields() {
  const service = el("service").value;
  const container = el("dynamic-fields");
  container.innerHTML = "";
  const def = CATALOG.services[service];

  if (service === "vm") {
    container.appendChild(fieldLabel("Taille", `<select id="p-sku">${optionsHtml(def.skus)}</select>`));
    container.appendChild(fieldLabel("OS", `<select id="p-os">${optionsHtml(def.os_options)}</select>`));
    container.appendChild(fieldLabel("Heures / mois", `<input type="number" id="p-hours" value="730" min="1">`));
  } else if (service === "storage") {
    container.appendChild(fieldLabel("Tier", `<select id="p-tier">${optionsHtml(def.tiers)}</select>`));
    container.appendChild(fieldLabel("Redondance", `<select id="p-redundancy">${optionsHtml(def.redundancies)}</select>`));
    container.appendChild(fieldLabel("Volume (Go)", `<input type="number" id="p-volume" value="100" min="0">`));
  } else if (service === "sql") {
    container.appendChild(fieldLabel("Tier", `<select id="p-tier-id">${optionsHtml(def.tiers)}</select>`));
    container.appendChild(fieldLabel("Heures / mois", `<input type="number" id="p-hours" value="730" min="1">`));
  } else if (service === "cosmos") {
    const modeSelect = fieldLabel("Mode", `<select id="p-mode">${optionsHtml(def.modes)}</select>`);
    container.appendChild(modeSelect);
    container.appendChild(fieldLabel("RU/s (provisionné)", `<input type="number" id="p-ru" value="400" min="0" step="100">`));
    container.appendChild(fieldLabel("Millions de RU (serverless)", `<input type="number" id="p-rum" value="1" min="0" step="0.1">`));
    container.appendChild(fieldLabel("Stockage (Go)", `<input type="number" id="p-storage" value="10" min="0">`));
  } else if (service === "ai_search") {
    container.appendChild(fieldLabel("Tier", `<select id="p-tier-id">${optionsHtml(def.tiers)}</select>`));
  } else if (service === "openai") {
    container.appendChild(fieldLabel("Modèle", `<select id="p-model">${optionsHtml(def.models)}</select>`));
    container.appendChild(fieldLabel("Millions tokens entrée / mois", `<input type="number" id="p-input-tok" value="1" min="0" step="0.1">`));
    container.appendChild(fieldLabel("Millions tokens sortie / mois", `<input type="number" id="p-output-tok" value="0.5" min="0" step="0.1">`));
  } else if (service === "cognitive_services") {
    container.appendChild(fieldLabel("API", `<select id="p-api">${optionsHtml(def.apis)}</select>`));
    container.appendChild(fieldLabel("Milliers de transactions / mois", `<input type="number" id="p-transactions" value="10" min="0">`));
  }
}

function buildParamsForCurrentService() {
  const service = el("service").value;
  if (service === "vm") {
    return { sku: el("p-sku").value, os: el("p-os").value, hours_per_month: Number(el("p-hours").value) };
  } else if (service === "storage") {
    return { tier: el("p-tier").value, redundancy: el("p-redundancy").value, volume_gb: Number(el("p-volume").value) };
  } else if (service === "sql") {
    return { tier_id: el("p-tier-id").value, hours_per_month: Number(el("p-hours").value) };
  } else if (service === "cosmos") {
    return {
      mode: el("p-mode").value,
      ru_per_sec: Number(el("p-ru").value),
      request_units_millions: Number(el("p-rum").value),
      storage_gb: Number(el("p-storage").value),
    };
  } else if (service === "ai_search") {
    return { tier_id: el("p-tier-id").value };
  } else if (service === "openai") {
    return {
      model: el("p-model").value,
      input_tokens_millions: Number(el("p-input-tok").value),
      output_tokens_millions: Number(el("p-output-tok").value),
    };
  } else if (service === "cognitive_services") {
    return { api: el("p-api").value, transactions_thousands: Number(el("p-transactions").value) };
  }
  return {};
}

function addLine() {
  const service = el("service").value;
  const region = el("region").value;
  const quantity = Number(el("quantity").value) || 1;
  const params = buildParamsForCurrentService();

  lines.push({
    id: crypto.randomUUID(),
    service,
    region,
    quantity,
    params,
  });

  renderLinesTable();
  recalculate();
}

function removeLine(id) {
  lines = lines.filter((l) => l.id !== id);
  renderLinesTable();
  recalculate();
}

function renderLinesTable() {
  const body = el("lines-body");
  body.innerHTML = "";
  el("empty-state").style.display = lines.length ? "none" : "block";

  lines.forEach((line) => {
    const row = document.createElement("tr");
    row.dataset.id = line.id;
    row.innerHTML = `
      <td class="label-cell">${CATALOG.services[line.service].label}</td>
      <td>${line.quantity}</td>
      <td class="unit-cell">…</td>
      <td class="monthly-cell">…</td>
      <td class="annual-cell">…</td>
      <td><button class="remove-btn" type="button">✕</button></td>
    `;
    row.querySelector(".remove-btn").addEventListener("click", () => removeLine(line.id));
    body.appendChild(row);
  });
}

function formatCurrency(value, currency) {
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency }).format(value);
}

async function recalculate() {
  const currency = el("currency").value;
  if (!lines.length) {
    el("total-monthly").textContent = "–";
    el("total-annual").textContent = "–";
    return;
  }

  const res = await fetch("/api/estimate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lines, currency }),
  });

  if (!res.ok) {
    console.error("Erreur lors du calcul de l'estimation", await res.text());
    return;
  }

  const data = await res.json();

  data.lines.forEach((result) => {
    const row = document.querySelector(`tr[data-id="${result.id}"]`);
    if (!row) return;
    row.querySelector(".label-cell").innerHTML =
      result.label + (result.warning ? `<span class="line-warning">${result.warning}</span>` : "");
    row.querySelector(".unit-cell").textContent = result.unit
      ? `${formatCurrency(result.unit_price, result.currency)} / ${result.unit}`
      : "–";
    row.querySelector(".monthly-cell").textContent = formatCurrency(result.monthly_cost, result.currency);
    row.querySelector(".annual-cell").textContent = formatCurrency(result.annual_cost, result.currency);
  });

  el("total-monthly").textContent = formatCurrency(data.total_monthly, data.currency);
  el("total-annual").textContent = formatCurrency(data.total_annual, data.currency);
}

async function exportEstimate(format) {
  const currency = el("currency").value;
  const res = await fetch(`/api/export?format=${format}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lines, currency }),
  });
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = format === "csv" ? "estimation_azure.csv" : "estimation_azure.json";
  a.click();
  URL.revokeObjectURL(url);
}

el("service").addEventListener("change", renderDynamicFields);
el("add-line").addEventListener("click", addLine);
el("currency").addEventListener("change", recalculate);
el("region").addEventListener("change", () => {});
el("export-json").addEventListener("click", () => exportEstimate("json"));
el("export-csv").addEventListener("click", () => exportEstimate("csv"));

loadCatalog();
