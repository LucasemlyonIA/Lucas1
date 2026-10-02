# Calculateur de coûts Copilot Studio (pay-as-you-go)

Application web statique (HTML/CSS/JS, sans dépendance) : ouvrir `index.html`
dans un navigateur, ou `python -m http.server` depuis ce dossier.

## Formule

```
utilisateurs facturés = total − utilisateurs avec licence M365 Copilot
interactions/mois     = utilisateurs facturés × interactions par utilisateur
crédits/mois          = Σ (interactions × part du type × crédits du type)
coût Copilot (USD)    = crédits × 0,01
coût mensuel (EUR)    = coût Copilot (USD) × taux USD→EUR + ressources Azure (EUR/mois)
coût annuel           = coût mensuel × 12
```

Crédits par type : classique 1 · générative 2 · action d'agent 5 · appel de
ressource Azure 5 · grounding Microsoft Graph 10.

Hypothèse : chaque interaction relève d'un seul type (la répartition totalise
100 %). Le taux USD→EUR (0,92 par défaut) et le prix du crédit sont modifiables.
Les ressources Azure additionnelles sont saisies en € / mois.
Les valeurs sont conservées dans le `localStorage` du navigateur.

## Tests

```bash
node test.js
```
