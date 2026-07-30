from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.turkish import turkish_sort_key
from app.db.session import get_db
from app.models.foreman import Chief, Foreman, ForemanAssignment
from app.models.kpi import Kpi, KpiCalculationRule
from app.models.organization import Plant, Shift
from app.schemas.common import Filters, PageParams, common_filters, page_params
from app.services import analytics
from app.services.kpi_engine import resolve_performance_level
from app.services.level_lookup import get_performance_levels, level_to_dict

router = APIRouter(prefix="/foremen", tags=["foremen"])


def _assignment_as_of(db: Session, foreman_id: UUID, as_of: date) -> ForemanAssignment | None:
    return db.scalar(
        select(ForemanAssignment)
        .where(
            ForemanAssignment.foreman_id == foreman_id,
            ForemanAssignment.start_date <= as_of,
        )
        .where((ForemanAssignment.end_date.is_(None)) | (ForemanAssignment.end_date >= as_of))
        .order_by(ForemanAssignment.start_date.desc())
        .limit(1)
    )


@router.get("")
def list_foremen(
    search: str | None = Query(None),
    plant_id: UUID | None = Query(None),
    chief_id: UUID | None = Query(None),
    shift_id: UUID | None = Query(None),
    is_active: bool | None = Query(None),
    sort_by: str = Query("name", pattern="^(name|employee_number|plant|chief|shift|score|level|reliability)$"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    page: PageParams = Depends(page_params),
    filters: Filters = Depends(common_filters),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    levels = get_performance_levels(db)

    query = select(Foreman)
    if search:
        query = query.where(
            Foreman.first_name.ilike(f"%{search}%")
            | Foreman.last_name.ilike(f"%{search}%")
            | Foreman.employee_number.ilike(f"%{search}%")
        )
    if is_active is not None:
        query = query.where(Foreman.is_active == is_active)

    if plant_id:
        filters.plant_ids = [plant_id]
    if chief_id:
        filters.chief_ids = [chief_id]
    if shift_id:
        filters.shift_ids = [shift_id]

    if filters.factory_ids or filters.plant_ids or filters.chief_ids or filters.shift_ids:
        assignment_query = select(ForemanAssignment.foreman_id).where(
            ForemanAssignment.start_date <= filters.date_to,
            (ForemanAssignment.end_date.is_(None)) | (ForemanAssignment.end_date >= filters.date_from),
        )
        if filters.factory_ids:
            assignment_query = assignment_query.where(
                ForemanAssignment.plant_id.in_(select(Plant.id).where(Plant.factory_id.in_(filters.factory_ids)))
            )
        if filters.plant_ids:
            assignment_query = assignment_query.where(ForemanAssignment.plant_id.in_(filters.plant_ids))
        if filters.chief_ids:
            assignment_query = assignment_query.where(ForemanAssignment.chief_id.in_(filters.chief_ids))
        if filters.shift_ids:
            assignment_query = assignment_query.where(ForemanAssignment.shift_id.in_(filters.shift_ids))
        query = query.where(Foreman.id.in_(assignment_query))

    all_foremen = list(db.scalars(query))

    scores_by_foreman = {s.key: s for s in analytics.foreman_scores(db, filters)}

    foreman_ids = [f.id for f in all_foremen]
    assignments_by_foreman: dict[UUID, list[ForemanAssignment]] = {}
    if foreman_ids:
        for a in db.scalars(select(ForemanAssignment).where(ForemanAssignment.foreman_id.in_(foreman_ids))):
            assignments_by_foreman.setdefault(a.foreman_id, []).append(a)
    plants_by_id = {p.id: p for p in db.scalars(select(Plant))}
    shifts_by_id = {s.id: s for s in db.scalars(select(Shift))}
    chiefs_by_id = {c.id: c for c in db.scalars(select(Chief))}

    factory_plant_ids = (
        {p.id for p in plants_by_id.values() if p.factory_id in set(filters.factory_ids)}
        if filters.factory_ids
        else None
    )

    def matches_filters(a: ForemanAssignment) -> bool:
        if factory_plant_ids is not None and a.plant_id not in factory_plant_ids:
            return False
        if filters.plant_ids and a.plant_id not in set(filters.plant_ids):
            return False
        if filters.chief_ids and a.chief_id not in set(filters.chief_ids):
            return False
        if filters.shift_ids and a.shift_id not in set(filters.shift_ids):
            return False
        return True

    def current_assignment(fid: UUID) -> ForemanAssignment | None:
        candidates = [
            a for a in assignments_by_foreman.get(fid, [])
            if a.start_date <= filters.date_to and (a.end_date is None or a.end_date >= filters.date_from)
        ]
        preferred = [a for a in candidates if matches_filters(a)] or candidates
        return max(preferred, key=lambda a: a.start_date) if preferred else None

    full_items = []
    for f in all_foremen:
        assignment = current_assignment(f.id)
        gs = scores_by_foreman.get(f.id)
        score = gs.total_score if gs else 0.0
        plant = plants_by_id.get(assignment.plant_id) if assignment else None
        shift = shifts_by_id.get(assignment.shift_id) if assignment else None
        chief = chiefs_by_id.get(assignment.chief_id) if assignment else None
        chief_name = f"{chief.first_name} {chief.last_name}" if chief else None
        level = resolve_performance_level(score, levels)
        full_items.append(
            {
                "id": str(f.id), "employee_number": f.employee_number,
                "full_name": f"{f.first_name} {f.last_name}", "is_active": f.is_active,
                "plant": {"id": str(plant.id), "name": plant.name} if plant else None,
                "chief": {"id": str(chief.id), "name": chief_name} if chief else None,
                "shift": {"id": str(shift.id), "name": shift.name} if shift else None,
                "total_score": round(score, 2),
                "is_reliable": gs.is_reliable if gs else False,
                "level": level_to_dict(level),
                "_sort": {
                    "name": (turkish_sort_key(f.first_name), turkish_sort_key(f.last_name)),
                    "employee_number": f.employee_number,
                    "plant": plant.sequence_number if plant else -1,
                    "chief": turkish_sort_key(chief_name) if chief_name else (),
                    "shift": turkish_sort_key(shift.name) if shift else (),
                    "score": score,
                    "level": level.sort_order,
                    "reliability": gs.is_reliable if gs else False,
                },
            }
        )

    reverse = sort_dir == "desc"
    full_items.sort(key=lambda it: it["_sort"][sort_by], reverse=reverse)
    for it in full_items:
        del it["_sort"]

    total = len(full_items)
    start = (page.page - 1) * page.page_size
    items = full_items[start : start + page.page_size]
    return {"items": items, "total": total, "page": page.page, "page_size": page.page_size}


@router.get("/{foreman_id}")
def get_foreman(
    foreman_id: UUID, filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_user)
) -> dict:
    foreman = db.get(Foreman, foreman_id)
    if foreman is None:
        raise HTTPException(404, "Formen bulunamadı.")

    levels = get_performance_levels(db)
    assignment = _assignment_as_of(db, foreman_id, filters.date_to)
    plant = db.get(Plant, assignment.plant_id) if assignment else None
    chief = db.get(Chief, assignment.chief_id) if assignment else None
    shift = db.get(Shift, assignment.shift_id) if assignment else None

    scoped_filters = Filters(date_from=filters.date_from, date_to=filters.date_to)
    all_scores = {s.key: s for s in analytics.foreman_scores(db, scoped_filters)}
    my_score = all_scores.get(foreman_id)
    total_score = my_score.total_score if my_score else 0.0

    ranked = sorted(all_scores.values(), key=lambda s: s.total_score, reverse=True)
    company_rank = next((i + 1 for i, s in enumerate(ranked) if s.key == foreman_id), None)

    plant_filters = Filters(date_from=filters.date_from, date_to=filters.date_to, plant_ids=[plant.id] if plant else None)
    plant_scores = sorted(analytics.foreman_scores(db, plant_filters), key=lambda s: s.total_score, reverse=True)
    plant_rank = next((i + 1 for i, s in enumerate(plant_scores) if s.key == foreman_id), None)

    return {
        "id": str(foreman.id), "employee_number": foreman.employee_number,
        "full_name": f"{foreman.first_name} {foreman.last_name}",
        "hire_date": foreman.hire_date.isoformat(), "is_active": foreman.is_active,
        "plant": {"id": str(plant.id), "name": plant.name} if plant else None,
        "chief": {"id": str(chief.id), "name": f"{chief.first_name} {chief.last_name}"} if chief else None,
        "shift": {"id": str(shift.id), "name": shift.name} if shift else None,
        "total_score": round(total_score, 2),
        "is_reliable": my_score.is_reliable if my_score else False,
        "level": level_to_dict(resolve_performance_level(total_score, levels)),
        "company_rank": company_rank,
        "company_total": len(ranked),
        "plant_rank": plant_rank,
        "plant_total": len(plant_scores),
    }


@router.get("/{foreman_id}/kpis")
def foreman_kpis(
    foreman_id: UUID, filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_user)
) -> dict:
    if db.get(Foreman, foreman_id) is None:
        raise HTTPException(404, "Formen bulunamadı.")

    rows = analytics.foreman_kpi_breakdown(db, filters, foreman_id)
    kpis_by_id = {k.id: k for k in db.scalars(select(Kpi))}

    items = []
    for row in rows:
        kpi = kpis_by_id.get(row["kpi_id"])
        if kpi is None:
            continue
        items.append(
            {
                "kpi_id": str(row["kpi_id"]), "code": kpi.code, "name": kpi.name, "unit": kpi.unit,
                "avg_target": round(float(row["avg_target"]), kpi.decimal_places) if row["avg_target"] is not None else None,
                "avg_actual": round(float(row["avg_actual"]), kpi.decimal_places) if row["avg_actual"] is not None else None,
                "avg_raw_score": round(float(row["avg_raw_score"]), 2),
                "avg_capped_score": round(float(row["avg_capped_score"]), 2),
                "weight": float(row["weight"]),
                "weighted_contribution_sum": round(float(row["contrib_sum"]), 2),
                "record_count": row["record_count"],
            }
        )
    items.sort(key=lambda i: kpis_by_id[UUID(i["kpi_id"])].display_order)
    return {"items": items}


