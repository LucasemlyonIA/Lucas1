from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import catalog
from .calculator import EstimationError, estimate_line
from .models import EstimateLineResult, EstimateRequest, EstimateResponse
from .pricing_client import PricingApiError

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="Azure Cost Simulator")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/catalog")
async def get_catalog() -> JSONResponse:
    return JSONResponse(catalog.get_catalog())


async def _compute_estimate(request: EstimateRequest) -> EstimateResponse:
    results = []
    for line in request.lines:
        try:
            result = await estimate_line(line, request.currency)
        except (EstimationError, PricingApiError) as exc:
            result = None
            error_message = str(exc)
        else:
            error_message = None

        if result is None:
            results.append(
                EstimateLineResult(
                    id=line.id,
                    service=line.service,
                    label=f"{line.service} - {line.region} (erreur)",
                    unit_price=0.0,
                    unit="",
                    quantity=line.quantity,
                    monthly_cost=0.0,
                    annual_cost=0.0,
                    currency=request.currency,
                    warning=error_message,
                )
            )
        else:
            results.append(result)

    total_monthly = sum(r.monthly_cost for r in results)
    total_annual = sum(r.annual_cost for r in results)
    return EstimateResponse(
        lines=results,
        total_monthly=total_monthly,
        total_annual=total_annual,
        currency=request.currency,
    )


@app.post("/api/estimate", response_model=EstimateResponse)
async def post_estimate(request: EstimateRequest) -> EstimateResponse:
    return await _compute_estimate(request)


@app.post("/api/export")
async def export_estimate(request: EstimateRequest, format: str = "json") -> Response:
    estimate = await _compute_estimate(request)

    if format == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["service", "label", "unit_price", "unit", "quantity", "monthly_cost", "annual_cost", "currency"])
        for line in estimate.lines:
            writer.writerow(
                [line.service, line.label, line.unit_price, line.unit, line.quantity, line.monthly_cost, line.annual_cost, line.currency]
            )
        writer.writerow([])
        writer.writerow(["TOTAL", "", "", "", "", estimate.total_monthly, estimate.total_annual, estimate.currency])
        return Response(
            content=buffer.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=estimation_azure.csv"},
        )

    return Response(
        content=json.dumps(estimate.model_dump(), ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=estimation_azure.json"},
    )
