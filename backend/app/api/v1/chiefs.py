
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.turkish import turkish_sort_key
from app.db.session import get_db
from app.models.foreman import Chief, Foreman, ForemanAssignment
from app.models.kpi import Kpi
from app.models.organization import Factory, Plant
from app.schemas.common import Filters, PageParams, common_filters, page_params
from app.services import analytics
from app.services.kpi_engine import resolve_performance_level
from app.services.level_lookup import get_performance_levels, level_to_dict

router = APIRouter(prefix="/chiefs", tags=["chiefs"])


def _chiefs_in_scope(db: Session, filters: Filters, search: str | None, is_active: bool | None):
    query = select(Chief)
    if search:
        query = query.where(
            Chief.first_name.ilike(f"%{search}%")
            | Chief.last_name.ilike(f"%{search}%")
            | Chief.employee_number.ilike(f"%{search}%")
        )
    if is_active is not None:
        query = query.where(Chief.is_active == is_active)
    if filters.chief_ids:
        query = query.where(Chief.id.in_(filters.chief_ids))
    if filters.plant_ids:
        query = query.where(Chief.id.in_(select(Plant.chief_id).where(Plant.id.in_(filters.plant_ids))))
    if filters.factory_ids:
        query = query.where(
            Chief.id.in_(select(Plant.chief_id).where(Plant.factory_id.in_(filters.factory_ids)))
        )

    query = query.where(
        Chief.id.in_(
            select(ForemanAssignment.chief_id).where(
                ForemanAssignment.start_date <= filters.date_to,
                (ForemanAssignment.end_date.is_(None)) | (ForemanAssignment.end_date >= filters.date_from),
            )
        )
    )
    return list(db.scalars(query))


