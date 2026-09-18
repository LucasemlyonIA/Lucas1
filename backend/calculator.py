"""Calcule le coût mensuel/annuel d'une ligne de ressource en s'appuyant sur
l'API Retail Prices (via pricing_client) et les règles de correspondance de
catalog.py.
"""
from __future__ import annotations

from . import catalog
from .models import EstimateLineResult, ResourceLine
from .pricing_client import fetch_prices


class EstimationError(ValueError):
    """Levée quand aucun prix correspondant n'a pu être trouvé pour une ligne."""


async def _calculate_vm(line: ResourceLine, currency: str) -> EstimateLineResult:
    sku = line.params.get("sku")
    os_choice = line.params.get("os", "linux")
    hours_per_month = float(line.params.get("hours_per_month", catalog.HOURS_PER_MONTH_DEFAULT))
    if not sku:
        raise EstimationError("Le paramètre 'sku' est requis pour une VM.")

    items = await fetch_prices(catalog.build_vm_filter(line.region, sku), currency)
    item = catalog.resolve_vm_item(items, os_choice)
    if not item:
        raise EstimationError(f"Aucun prix trouvé pour la VM {sku} ({os_choice}) en {line.region}.")

    unit_price = float(item["retailPrice"])
    monthly = unit_price * hours_per_month * line.quantity
    return EstimateLineResult(
        id=line.id,
        service=line.service,
        label=f"VM {sku} ({os_choice}) - {line.region}",
        unit_price=unit_price,
        unit="heure",
        quantity=line.quantity,
        monthly_cost=monthly,
        annual_cost=monthly * 12,
        currency=currency,
    )


async def _calculate_storage(line: ResourceLine, currency: str) -> EstimateLineResult:
    tier = line.params.get("tier", "Hot")
    redundancy = line.params.get("redundancy", "LRS")
    volume_gb = float(line.params.get("volume_gb", 100))

    items = await fetch_prices(catalog.build_storage_filter(line.region, redundancy), currency)
    item = catalog.resolve_storage_item(items, tier)
    if not item:
        raise EstimationError(f"Aucun prix trouvé pour Blob Storage {tier} {redundancy} en {line.region}.")

    unit_price = float(item["retailPrice"])
    monthly = unit_price * volume_gb * line.quantity
    return EstimateLineResult(
        id=line.id,
        service=line.service,
        label=f"Blob Storage {tier} {redundancy} - {line.region} ({volume_gb} Go)",
        unit_price=unit_price,
        unit="Go/mois",
        quantity=line.quantity,
        monthly_cost=monthly,
        annual_cost=monthly * 12,
        currency=currency,
    )


async def _calculate_sql(line: ResourceLine, currency: str) -> EstimateLineResult:
    tier_id = line.params.get("tier_id")
    hours_per_month = float(line.params.get("hours_per_month", catalog.HOURS_PER_MONTH_DEFAULT))
    tier_def = next((t for t in catalog.SQL_TIERS if t["id"] == tier_id), None)
    if not tier_def:
        raise EstimationError(f"Tier SQL Database inconnu: {tier_id}")

    items = await fetch_prices(catalog.build_sql_filter(line.region, tier_def["sku_name"]), currency)
    item = catalog.resolve_sql_item(items)
    if not item:
        raise EstimationError(f"Aucun prix trouvé pour SQL Database {tier_id} en {line.region}.")

    unit_price = float(item["retailPrice"])
    monthly = unit_price * hours_per_month * line.quantity
    return EstimateLineResult(
        id=line.id,
        service=line.service,
        label=f"SQL Database {tier_def['label']} - {line.region}",
        unit_price=unit_price,
        unit="heure",
        quantity=line.quantity,
        monthly_cost=monthly,
        annual_cost=monthly * 12,
        currency=currency,
    )


async def _calculate_cosmos(line: ResourceLine, currency: str) -> EstimateLineResult:
    mode = line.params.get("mode", "provisioned")
    storage_gb = float(line.params.get("storage_gb", 0))
    hours_per_month = float(line.params.get("hours_per_month", catalog.HOURS_PER_MONTH_DEFAULT))

    throughput_monthly = 0.0
    unit_price = 0.0
    unit = ""

    if mode == "provisioned":
        ru_per_sec = float(line.params.get("ru_per_sec", 400))
        items = await fetch_prices(catalog.build_cosmos_throughput_filter(line.region, mode), currency)
        item = catalog.resolve_cosmos_throughput_item(items, mode)
        if not item:
            raise EstimationError(f"Aucun prix trouvé pour Cosmos DB (provisioned) en {line.region}.")
        unit_price = float(item["retailPrice"])
        throughput_monthly = unit_price * (ru_per_sec / 100.0) * hours_per_month
        unit = "100 RU/s / heure"
    else:
        request_units_millions = float(line.params.get("request_units_millions", 1))
        items = await fetch_prices(catalog.build_cosmos_throughput_filter(line.region, mode), currency)
        item = catalog.resolve_cosmos_throughput_item(items, mode)
        if not item:
            raise EstimationError(f"Aucun prix trouvé pour Cosmos DB (serverless) en {line.region}.")
        unit_price = float(item["retailPrice"])
        throughput_monthly = unit_price * request_units_millions
        unit = "million de RU"

    storage_monthly = 0.0
    if storage_gb > 0:
        storage_items = await fetch_prices(catalog.build_cosmos_storage_filter(line.region), currency)
        storage_item = catalog.resolve_cosmos_storage_item(storage_items)
        if storage_item:
            storage_monthly = float(storage_item["retailPrice"]) * storage_gb

    monthly = (throughput_monthly + storage_monthly) * line.quantity
    return EstimateLineResult(
        id=line.id,
        service=line.service,
        label=f"Cosmos DB ({mode}) - {line.region}" + (f" + {storage_gb} Go stockés" if storage_gb else ""),
        unit_price=unit_price,
        unit=unit,
        quantity=line.quantity,
        monthly_cost=monthly,
        annual_cost=monthly * 12,
        currency=currency,
    )


