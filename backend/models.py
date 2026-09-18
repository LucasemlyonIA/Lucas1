from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

ServiceType = Literal["vm", "storage", "sql", "cosmos", "ai_search", "openai", "cognitive_services"]


class ResourceLine(BaseModel):
    id: Optional[str] = None
    service: ServiceType
    region: str
    quantity: float = Field(default=1, gt=0)
    params: dict[str, Any] = Field(default_factory=dict)


class EstimateRequest(BaseModel):
    lines: list[ResourceLine]
    currency: str = "EUR"


class EstimateLineResult(BaseModel):
    id: Optional[str] = None
    service: ServiceType
    label: str
    unit_price: float
    unit: str
    quantity: float
    monthly_cost: float
    annual_cost: float
    currency: str
    warning: Optional[str] = None


class EstimateResponse(BaseModel):
    lines: list[EstimateLineResult]
    total_monthly: float
    total_annual: float
    currency: str
