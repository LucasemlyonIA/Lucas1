"""Client pour l'API publique Azure Retail Prices.

Documentation: https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices

Pas de clé API nécessaire. On construit un filtre OData ($filter), on paginate
via NextPageLink, et on met en cache le résultat (voir cache.py) pour éviter
de refaire l'appel à chaque interaction utilisateur.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

import httpx

from .cache import price_cache

logger = logging.getLogger(__name__)

BASE_URL = "https://prices.azure.com/api/retail/prices"
DEFAULT_CURRENCY = "EUR"
REQUEST_TIMEOUT = 15.0
MAX_PAGES = 10  # garde-fou anti-boucle infinie


class PricingApiError(RuntimeError):
    """Levée quand l'API Retail Prices est injoignable ou renvoie une erreur."""


def _cache_key(filter_str: str, currency: str) -> str:
    raw = f"{currency}|{filter_str}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def fetch_prices(filter_str: str, currency: str = DEFAULT_CURRENCY) -> list[dict[str, Any]]:
    """Récupère tous les items correspondant au filtre OData donné (avec cache)."""
    key = _cache_key(filter_str, currency)
    cached = price_cache.get(key)
    if cached is not None:
        return cached

    items: list[dict[str, Any]] = []
    params = {"$filter": filter_str, "currencyCode": currency}
    url: str | None = BASE_URL

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            page = 0
            while url and page < MAX_PAGES:
                response = await client.get(url, params=params if page == 0 else None)
                response.raise_for_status()
                payload = response.json()
                items.extend(payload.get("Items", []))
                url = payload.get("NextPageLink")
                page += 1
    except httpx.HTTPError as exc:
        raise PricingApiError(f"Erreur lors de l'appel à l'API Azure Retail Prices: {exc}") from exc

    price_cache.set(key, items)
    return items
