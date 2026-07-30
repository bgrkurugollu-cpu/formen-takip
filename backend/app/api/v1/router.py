from fastapi import APIRouter

from app.api.v1 import (
    action_plans,
    audit_logs,
    auth,
    chiefs,
    dashboard,
    data_quality,
    foremen,
    integration,
    kpis,
    meta,
    plants,
    reports,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(meta.router)
api_router.include_router(dashboard.router)
api_router.include_router(plants.router)
api_router.include_router(foremen.router)
api_router.include_router(chiefs.router)
api_router.include_router(kpis.router)
api_router.include_router(data_quality.router)
api_router.include_router(integration.router)
api_router.include_router(audit_logs.router)
api_router.include_router(action_plans.router)
api_router.include_router(reports.router)