@router.get("")
def list_chiefs(
    search: str | None = Query(None),
    plant_id: UUID | None = Query(None),
    is_active: bool | None = Query(None),
    sort_by: str = Query("name", pattern="^(name|employee_number|plant|factory|foreman_count|score|level|reliability)$"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    page: PageParams = Depends(page_params),
    filters: Filters = Depends(common_filters),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    if plant_id:
        filters.plant_ids = [plant_id]

    levels = get_performance_levels(db)
    chiefs = _chiefs_in_scope(db, filters, search, is_active)

    teams_by_chief = {t.chief_id: t for t in analytics.chief_team_scores(db, filters)}
    factories_by_id = {f.id: f for f in db.scalars(select(Factory))}
    plants_by_chief: dict = {}
    for p in db.scalars(select(Plant)):
        plants_by_chief.setdefault(p.chief_id, []).append(p)

    full_items = []
    for c in chiefs:
        team = teams_by_chief.get(c.id)
        score = team.total_score if team else 0.0
        chief_plants = sorted(plants_by_chief.get(c.id, []), key=lambda p: p.sequence_number)
        factory = factories_by_id.get(chief_plants[0].factory_id) if chief_plants else None
        level = resolve_performance_level(score, levels)
        full_items.append(
            {
                "id": str(c.id),
                "employee_number": c.employee_number,
                "full_name": f"{c.first_name} {c.last_name}",
                "is_active": c.is_active,
                "plants": [{"id": str(p.id), "name": p.name} for p in chief_plants],
                "factory": {"id": str(factory.id), "code": factory.code, "name": factory.name} if factory else None,
                "foreman_count": team.foreman_count if team else 0,
                "total_score": round(score, 2),
                "is_reliable": team.is_reliable if team else False,
                "level": level_to_dict(level),
                "_sort": {
                    "name": (turkish_sort_key(c.first_name), turkish_sort_key(c.last_name)),
                    "employee_number": c.employee_number,
                    "plant": chief_plants[0].sequence_number if chief_plants else -1,
                    "factory": turkish_sort_key(factory.code) if factory else (),
                    "foreman_count": team.foreman_count if team else 0,
                    "score": score,
                    "level": level.sort_order,
                    "reliability": team.is_reliable if team else False,
                },
            }
        )

    full_items.sort(key=lambda it: it["_sort"][sort_by], reverse=sort_dir == "desc")
    for it in full_items:
        del it["_sort"]

    total = len(full_items)
    start = (page.page - 1) * page.page_size
    return {
        "items": full_items[start : start + page.page_size],
        "total": total,
        "page": page.page,
        "page_size": page.page_size,
    }


def _get_chief_or_404(db: Session, chief_id: UUID) -> Chief:
    chief = db.get(Chief, chief_id)
    if chief is None:
        raise HTTPException(404, "Şef bulunamadı.")
    return chief


@router.get("/{chief_id}")
def get_chief(
    chief_id: UUID, filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_user)
) -> dict:
    chief = _get_chief_or_404(db, chief_id)
    levels = get_performance_levels(db)
    chief_plants = sorted(
        db.scalars(select(Plant).where(Plant.chief_id == chief.id)), key=lambda p: p.sequence_number
    )
    factory = db.get(Factory, chief_plants[0].factory_id) if chief_plants else None

    ranking_filters = Filters(date_from=filters.date_from, date_to=filters.date_to, shift_ids=filters.shift_ids, kpi_ids=filters.kpi_ids)
    all_teams = analytics.chief_team_scores(db, ranking_filters)
    my_team = next((t for t in all_teams if t.chief_id == chief_id), None)
    score = my_team.total_score if my_team else 0.0

    ranked = sorted(all_teams, key=lambda t: t.total_score, reverse=True)
    company_rank = next((i + 1 for i, t in enumerate(ranked) if t.chief_id == chief_id), None)

    factory_chief_ids = (
        {p.chief_id for p in db.scalars(select(Plant).where(Plant.factory_id == factory.id))} if factory else set()
    )
    factory_ranked = [t for t in ranked if t.chief_id in factory_chief_ids]
    factory_rank = next((i + 1 for i, t in enumerate(factory_ranked) if t.chief_id == chief_id), None)

    return {
        "id": str(chief.id),
        "employee_number": chief.employee_number,
        "full_name": f"{chief.first_name} {chief.last_name}",
        "hire_date": chief.hire_date.isoformat(),
        "is_active": chief.is_active,
        "phone_number": chief.phone_number,
        "email": chief.email,
        "plants": [{"id": str(p.id), "name": p.name} for p in chief_plants],
        "factory": {"id": str(factory.id), "code": factory.code, "name": factory.name} if factory else None,
        "foreman_count": my_team.foreman_count if my_team else 0,
        "total_score": round(score, 2),
        "is_reliable": my_team.is_reliable if my_team else False,
        "level": level_to_dict(resolve_performance_level(score, levels)),
        "company_rank": company_rank,
        "company_total": len(ranked),
        "factory_rank": factory_rank,
        "factory_total": len(factory_ranked),
    }


@router.get("/{chief_id}/foremen")
def chief_foremen(
    chief_id: UUID, filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_user)
) -> dict:
    _get_chief_or_404(db, chief_id)
    filters.chief_ids = [chief_id]
    levels = get_performance_levels(db)

    team = next((t for t in analytics.chief_team_scores(db, filters) if t.chief_id == chief_id), None)
    scores = team.foreman_scores if team else []
    foremen_by_id = (
        {f.id: f for f in db.scalars(select(Foreman).where(Foreman.id.in_([s.key for s in scores])))} if scores else {}
    )

    items = []
    for s in sorted(scores, key=lambda x: x.total_score, reverse=True):
        f = foremen_by_id.get(s.key)
        items.append(
            {
                "id": str(s.key),
                "employee_number": f.employee_number if f else None,
                "full_name": f"{f.first_name} {f.last_name}" if f else None,
                "total_score": round(s.total_score, 2),
                "is_reliable": s.is_reliable,
                "level": level_to_dict(resolve_performance_level(s.total_score, levels)),
            }
        )
    return {"items": items}