@router.get("/{foreman_id}/kpis/{kpi_id}/calculation-detail")
def foreman_kpi_calculation_detail(foreman_id: UUID, kpi_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_user)) -> dict:
    row = analytics.latest_foreman_kpi_record(db, foreman_id, kpi_id)
    if row is None:
        raise HTTPException(404, "Bu formen/KPI için hesaplanmış kayıt bulunamadı.")
    record, score = row
    kpi = db.get(Kpi, kpi_id)
    rule = db.get(KpiCalculationRule, score.calculation_rule_id)
    return {
        "performance_date": record.performance_date.isoformat(),
        "target_value": float(record.target_value) if record.target_value is not None else None,
        "actual_value": float(record.actual_value) if record.actual_value is not None else None,
        "unit": record.unit,
        "calculation_type": rule.calculation_type.value if rule else None,
        "calculation_rule_parameters": rule.parameters if rule else None,
        "calculation_version": score.calculation_version,
        "raw_score": float(score.raw_score),
        "capped_score": float(score.capped_score),
        "min_score": float(kpi.min_score) if kpi else None,
        "max_score": float(kpi.max_score) if kpi else None,
        "kpi_weight": float(score.kpi_weight),
        "weighted_contribution": float(score.weighted_contribution),
        "data_source": record.source_system.value,
        "source_record_id": record.source_record_id,
    }


