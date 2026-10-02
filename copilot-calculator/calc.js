/* Logique de calcul pure (utilisable dans le navigateur et sous Node pour les tests). */
(function (root) {
  "use strict";

  // Tarifs officiels Microsoft en crédits Copilot (Copilot Studio, pay-as-you-go).
  const DEFAULT_TYPES = [
    { id: "classic", label: "Réponse classique", credits: 1, pct: 40 },
    { id: "generative", label: "Réponse générative", credits: 2, pct: 40 },
    { id: "action", label: "Action d'agent", credits: 5, pct: 10 },
    { id: "azure", label: "Appel de ressource Azure", credits: 5, pct: 5 },
    { id: "graph", label: "Grounding Microsoft Graph", credits: 10, pct: 5 },
  ];
  const DEFAULTS = {
    totalUsers: 1000,
    licensedUsers: 200,
    interactions: 30,
    creditPriceUsd: 0.01,
    usdToEur: 0.92,
    types: DEFAULT_TYPES,
  };

  const num = (v) => (Number.isFinite(+v) && +v > 0 ? +v : 0);

  /**
   * @param {object} p
   * @param {number} p.totalUsers
   * @param {number} p.licensedUsers  utilisateurs M365 Copilot (0 crédit)
   * @param {number} p.interactions   interactions / utilisateur / mois
   * @param {Array<{id,label,credits,pct}>} p.types  pct en % (somme attendue = 100)
   * @param {number} p.creditPriceUsd
   * @param {number} p.usdToEur
   * @param {Array<{name,monthlyEur}>} [p.azureResources]  coûts Azure séparés, en EUR / mois
   */
  function compute(p) {
    const total = num(p.totalUsers);
    const licensed = Math.min(num(p.licensedUsers), total);
    const billable = total - licensed;
    const perUser = num(p.interactions);
    const price = num(p.creditPriceUsd);
    const fx = num(p.usdToEur);

    const pctSum = p.types.reduce((s, t) => s + num(t.pct), 0);
    const interactionsBilled = billable * perUser; // interactions des utilisateurs sans licence

    const lines = p.types.map((t) => {
      const share = num(t.pct) / 100;
      const interactions = interactionsBilled * share;
      const credits = interactions * num(t.credits);
      const usd = credits * price;
      return { id: t.id, label: t.label, pct: num(t.pct), unitCredits: num(t.credits), interactions, credits, usd, eur: usd * fx };
    });

    const credits = lines.reduce((s, l) => s + l.credits, 0);
    const copilotUsd = credits * price;
    const copilotEur = copilotUsd * fx;
    const azureEur = (p.azureResources || []).reduce((s, r) => s + num(r.monthlyEur), 0);
    const monthlyEur = copilotEur + azureEur;

    return {
      billableUsers: billable,
      licensedUsers: licensed,
      pctSum,
      pctValid: Math.abs(pctSum - 100) < 1e-6,
      interactionsBilled,
      lines,
      creditsMonthly: credits,
      creditsAnnual: credits * 12,
      copilotUsdMonthly: copilotUsd,
      copilotEurMonthly: copilotEur,
      copilotEurAnnual: copilotEur * 12,
      azureEurMonthly: azureEur,
      azureEurAnnual: azureEur * 12,
      monthlyEur,
      annualEur: monthlyEur * 12,
      avgCreditsPerInteraction: interactionsBilled ? credits / interactionsBilled : 0,
      costPerBillableUserEur: billable ? monthlyEur / billable : 0,
      costPerInteractionEur: interactionsBilled ? monthlyEur / interactionsBilled : 0,
    };
  }

  const api = { compute, DEFAULTS, DEFAULT_TYPES };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.CopilotCalc = api;
})(typeof window !== "undefined" ? window : globalThis);
