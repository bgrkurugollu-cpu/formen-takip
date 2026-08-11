from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.turkish import turkish_sort_key
from app.db.session import get_db
from app.models.foreman import Chief, Foreman, ForemanAssignment
from app.models.kpi import Kpi
from app.models.organization import Factory, Plant, Shift
from app.schemas.common import Filters, PageParams, common_filters, page_params
from app.services import analytics, shift_analysis
from app.services.kpi_engine import resolve_performance_level
from app.services.level_lookup import get_performance_levels, level_to_dict

router = APIRouter(prefix="/plants", tags=["plants"])


def _factory_ref(db: Session, factory_id: UUID) -> dict | None:
    factory = db.get(Factory, factory_id)
    if factory is None:
        return None
    return {"id": str(factory.id), "code": factory.code, "name": factory.name}


@router.get("")
def list_plants(
    search: str | None = Query(None),
    factory_id: UUID | None = Query(None),
    is_active: bool | None = Query(None),
    sort_by: str = Query("sequence", pattern="^(sequence|name|factory|active_foreman_count|score|level)$"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    page: PageParams = Depends(page_params),
    filters: Filters = Depends(common_filters),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    levels = get_performance_levels(db)
    query = select(Plant)
    if search:
        query = query.where(Plant.name.ilike(f"%{search}%") | Plant.code.ilike(f"%{search}%"))
    if factory_id:
        query = query.where(Plant.factory_id == factory_id)
    if is_active is not None:
        query = query.where(Plant.is_active == is_active)

    if filters.factory_ids:
        query = query.where(Plant.factory_id.in_(filters.factory_ids))
    if filters.plant_ids:
        query = query.where(Plant.id.in_(filters.plant_ids))

    all_plants = list(db.scalars(query.order_by(Plant.sequence_number)))

    scores_by_plant = {s.key: s for s in analytics.plant_scores(db, filters)}
    factories_by_id = {f.id: f for f in db.scalars(select(Factory))}
    active_foreman_counts = dict(
        db.execute(
            select(ForemanAssignment.plant_id, func.count(func.distinct(ForemanAssignment.foreman_id)))
            .join(Foreman, Foreman.id == ForemanAssignment.foreman_id)
            .where(Foreman.is_active.is_(True))
            .group_by(ForemanAssignment.plant_id)
        ).all()
    )

    full_items = []
    for p in all_plants:
        gs = scores_by_plant.get(p.id)
        score = gs.total_score if gs else 0.0
        active_foremen = active_foreman_counts.get(p.id, 0)
        factory = factories_by_id.get(p.factory_id)
        level = resolve_performance_level(score, levels)
        full_items.append(
            {
                "id": str(p.id), "code": p.code, "name": p.name, "sequence_number": p.sequence_number,
                "factory": {"id": str(factory.id), "code": factory.code, "name": factory.name} if factory else None,
                "is_active": p.is_active, "total_score": round(score, 2),
                "level": level_to_dict(level),
                "active_foreman_count": active_foremen,
                "record_count": gs.record_count if gs else 0,
                "_sort": {
                    "sequence": p.sequence_number,
                    "name": turkish_sort_key(p.name),
                    "factory": turkish_sort_key(factory.name) if factory else (),
                    "active_foreman_count": active_foremen,
                    "score": score,
                    "level": level.sort_order,
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


@router.get("/{plant_id}")
def get_plant(plant_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_user)) -> dict:
    plant = db.get(Plant, plant_id)
    if plant is None:
        raise HTTPException(404, "Tesis bulunamadı.")
    return {
        "id": str(plant.id), "code": plant.code, "name": plant.name, "sequence_number": plant.sequence_number,
        "factory": _factory_ref(db, plant.factory_id),
        "description": plant.description, "is_active": plant.is_active, "sap_plant_code": plant.sap_plant_code,
    }


@router.get("/{plant_id}/summary")
def plant_summary(
    plant_id: UUID, filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_user)
) -> dict:
    plant = db.get(Plant, plant_id)
    if plant is None:
        raise HTTPException(404, "Tesis bulunamadı.")
    filters.plant_ids = [plant_id]
    levels = get_performance_levels(db)

    f_scores = analytics.foreman_scores(db, filters)
    score = sum(s.total_score for s in f_scores) / len(f_scores) if f_scores else 0.0
    critical_count = sum(1 for s in f_scores if resolve_performance_level(s.total_score, levels).name == "Kritik")

    kpi_items = analytics.kpi_summary(db, filters)
    kpis_by_id = {k.id: k for k in db.scalars(select(Kpi))}
    strongest = max(kpi_items, key=lambda i: i.avg_capped_score, default=None)
    weakest = min(kpi_items, key=lambda i: i.avg_capped_score, default=None)

    active_foremen = db.scalar(
        select(func.count(func.distinct(ForemanAssignment.foreman_id)))
        .join(Foreman, Foreman.id == ForemanAssignment.foreman_id)
        .where(ForemanAssignment.plant_id == plant_id, Foreman.is_active.is_(True))
    )

    return {
        "plant_id": str(plant_id),
        "total_score": round(score, 2),
        "level": level_to_dict(resolve_performance_level(score, levels)),
        "active_foreman_count": active_foremen or 0,
        "critical_foreman_count": critical_count,
        "strongest_kpi": (
            {"id": str(strongest.kpi_id), "name": kpis_by_id[strongest.kpi_id].name, "avg_score": round(strongest.avg_capped_score, 2)}
            if strongest else None
        ),
        "weakest_kpi": (
            {"id": str(weakest.kpi_id), "name": kpis_by_id[weakest.kpi_id].name, "avg_score": round(weakest.avg_capped_score, 2)}
            if weakest else None
        ),
    }


@router.get("/{plant_id}/kpis")
def plant_kpis(
    plant_id: UUID, filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_user)
) -> dict:
    filters.plant_ids = [plant_id]
    items = analytics.kpi_summary(db, filters)
    kpis_by_id = {k.id: k for k in db.scalars(select(Kpi))}
    return {
        "items": [
            {
                "kpi_id": str(i.kpi_id), "code": kpis_by_id[i.kpi_id].code, "name": kpis_by_id[i.kpi_id].name,
                "unit": kpis_by_id[i.kpi_id].unit, "avg_score": round(i.avg_capped_score, 2),
                "avg_target": round(i.avg_target, 2) if i.avg_target is not None else None,
                "avg_actual": round(i.avg_actual, 2) if i.avg_actual is not None else None,
            }
            for i in items if i.kpi_id in kpis_by_id
        ]
    }


@router.get("/{plant_id}/shifts")
def plant_shifts(
    plant_id: UUID, filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_user)
) -> dict:
    filters.plant_ids = [plant_id]
    levels = get_performance_levels(db)
    scores = analytics.shift_scores(db, filters)
    shifts_by_id = {s.id: s for s in db.scalars(select(Shift))}
    scores.sort(key=lambda s: shifts_by_id[s.key].sequence if s.key in shifts_by_id else 0)
    return {
        "items": [
            {
                "shift_id": str(s.key), "code": shifts_by_id[s.key].code, "name": shifts_by_id[s.key].name,
                "total_score": round(s.total_score, 2), "level": level_to_dict(resolve_performance_level(s.total_score, levels)),
            }
            for s in scores if s.key in shifts_by_id
        ]
    }


@router.get("/{plant_id}/chiefs")
def plant_chiefs(
    plant_id: UUID, filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_user)
) -> dict:
    filters.plant_ids = [plant_id]
    levels = get_performance_levels(db)
    scores_by_chief = {s.key: s for s in analytics.chief_scores(db, filters)}
    plant = db.get(Plant, plant_id)
    chief_ids = [plant.chief_id] if plant else []
    chiefs = list(db.scalars(select(Chief).where(Chief.id.in_(chief_ids)).order_by(Chief.employee_number)))

    items = []
    for c in chiefs:
        foreman_count = db.scalar(
            select(func.count(func.distinct(ForemanAssignment.foreman_id)))
            .join(Foreman, Foreman.id == ForemanAssignment.foreman_id)
            .where(ForemanAssignment.chief_id == c.id, Foreman.is_active.is_(True))
        )
        gs = scores_by_chief.get(c.id)
        score = gs.total_score if gs else 0.0
        items.append(
            {
                "id": str(c.id), "employee_number": c.employee_number,
                "full_name": f"{c.first_name} {c.last_name}",
                "foreman_count": foreman_count or 0,
                "total_score": round(score, 2),
                "level": level_to_dict(resolve_performance_level(score, levels)),
            }
        )
    return {"items": items}


