from fastapi import APIRouter

from app.api.v1 import (
    anomalies,
    auth,
    chiefs,
    contributions,
    dashboard,
    foremen,
    kpis,
    meta,
    plants,
    reports,
    shift_analysis,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(meta.router)
api_router.include_router(dashboard.router)
api_router.include_router(plants.router)
api_router.include_router(foremen.router)
api_router.include_router(chiefs.router)
api_router.include_router(kpis.router)
api_router.include_router(reports.router)
api_router.include_router(contributions.router)
api_router.include_router(anomalies.router)
api_router.include_router(anomalies.analyses_router)
api_router.include_router(shift_analysis.router)