@router.get("/{foreman_id}/trend")
def foreman_trend(
    foreman_id: UUID,
    granularity: str = Query("day", pattern="^(day|week|month|quarter|year)$"),
    filters: Filters = Depends(common_filters),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    points = analytics.trend(db, filters, granularity, foreman_id=foreman_id)
    return {
        "granularity": granularity,
        "points": [
            {"date": p.bucket.isoformat(), "total_score": round(p.total_score, 2), "is_reliable": p.is_reliable}
            for p in points
        ],
    }


@router.get("/{foreman_id}/assignment-history")
def assignment_history(foreman_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_user)) -> dict:
    if db.get(Foreman, foreman_id) is None:
        raise HTTPException(404, "Formen bulunamadı.")
    assignments = list(
        db.scalars(
            select(ForemanAssignment).where(ForemanAssignment.foreman_id == foreman_id).order_by(ForemanAssignment.start_date)
        )
    )
    items = []
    for a in assignments:
        plant = db.get(Plant, a.plant_id)
        chief = db.get(Chief, a.chief_id)
        shift = db.get(Shift, a.shift_id)
        items.append(
            {
                "plant": plant.name if plant else None,
                "chief": f"{chief.first_name} {chief.last_name}" if chief else None,
                "shift": shift.name if shift else None,
                "start_date": a.start_date.isoformat(),
                "end_date": a.end_date.isoformat() if a.end_date else None,
                "is_active": a.is_active,
            }
        )
    return {"items": items}
