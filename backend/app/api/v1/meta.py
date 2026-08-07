from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.foreman import Chief
from app.models.kpi import Kpi
from app.models.organization import Factory, Plant, Shift

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/filters")
def get_filter_options(
    plant_ids: str | None = Query(None, description="Virgülle ayrılmış tesis ID listesi"),
    factory_ids: str | None = Query(None, description="Virgülle ayrılmış fabrika ID listesi"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    factories = list(db.scalars(select(Factory).where(Factory.is_active.is_(True)).order_by(Factory.code)))

    plant_query = select(Plant).where(Plant.is_active.is_(True))
    if factory_ids:
        ids = [UUID(v) for v in factory_ids.split(",") if v.strip()]
        plant_query = plant_query.where(Plant.factory_id.in_(ids))
    plants = list(db.scalars(plant_query.order_by(Plant.sequence_number)))

    chief_query = select(Chief).where(Chief.is_active.is_(True))
    if plant_ids:
        ids = [UUID(v) for v in plant_ids.split(",") if v.strip()]
        chief_query = chief_query.where(Chief.id.in_(select(Plant.chief_id).where(Plant.id.in_(ids))))
    elif factory_ids:
        ids = [UUID(v) for v in factory_ids.split(",") if v.strip()]
        chief_query = chief_query.where(Chief.id.in_(select(Plant.chief_id).where(Plant.factory_id.in_(ids))))
    chiefs = list(db.scalars(chief_query.order_by(Chief.employee_number)))
    plant_ids_by_chief: dict = {}
    for p in db.scalars(select(Plant)):
        plant_ids_by_chief.setdefault(p.chief_id, []).append(str(p.id))

    shifts = list(db.scalars(select(Shift).where(Shift.is_active.is_(True)).order_by(Shift.sequence)))
    kpis = list(db.scalars(select(Kpi).where(Kpi.is_active.is_(True)).order_by(Kpi.display_order)))

    return {
        "factories": [{"id": str(f.id), "code": f.code, "name": f.name, "location": f.location} for f in factories],
        "plants": [
            {"id": str(p.id), "code": p.code, "name": p.name, "sequence_number": p.sequence_number, "factory_id": str(p.factory_id)}
            for p in plants
        ],
        "chiefs": [
            {
                "id": str(c.id), "employee_number": c.employee_number, "name": f"{c.first_name} {c.last_name}",
                "plant_ids": plant_ids_by_chief.get(c.id, []),
            }
            for c in chiefs
        ],
        "shifts": [{"id": str(s.id), "code": s.code, "name": s.name, "sequence": s.sequence} for s in shifts],
        "kpis": [
            {"id": str(k.id), "code": k.code, "name": k.name, "unit": k.unit, "weight": float(k.weight)}
            for k in kpis
        ],
    }
