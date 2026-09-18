"""Catalogue statique (régions, SKUs, tiers...) + construction des filtres OData
pour l'API Azure Retail Prices + résolution de l'item de prix pertinent parmi
les résultats retournés (l'API renvoie souvent plusieurs entrées proches :
Spot, Windows/Linux, tiers de volume, etc.).

Les listes ci-dessous couvrent le premier périmètre demandé. Si Microsoft
change un nom de champ (meterName/skuName/productName), c'est ici qu'il
faudra ajuster la logique de correspondance.
"""
from __future__ import annotations

from typing import Any, Optional

HOURS_PER_MONTH_DEFAULT = 730

# ---------------------------------------------------------------------------
# Régions
# ---------------------------------------------------------------------------
REGIONS = [
    {"id": "francecentral", "label": "France Central"},
    {"id": "francesouth", "label": "France South"},
    {"id": "westeurope", "label": "West Europe"},
    {"id": "northeurope", "label": "North Europe"},
    {"id": "germanywestcentral", "label": "Germany West Central"},
    {"id": "switzerlandnorth", "label": "Switzerland North"},
    {"id": "uksouth", "label": "UK South"},
    {"id": "eastus", "label": "East US"},
    {"id": "eastus2", "label": "East US 2"},
    {"id": "westus2", "label": "West US 2"},
]

CURRENCIES = ["EUR", "USD", "GBP", "CHF"]

# ---------------------------------------------------------------------------
# Virtual Machines
# ---------------------------------------------------------------------------
VM_SKUS = [
    {"id": "Standard_B1s", "label": "B1s (1 vCPU, 1 GiB) - Burstable"},
    {"id": "Standard_B2s", "label": "B2s (2 vCPU, 4 GiB) - Burstable"},
    {"id": "Standard_D2s_v3", "label": "D2s v3 (2 vCPU, 8 GiB) - General purpose"},
    {"id": "Standard_D4s_v3", "label": "D4s v3 (4 vCPU, 16 GiB) - General purpose"},
    {"id": "Standard_D2s_v5", "label": "D2s v5 (2 vCPU, 8 GiB) - General purpose"},
    {"id": "Standard_D4s_v5", "label": "D4s v5 (4 vCPU, 16 GiB) - General purpose"},
    {"id": "Standard_E2s_v5", "label": "E2s v5 (2 vCPU, 16 GiB) - Memory optimized"},
    {"id": "Standard_E4s_v5", "label": "E4s v5 (4 vCPU, 32 GiB) - Memory optimized"},
    {"id": "Standard_F2s_v2", "label": "F2s v2 (2 vCPU, 4 GiB) - Compute optimized"},
]

VM_OS_OPTIONS = [
    {"id": "linux", "label": "Linux"},
    {"id": "windows", "label": "Windows"},
]


def build_vm_filter(region: str, sku: str) -> str:
    return (
        f"serviceName eq 'Virtual Machines' and armRegionName eq '{region}' "
        f"and armSkuName eq '{sku}' and type eq 'Consumption'"
    )


def resolve_vm_item(items: list[dict[str, Any]], os_choice: str) -> Optional[dict[str, Any]]:
    """Parmi les items VM, choisit l'entrée Linux ou Windows, hors Spot/Low priority."""
    candidates = []
    for item in items:
        product = item.get("productName", "")
        meter = item.get("meterName", "")
        if "Spot" in product or "Spot" in meter or "Low Priority" in product:
            continue
        is_windows = "Windows" in product
        if os_choice == "windows" and is_windows:
            candidates.append(item)
        elif os_choice == "linux" and not is_windows:
            candidates.append(item)
    if not candidates:
        return None
    # Plusieurs entrées peuvent rester (ex: promo régionale) : on prend la moins chère.
    return min(candidates, key=lambda i: i.get("retailPrice", float("inf")))


# ---------------------------------------------------------------------------
# Stockage Blob
# ---------------------------------------------------------------------------
STORAGE_TIERS = [
    {"id": "Hot", "label": "Hot (accès fréquent)"},
    {"id": "Cool", "label": "Cool (accès occasionnel)"},
    {"id": "Cold", "label": "Cold (accès rare)"},
    {"id": "Archive", "label": "Archive (archivage long terme)"},
]

STORAGE_REDUNDANCIES = [
    {"id": "LRS", "label": "LRS (locale)"},
    {"id": "ZRS", "label": "ZRS (zone)"},
    {"id": "GRS", "label": "GRS (géo-redondante)"},
]


def build_storage_filter(region: str, redundancy: str) -> str:
    return (
        f"serviceName eq 'Storage' and armRegionName eq '{region}' "
        f"and contains(productName, 'Blob') and contains(skuName, '{redundancy}')"
    )


