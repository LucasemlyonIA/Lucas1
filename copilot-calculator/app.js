(function () {
  "use strict";
  const { compute, DEFAULTS } = window.CopilotCalc;
  const $ = (id) => document.getElementById(id);
  const STORE = "copilot-calc-v1";

  const state = JSON.parse(JSON.stringify(DEFAULTS));
  state.azureResources = [];

  try {
    const saved = JSON.parse(localStorage.getItem(STORE));
    if (saved && typeof saved === "object") {
      for (const k of ["totalUsers", "licensedUsers", "interactions", "creditPriceUsd", "usdToEur"]) {
        if (Number.isFinite(+saved[k])) state[k] = +saved[k];
      }
      if (Array.isArray(saved.types)) {
        state.types.forEach((t) => {
          const s = saved.types.find((x) => x.id === t.id);
          if (s) { t.pct = +s.pct || 0; t.credits = Number.isFinite(+s.credits) ? +s.credits : t.credits; }
        });
      }
      if (Array.isArray(saved.azureResources)) {
        state.azureResources = saved.azureResources.map((r) => ({ name: String(r.name || ""), monthlyEur: +r.monthlyEur || 0 }));
      }
    }
  } catch (e) { /* stockage indisponible : valeurs par défaut */ }

  const fmtEur = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 2 });
  const fmtInt = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });
  const fmtDec = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 });
  const eur = (v) => fmtEur.format(v);

  function persist() {
    try { localStorage.setItem(STORE, JSON.stringify(state)); } catch (e) { /* ignore */ }
  }

  // --- Construction des champs -------------------------------------------------
  function bindNumber(id, key) {
    const el = $(id);
    el.value = state[key];
    el.addEventListener("input", () => {
      state[key] = el.value === "" ? 0 : Math.max(0, parseFloat(el.value) || 0);
      render();
    });
  }
  bindNumber("totalUsers", "totalUsers");
  bindNumber("licensedUsers", "licensedUsers");
  bindNumber("interactions", "interactions");
  bindNumber("usdToEur", "usdToEur");
  bindNumber("creditPrice", "creditPriceUsd");

  const typesBody = $("typesBody");
  state.types.forEach((t) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${t.label}</td><td>${t.credits}</td><td><input type="number" min="0" max="100" step="0.1" aria-label="Part ${t.label}"></td>`;
    const input = tr.querySelector("input");
    input.value = t.pct;
    input.addEventListener("input", () => {
      t.pct = input.value === "" ? 0 : Math.max(0, parseFloat(input.value) || 0);
      render();
    });
    t._input = input;
    typesBody.appendChild(tr);
  });

  $("normalize").addEventListener("click", () => {
    const sum = state.types.reduce((s, t) => s + t.pct, 0);
    if (sum <= 0) { state.types.forEach((t, i) => (t.pct = i === 0 ? 100 : 0)); }
    else state.types.forEach((t) => (t.pct = Math.round((t.pct / sum) * 1000) / 10));
    // corrige l'arrondi sur la plus grande part pour retomber exactement sur 100
    const diff = Math.round((100 - state.types.reduce((s, t) => s + t.pct, 0)) * 10) / 10;
    const big = state.types.reduce((a, b) => (b.pct > a.pct ? b : a));
    big.pct = Math.round((big.pct + diff) * 10) / 10;
    state.types.forEach((t) => (t._input.value = t.pct));
    render();
  });

  // --- Ressources Azure ---------------------------------------------------------
  function renderAzure() {
    const list = $("azureList");
    list.innerHTML = "";
    state.azureResources.forEach((r, i) => {
      const row = document.createElement("div");
      row.className = "azure-row";
      row.innerHTML = `<input type="text" placeholder="Nom de la ressource (ex. Azure AI Search)" aria-label="Nom">
        <input type="number" min="0" step="0.01" placeholder="€ / mois" aria-label="Montant mensuel en euros">
        <button type="button" aria-label="Supprimer">Supprimer</button>`;
      const [name, amount] = row.querySelectorAll("input");
      name.value = r.name; amount.value = r.monthlyEur || "";
      name.addEventListener("input", () => { r.name = name.value; render(false); });
      amount.addEventListener("input", () => { r.monthlyEur = Math.max(0, parseFloat(amount.value) || 0); render(false); });
      row.querySelector("button").addEventListener("click", () => { state.azureResources.splice(i, 1); renderAzure(); render(); });
      list.appendChild(row);
    });
    $("azureEmpty").hidden = state.azureResources.length > 0;
  }
  $("addAzure").addEventListener("click", () => {
    state.azureResources.push({ name: "", monthlyEur: 0 });
    renderAzure();
    const inputs = $("azureList").querySelectorAll("input[type=text]");
    inputs[inputs.length - 1].focus();
    render();
  });

  $("reset").addEventListener("click", () => {
    if (!confirm("Réinitialiser toutes les valeurs ?")) return;
    try { localStorage.removeItem(STORE); } catch (e) { /* ignore */ }
    location.reload();
  });

  // --- Rendu des résultats ------------------------------------------------------
  let last;
  function render() {
    const r = (last = compute(state));
    persist();

    $("fxShow").textContent = fmtDec.format(state.usdToEur);
    const over = state.licensedUsers > state.totalUsers;
    $("licensedUsers").classList.toggle("invalid", over);
    $("licenseHint").textContent = over
      ? `Supérieur au total : limité à ${fmtInt.format(state.totalUsers)}.`
      : "Ces utilisateurs ne consomment pas de crédits.";

    const badge = $("pctBadge");
    badge.textContent = `${fmtDec.format(r.pctSum)} %`;
    badge.classList.toggle("bad", !r.pctValid);
    $("pctWarning").hidden = r.pctValid;

    $("monthly").textContent = eur(r.monthlyEur);
    $("annual").textContent = eur(r.annualEur);

    $("breakdownBody").innerHTML = r.lines.map((l) =>
      `<tr><td>${l.label} <small>(${fmtDec.format(l.pct)} % × ${l.unitCredits} cr.)</small></td><td>${fmtInt.format(l.credits)}</td><td>${eur(l.eur)}</td></tr>`).join("");
    $("breakdownFoot").innerHTML =
      `<tr><td>Crédits Copilot (pay-as-you-go)</td><td>${fmtInt.format(r.creditsMonthly)}</td><td>${eur(r.copilotEurMonthly)}</td></tr>` +
      `<tr><td>Ressources Azure additionnelles</td><td>—</td><td>${eur(r.azureEurMonthly)}</td></tr>` +
      `<tr><td>Total mensuel</td><td></td><td>${eur(r.monthlyEur)}</td></tr>`;

    $("sBillable").textContent = `${fmtInt.format(r.billableUsers)} / ${fmtInt.format(state.totalUsers)}`;
    $("sInteractions").textContent = fmtInt.format(r.interactionsBilled);
    $("sAvg").textContent = fmtDec.format(r.avgCreditsPerInteraction);
    $("sPerUser").textContent = eur(r.costPerBillableUserEur);
    $("sPerInter").textContent = fmtEur.format(r.costPerInteractionEur);
  }

  $("exportCsv").addEventListener("click", () => {
    const r = last, q = (s) => `"${String(s).replace(/"/g, '""')}"`;
    const rows = [["Poste", "Part %", "Crédits unitaires", "Interactions/mois", "Crédits/mois", "EUR/mois", "EUR/an"]];
    r.lines.forEach((l) => rows.push([q(l.label), l.pct, l.unitCredits, Math.round(l.interactions), Math.round(l.credits), l.eur.toFixed(2), (l.eur * 12).toFixed(2)]));
    state.azureResources.forEach((a) => rows.push([q("Azure : " + (a.name || "sans nom")), "", "", "", "", a.monthlyEur.toFixed(2), (a.monthlyEur * 12).toFixed(2)]));
    rows.push([q("TOTAL"), "", "", "", Math.round(r.creditsMonthly), r.monthlyEur.toFixed(2), r.annualEur.toFixed(2)]);
    rows.push([], [q("Taux USD->EUR"), state.usdToEur], [q("Prix du crédit (USD)"), state.creditPriceUsd]);
    const blob = new Blob(["﻿" + rows.map((x) => x.join(";")).join("\n")], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "estimation-copilot-studio.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  });

  renderAzure();
  render();
})();