@router.get("/{plant_id}/foreman-shift-matrix")
def plant_foreman_shift_matrix(
    plant_id: UUID,
    kpi_id: UUID = Query(...),
    filters: Filters = Depends(common_filters),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    matrix = shift_analysis.build_foreman_shift_matrix(db, filters, plant_id, kpi_id)
    if matrix is None:
        raise HTTPException(404, "Bu tesis/KPI kombinasyonu için formen-vardiya karşılaştırması yapılacak veri bulunamadı.")

    levels = get_performance_levels(db)

    def cell_dict(cell: shift_analysis.ForemanShiftCell | None) -> dict | None:
        if cell is None:
            return None
        deviation_pct = (
            (cell.avg_actual - cell.avg_target) / abs(cell.avg_target) * 100.0 if cell.avg_target else None
        )
        return {
            "avg_actual": round(cell.avg_actual, 2), "avg_target": round(cell.avg_target, 2),
            "score": round(cell.capped_score, 2), "record_count": cell.record_count,
            "deviation_pct": round(deviation_pct, 1) if deviation_pct is not None else None,
            "level": level_to_dict(resolve_performance_level(cell.capped_score, levels)),
        }

    return {
        "kpi": {
            "id": str(matrix.kpi_id), "code": matrix.kpi_code, "name": matrix.kpi_name, "unit": matrix.kpi_unit,
            "success_direction_higher": matrix.success_direction_higher,
        },
        "reference_target": round(matrix.reference_target, 2),
        "shifts": [{"id": str(s.id), "code": s.code, "name": s.name} for s in matrix.shifts],
        "rows": [
            {
                "foreman_id": str(row.foreman_id), "full_name": row.name, "employee_number": row.employee_number,
                "cells": {str(shift_id): cell_dict(cell) for shift_id, cell in row.cells.items()},
            }
            for row in matrix.rows
        ],
        "insight": matrix.insight,
    }


@router.get("/{plant_id}/foremen")
def plant_foremen(
    plant_id: UUID,
    page: PageParams = Depends(page_params),
    filters: Filters = Depends(common_filters),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    filters.plant_ids = [plant_id]
    levels = get_performance_levels(db)
    scores = analytics.foreman_scores(db, filters)
    scores.sort(key=lambda s: s.total_score, reverse=True)
    total = len(scores)
    start = (page.page - 1) * page.page_size
    page_scores = scores[start : start + page.page_size]

    foreman_ids = [s.key for s in page_scores]
    foremen_by_id = {f.id: f for f in db.scalars(select(Foreman).where(Foreman.id.in_(foreman_ids)))} if foreman_ids else {}

    return {
        "items": [
            {
                "foreman_id": str(s.key),
                "employee_number": foremen_by_id[s.key].employee_number if s.key in foremen_by_id else None,
                "full_name": f"{foremen_by_id[s.key].first_name} {foremen_by_id[s.key].last_name}" if s.key in foremen_by_id else None,
                "total_score": round(s.total_score, 2),
                "level": level_to_dict(resolve_performance_level(s.total_score, levels)),
            }
            for s in page_scores
        ],
        "total": total, "page": page.page, "page_size": page.page_size,
    }