def resolve_storage_item(items: list[dict[str, Any]], tier: str) -> Optional[dict[str, Any]]:
    """Cherche le meter 'Data Stored' (prix au Go/mois) pour le tier demandé,
    en prenant la tranche de volume de base (pas de palier tierMinimumUnits)."""
    candidates = [
        item
        for item in items
        if tier.lower() in item.get("skuName", "").lower()
        and "data stored" in item.get("meterName", "").lower()
        and item.get("unitOfMeasure") == "1 GB/Month"
        and item.get("type") == "Consumption"
    ]
    if not candidates:
        return None
    # tierMinimumUnits == 0 correspond au premier palier de volume (prix standard)
    base_tier = [c for c in candidates if c.get("tierMinimumUnits", 0) == 0]
    pool = base_tier or candidates
    return min(pool, key=lambda i: i.get("retailPrice", float("inf")))


# ---------------------------------------------------------------------------
# Azure SQL Database
# ---------------------------------------------------------------------------
SQL_TIERS = [
    {"id": "Basic", "label": "Basic (DTU)", "sku_name": "Basic"},
    {"id": "S0", "label": "Standard S0 (DTU)", "sku_name": "S0"},
    {"id": "S1", "label": "Standard S1 (DTU)", "sku_name": "S1"},
    {"id": "S2", "label": "Standard S2 (DTU)", "sku_name": "S2"},
    {"id": "S3", "label": "Standard S3 (DTU)", "sku_name": "S3"},
    {"id": "GP_Gen5_2", "label": "General Purpose - 2 vCore (Gen5)", "sku_name": "GP_Gen5_2"},
    {"id": "GP_Gen5_4", "label": "General Purpose - 4 vCore (Gen5)", "sku_name": "GP_Gen5_4"},
    {"id": "BC_Gen5_2", "label": "Business Critical - 2 vCore (Gen5)", "sku_name": "BC_Gen5_2"},
]


def build_sql_filter(region: str, sku_name: str) -> str:
    return (
        f"serviceName eq 'SQL Database' and armRegionName eq '{region}' "
        f"and skuName eq '{sku_name}' and type eq 'Consumption'"
    )