@router.get("/{chief_id}/kpis")
def chief_kpis(
    chief_id: UUID, filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_user)
) -> dict:
    _get_chief_or_404(db, chief_id)
    filters.chief_ids = [chief_id]

    rows = analytics.kpi_breakdown(db, filters)
    kpis_by_id = {k.id: k for k in db.scalars(select(Kpi))}

    items = []
    for row in rows:
        kpi = kpis_by_id.get(row["kpi_id"])
        if kpi is None:
            continue
        avg_target = float(row["avg_target"]) if row["avg_target"] is not None else None
        avg_actual = float(row["avg_actual"]) if row["avg_actual"] is not None else None
        item = {
            "kpi_id": str(row["kpi_id"]), "code": kpi.code, "name": kpi.name,
            "description": kpi.description, "unit": kpi.unit,
            "avg_target": round(avg_target, kpi.decimal_places) if avg_target is not None else None,
            "avg_actual": round(avg_actual, kpi.decimal_places) if avg_actual is not None else None,
            "avg_raw_score": round(float(row["avg_raw_score"]), 2),
            "avg_capped_score": round(float(row["avg_capped_score"]), 2),
            "weight": float(row["weight"]),
            "weighted_contribution_sum": round(float(row["contrib_sum"]), 2),
            "record_count": row["record_count"],
            "calculation_version": row["calculation_version"],
            "calculation_period": {"date_from": filters.date_from.isoformat(), "date_to": filters.date_to.isoformat()},
            "data_quality_status": "complete" if row["record_count"] > 0 else "missing",
            "source_system": "SYNTHETIC",
        }
        if kpi.code == "AGIR_GITME" and avg_actual is not None:
            direction = "OVERWEIGHT" if avg_actual > 0 else ("UNDERWEIGHT" if avg_actual < 0 else "ON_TARGET")
            item["agir_gitme"] = {
                "signed_value": round(avg_actual, kpi.decimal_places),
                "absolute_value": round(abs(avg_actual), kpi.decimal_places),
                "direction": direction,
                "ratio_to_target": round(abs(avg_actual) / avg_target, 4) if avg_target else None,
            }
        elif kpi.code == "INKITA":
            item["inkita"] = {
                "included_total": item["avg_actual"],
                "included_components": ["TECHNICAL", "MANUFACTURING"],
                "excluded_components": ["OTHER"],
                "note": "Diğer duruş süresi puana dahil edilmez.",
            }
        elif kpi.code == "PLANA_UYUM" and avg_actual is not None:
            planned_qty = row.get("denominator_sum")
            actual_qty = row.get("numerator_sum")
            kg_diff = (actual_qty - planned_qty) if (planned_qty is not None and actual_qty is not None) else None
            signed_pct_deviation = (kg_diff / planned_qty * 100.0) if (kg_diff is not None and planned_qty) else None
            direction = (
                "ABOVE_PLAN" if (signed_pct_deviation or 0) > 0
                else ("BELOW_PLAN" if (signed_pct_deviation or 0) < 0 else "ON_PLAN")
            )
            item["plana_uyum"] = {
                "avg_attainment_pct": round(avg_actual, kpi.decimal_places),
                "planned_qty": round(planned_qty, 2) if planned_qty is not None else None,
                "actual_qty": round(actual_qty, 2) if actual_qty is not None else None,
                "kg_diff": round(kg_diff, 2) if kg_diff is not None else None,
                "signed_pct_deviation": round(signed_pct_deviation, 2) if signed_pct_deviation is not None else None,
                "direction": direction,
            }
        items.append(item)
    items.sort(key=lambda i: kpis_by_id[UUID(i["kpi_id"])].display_order)
    return {"items": items}


@router.get("/{chief_id}/trend")
def chief_trend(
    chief_id: UUID,
    granularity: str = Query("day", pattern="^(day|week|month|quarter|year)$"),
    filters: Filters = Depends(common_filters),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    _get_chief_or_404(db, chief_id)
    filters.chief_ids = [chief_id]
    points = analytics.trend(db, filters, granularity)
    return {
        "granularity": granularity,
        "points": [
            {"date": p.bucket.isoformat(), "total_score": round(p.total_score, 2), "is_reliable": p.is_reliable}
            for p in points
        ],
    }
