# Simulateur de coûts Azure

Application locale (FastAPI + HTML/CSS/JS) qui estime le coût mensuel/annuel
de ressources Azure en s'appuyant sur l'[API publique Azure Retail Prices](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices)
(aucune clé requise).

## Démarrage

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Puis ouvre http://127.0.0.1:8000 dans ton navigateur.

## Fonctionnement

- Choisis une région, un service (VM, Blob Storage, SQL Database, Cosmos DB,
  AI Search, Azure OpenAI, Cognitive Services), ses paramètres, puis
  "Ajouter la ligne".
- Chaque ligne interroge l'API Retail Prices (résultat mis en cache 24h dans
  `cache/prices_cache.json` pour éviter les appels répétés) et affiche son
  prix unitaire, son coût mensuel et annuel.
- Le total général se met à jour automatiquement.
- Boutons "Exporter JSON" / "Exporter CSV" pour sauvegarder l'estimation.

## Structure

```
app.py                  # lance uvicorn
backend/
  main.py               # routes FastAPI (/api/catalog, /api/estimate, /api/export)
  catalog.py             # régions/SKUs/tiers + construction des filtres OData + résolution des prix
  calculator.py          # calcul coût unitaire -> mensuel/annuel par service
  pricing_client.py       # appel HTTP à l'API Retail Prices + pagination
  cache.py               # cache disque JSON avec TTL
  models.py              # schémas Pydantic
frontend/
  index.html, style.css, app.js
```

## Limites connues / points à surveiller

- L'API Retail Prices renvoie parfois plusieurs entrées proches pour un même
  filtre (Spot, Windows/Linux, paliers de volume...). La logique de sélection
  se trouve dans `catalog.py` (fonctions `resolve_*`) : si Microsoft modifie
  un `meterName`/`skuName`/`productName`, c'est là qu'il faut ajuster.
- Le mapping des tarifs Azure OpenAI (`catalog.OPENAI_MODELS`) et Cognitive
  Services est simplifié pour le premier périmètre ; certains modèles très
  récents peuvent nécessiter l'ajout d'une entrée dans le catalogue.
- Le développement a été fait dans un environnement dont l'accès sortant
  vers `prices.azure.com` est bloqué : la logique de calcul a été validée
  avec des données simulées reproduisant le format de l'API, mais un test
  en conditions réelles (sur ta machine) est recommandé pour confirmer que
  les filtres renvoient bien les prix attendus pour chaque service.