async def _calculate_ai_search(line: ResourceLine, currency: str) -> EstimateLineResult:
    tier_id = line.params.get("tier_id")
    hours_per_month = float(line.params.get("hours_per_month", catalog.HOURS_PER_MONTH_DEFAULT))
    tier_def = next((t for t in catalog.AI_SEARCH_TIERS if t["id"] == tier_id), None)
    if not tier_def:
        raise EstimationError(f"Tier AI Search inconnu: {tier_id}")

    if tier_def["id"] == "free":
        return EstimateLineResult(
            id=line.id,
            service=line.service,
            label=f"AI Search Free - {line.region}",
            unit_price=0.0,
            unit="heure",
            quantity=line.quantity,
            monthly_cost=0.0,
            annual_cost=0.0,
            currency=currency,
        )

    items = await fetch_prices(catalog.build_ai_search_filter(line.region, tier_def["sku_name"]), currency)
    item = catalog.resolve_ai_search_item(items)
    if not item:
        raise EstimationError(f"Aucun prix trouvé pour AI Search {tier_id} en {line.region}.")

    unit_price = float(item["retailPrice"])
    monthly = unit_price * hours_per_month * line.quantity
    return EstimateLineResult(
        id=line.id,
        service=line.service,
        label=f"AI Search {tier_def['label']} - {line.region}",
        unit_price=unit_price,
        unit="heure",
        quantity=line.quantity,
        monthly_cost=monthly,
        annual_cost=monthly * 12,
        currency=currency,
    )


async def _calculate_openai(line: ResourceLine, currency: str) -> EstimateLineResult:
    model_id = line.params.get("model")
    input_tokens_millions = float(line.params.get("input_tokens_millions", 0))
    output_tokens_millions = float(line.params.get("output_tokens_millions", 0))
    model_def = next((m for m in catalog.OPENAI_MODELS if m["id"] == model_id), None)
    if not model_def:
        raise EstimationError(f"Modèle Azure OpenAI inconnu: {model_id}")

    items = await fetch_prices(catalog.build_openai_filter(line.region, model_def["meter_keyword"]), currency)
    resolved = catalog.resolve_openai_items(items)
    input_item, output_item = resolved["input"], resolved["output"]
    if not input_item and not output_item:
        raise EstimationError(f"Aucun prix trouvé pour Azure OpenAI {model_id} en {line.region}.")

    input_price = float(input_item["retailPrice"]) if input_item else 0.0
    output_price = float(output_item["retailPrice"]) if output_item else 0.0
    # Prix exprimés par 1K tokens dans l'API Retail Prices.
    monthly = (
        input_tokens_millions * 1000 * input_price + output_tokens_millions * 1000 * output_price
    ) * line.quantity

    warning = None
    if not output_item and output_tokens_millions:
        warning = "Prix des tokens de sortie introuvable, non inclus dans l'estimation."

    return EstimateLineResult(
        id=line.id,
        service=line.service,
        label=f"Azure OpenAI {model_def['label']} - {line.region}",
        unit_price=input_price,
        unit="1K tokens (entrée)",
        quantity=line.quantity,
        monthly_cost=monthly,
        annual_cost=monthly * 12,
        currency=currency,
        warning=warning,
    )


async def _calculate_cognitive_services(line: ResourceLine, currency: str) -> EstimateLineResult:
    api_id = line.params.get("api")
    transactions_thousands = float(line.params.get("transactions_thousands", 0))
    api_def = next((a for a in catalog.COGNITIVE_SERVICES_APIS if a["id"] == api_id), None)
    if not api_def:
        raise EstimationError(f"API Cognitive Services inconnue: {api_id}")

    items = await fetch_prices(
        catalog.build_cognitive_services_filter(line.region, api_def["product_keyword"], api_def["sku_name"]),
        currency,
    )
    item = catalog.resolve_cognitive_services_item(items)
    if not item:
        raise EstimationError(f"Aucun prix trouvé pour {api_def['label']} en {line.region}.")

    unit_price = float(item["retailPrice"])
    monthly = unit_price * transactions_thousands * line.quantity
    return EstimateLineResult(
        id=line.id,
        service=line.service,
        label=f"{api_def['label']} - {line.region}",
        unit_price=unit_price,
        unit="1K transactions",
        quantity=line.quantity,
        monthly_cost=monthly,
        annual_cost=monthly * 12,
        currency=currency,
    )


_DISPATCH = {
    "vm": _calculate_vm,
    "storage": _calculate_storage,
    "sql": _calculate_sql,
    "cosmos": _calculate_cosmos,
    "ai_search": _calculate_ai_search,
    "openai": _calculate_openai,
    "cognitive_services": _calculate_cognitive_services,
}


async def estimate_line(line: ResourceLine, currency: str) -> EstimateLineResult:
    handler = _DISPATCH.get(line.service)
    if not handler:
        raise EstimationError(f"Service inconnu: {line.service}")
    return await handler(line, currency)