def resolve_sql_item(items: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    candidates = [i for i in items if i.get("unitOfMeasure") == "1 Hour"]
    pool = candidates or items
    if not pool:
        return None
    return min(pool, key=lambda i: i.get("retailPrice", float("inf")))


# ---------------------------------------------------------------------------
# Azure Cosmos DB
# ---------------------------------------------------------------------------
COSMOS_MODES = [
    {"id": "provisioned", "label": "Débit provisionné (RU/s)"},
    {"id": "serverless", "label": "Serverless (à la requête)"},
]


def build_cosmos_throughput_filter(region: str, mode: str) -> str:
    if mode == "serverless":
        return (
            f"serviceName eq 'Azure Cosmos DB' and armRegionName eq '{region}' "
            f"and contains(meterName, 'RU') and type eq 'Consumption'"
        )
    return (
        f"serviceName eq 'Azure Cosmos DB' and armRegionName eq '{region}' "
        f"and contains(skuName, 'Standard') and contains(meterName, '100 RU/s') "
        f"and type eq 'Consumption'"
    )


def build_cosmos_storage_filter(region: str) -> str:
    return (
        f"serviceName eq 'Azure Cosmos DB' and armRegionName eq '{region}' "
        f"and contains(meterName, 'Data Stored') and type eq 'Consumption'"
    )


def resolve_cosmos_throughput_item(items: list[dict[str, Any]], mode: str) -> Optional[dict[str, Any]]:
    candidates = [
        i
        for i in items
        if "multi-region" not in i.get("meterName", "").lower()
        and "multi region" not in i.get("productName", "").lower()
        and "free tier" not in i.get("skuName", "").lower()
    ]
    if mode == "serverless":
        candidates = [i for i in candidates if "1m ru" in i.get("meterName", "").lower() or "ru" in i.get("meterName", "").lower()]
    pool = candidates or items
    if not pool:
        return None
    return min(pool, key=lambda i: i.get("retailPrice", float("inf")))


def resolve_cosmos_storage_item(items: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    candidates = [i for i in items if i.get("unitOfMeasure") == "1 GB/Month"]
    pool = candidates or items
    if not pool:
        return None
    return min(pool, key=lambda i: i.get("retailPrice", float("inf")))


# ---------------------------------------------------------------------------
# Azure AI Search
# ---------------------------------------------------------------------------
AI_SEARCH_TIERS = [
    {"id": "free", "label": "Free", "sku_name": None, "flat_price": 0.0},
    {"id": "basic", "label": "Basic", "sku_name": "Basic"},
    {"id": "standard_s1", "label": "Standard S1", "sku_name": "Standard S1"},
    {"id": "standard_s2", "label": "Standard S2", "sku_name": "Standard S2"},
    {"id": "standard_s3", "label": "Standard S3", "sku_name": "Standard S3"},
]


def build_ai_search_filter(region: str, sku_name: str) -> str:
    return (
        f"serviceName eq 'Azure Search' and armRegionName eq '{region}' "
        f"and skuName eq '{sku_name}' and type eq 'Consumption'"
    )


def resolve_ai_search_item(items: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    candidates = [i for i in items if i.get("unitOfMeasure") == "1 Hour"]
    pool = candidates or items
    if not pool:
        return None
    return min(pool, key=lambda i: i.get("retailPrice", float("inf")))


# ---------------------------------------------------------------------------
# Azure OpenAI Service
# ---------------------------------------------------------------------------
# meter_keyword permet de retrouver les 2 meters (tokens en entrée / sortie)
# dans les résultats de l'API pour un modèle donné.
OPENAI_MODELS = [
    {"id": "gpt-4o", "label": "GPT-4o", "meter_keyword": "gpt-4o"},
    {"id": "gpt-4o-mini", "label": "GPT-4o mini", "meter_keyword": "gpt-4o-mini"},
    {"id": "gpt-4-turbo", "label": "GPT-4 Turbo", "meter_keyword": "gpt-4-turbo"},
    {"id": "gpt-35-turbo", "label": "GPT-3.5 Turbo", "meter_keyword": "gpt-35-turbo"},
    {"id": "text-embedding-3-small", "label": "Text Embedding 3 Small", "meter_keyword": "text-embedding-3-small"},
]


def build_openai_filter(region: str, meter_keyword: str) -> str:
    return (
        f"serviceName eq 'Cognitive Services' and armRegionName eq '{region}' "
        f"and contains(productName, 'OpenAI') and contains(meterName, '{meter_keyword}')"
    )


def resolve_openai_items(items: list[dict[str, Any]]) -> dict[str, Optional[dict[str, Any]]]:
    """Retourne les items 'input tokens' et 'output tokens' pour un modèle."""
    input_item, output_item = None, None
    for item in items:
        meter = item.get("meterName", "").lower()
        if "input" in meter or meter.endswith("inp tokens") or "inp tokens" in meter:
            if input_item is None or item.get("retailPrice", 0) < input_item.get("retailPrice", float("inf")):
                input_item = item
        elif "output" in meter or "outp tokens" in meter:
            if output_item is None or item.get("retailPrice", 0) < output_item.get("retailPrice", float("inf")):
                output_item = item
    return {"input": input_item, "output": output_item}


# ---------------------------------------------------------------------------
# Cognitive Services (hors OpenAI)
# ---------------------------------------------------------------------------
COGNITIVE_SERVICES_APIS = [
    {"id": "text_analytics_s0", "label": "Text Analytics - S0", "product_keyword": "Text Analytics", "sku_name": "S0"},
    {"id": "computer_vision_s1", "label": "Computer Vision - S1", "product_keyword": "Computer Vision", "sku_name": "S1"},
    {"id": "face_s0", "label": "Face API - S0", "product_keyword": "Face", "sku_name": "S0"},
]


def build_cognitive_services_filter(region: str, product_keyword: str, sku_name: str) -> str:
    return (
        f"serviceName eq 'Cognitive Services' and armRegionName eq '{region}' "
        f"and contains(productName, '{product_keyword}') and skuName eq '{sku_name}' "
        f"and type eq 'Consumption'"
    )


def resolve_cognitive_services_item(items: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not items:
        return None
    return min(items, key=lambda i: i.get("retailPrice", float("inf")))


# ---------------------------------------------------------------------------
# Catalogue exposé au frontend (GET /api/catalog)
# ---------------------------------------------------------------------------
def get_catalog() -> dict[str, Any]:
    return {
        "regions": REGIONS,
        "currencies": CURRENCIES,
        "services": {
            "vm": {
                "label": "Machine virtuelle",
                "skus": VM_SKUS,
                "os_options": VM_OS_OPTIONS,
            },
            "storage": {
                "label": "Stockage Blob",
                "tiers": STORAGE_TIERS,
                "redundancies": STORAGE_REDUNDANCIES,
            },
            "sql": {
                "label": "Azure SQL Database",
                "tiers": SQL_TIERS,
            },
            "cosmos": {
                "label": "Azure Cosmos DB",
                "modes": COSMOS_MODES,
            },
            "ai_search": {
                "label": "Azure AI Search",
                "tiers": AI_SEARCH_TIERS,
            },
            "openai": {
                "label": "Azure OpenAI Service",
                "models": OPENAI_MODELS,
            },
            "cognitive_services": {
                "label": "Cognitive Services",
                "apis": COGNITIVE_SERVICES_APIS,
            },
        },
    }
