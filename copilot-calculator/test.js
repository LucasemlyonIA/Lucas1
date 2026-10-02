const assert = require("assert");
const { compute, DEFAULTS } = require("./calc.js");

// Cas de référence : 1000 users dont 200 licenciés, 30 interactions, répartition par défaut
const r = compute(DEFAULTS);
assert.strictEqual(r.billableUsers, 800);
assert.strictEqual(r.interactionsBilled, 24000);
// crédits moyens/interaction = .4*1 + .4*2 + .1*5 + .05*5 + .05*10 = 2.45
assert.ok(Math.abs(r.creditsMonthly - 24000 * 2.45) < 1e-6);        // 58 800
assert.ok(Math.abs(r.copilotUsdMonthly - 588) < 1e-6);               // 588 $
assert.ok(Math.abs(r.copilotEurMonthly - 588 * 0.92) < 1e-6);
assert.ok(Math.abs(r.annualEur - 588 * 0.92 * 12) < 1e-6);
assert.ok(r.pctValid);

// Azure additionnel
const a = compute({ ...DEFAULTS, azureResources: [{ name: "Search", monthlyEur: 100 }, { name: "SQL", monthlyEur: 50 }] });
assert.ok(Math.abs(a.monthlyEur - (588 * 0.92 + 150)) < 1e-6);
assert.strictEqual(a.azureEurAnnual, 1800);

// Tous licenciés => 0 crédit ; licenciés > total plafonnés
assert.strictEqual(compute({ ...DEFAULTS, licensedUsers: 1000 }).creditsMonthly, 0);
assert.strictEqual(compute({ ...DEFAULTS, licensedUsers: 5000 }).billableUsers, 0);
// Entrées invalides
assert.strictEqual(compute({ ...DEFAULTS, totalUsers: "abc" }).monthlyEur, 0);
assert.ok(!compute({ ...DEFAULTS, types: DEFAULTS.types.map(t => ({ ...t, pct: 10 })) }).pctValid);
console.log("OK");
