from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.turkish import turkish_sort_key
from app.db.session import get_db
from app.models.contribution import ContributionWork, ContributionWorkForeman
from app.models.enums import ContributionRole, ContributionStatus, ContributionWorkType
from app.models.foreman import Chief, Foreman, ForemanAssignment
from app.models.kpi import Kpi, KpiCalculationRule
from app.models.organization import Plant, Shift
from app.schemas.common import Filters, PageParams, common_filters, page_params
from app.services import analytics
from app.services.kpi_engine import resolve_performance_level
from app.services.level_lookup import get_performance_levels, level_to_dict

router = APIRouter(prefix="/foremen", tags=["foremen"])


def _assignments_as_of(db: Session, foreman_id: UUID, as_of: date) -> list[ForemanAssignment]:
    return list(
        db.scalars(
            select(ForemanAssignment)
            .where(
                ForemanAssignment.foreman_id == foreman_id,
                ForemanAssignment.start_date <= as_of,
            )
            .where((ForemanAssignment.end_date.is_(None)) | (ForemanAssignment.end_date >= as_of))
        )
    )


def _assignments_to_dict(
    assignments: list[ForemanAssignment], plants_by_id: dict, chiefs_by_id: dict
) -> list[dict]:
    ordered = sorted(assignments, key=lambda a: plants_by_id[a.plant_id].sequence_number)
    items = []
    for a in ordered:
        plant = plants_by_id[a.plant_id]
        chief = chiefs_by_id[a.chief_id]
        items.append(
            {
                "plant": {"id": str(plant.id), "name": plant.name},
                "chief": {"id": str(chief.id), "name": f"{chief.first_name} {chief.last_name}"},
            }
        )
    return items


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

    def matching_assignments(fid: UUID) -> list[ForemanAssignment]:
        candidates = [
            a for a in assignments_by_foreman.get(fid, [])
            if a.start_date <= filters.date_to and (a.end_date is None or a.end_date >= filters.date_from)
        ]
        return [a for a in candidates if matches_filters(a)] or candidates

    full_items = []
    for f in all_foremen:
        assignments = matching_assignments(f.id)
        gs = scores_by_foreman.get(f.id)
        score = gs.total_score if gs else 0.0
        shift = shifts_by_id.get(assignments[0].shift_id) if assignments else None
        assignment_items = _assignments_to_dict(assignments, plants_by_id, chiefs_by_id)
        min_plant_seq = min(
            (plants_by_id[a.plant_id].sequence_number for a in assignments), default=-1
        )
        # Bir formen artık her zaman TEK bir şefe bağlı olduğundan (bkz. Organizasyon
        # Hiyerarşisi), tüm atamalar aynı şefi taşır — ilkini almak yeterlidir.
        chief_name = assignment_items[0]["chief"]["name"] if assignment_items else ""
        level = resolve_performance_level(score, levels)
        full_items.append(
            {
                "id": str(f.id), "employee_number": f.employee_number,
                "full_name": f"{f.first_name} {f.last_name}", "is_active": f.is_active,
                "assignments": assignment_items,
                "shift": {"id": str(shift.id), "name": shift.name} if shift else None,
                "total_score": round(score, 2),
                "is_reliable": gs.is_reliable if gs else False,
                "level": level_to_dict(level),
                "_sort": {
                    "name": (turkish_sort_key(f.first_name), turkish_sort_key(f.last_name)),
                    "employee_number": f.employee_number,
                    "plant": min_plant_seq,
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
    assignments = _assignments_as_of(db, foreman_id, filters.date_to)
    plants_by_id = {p.id: p for p in db.scalars(select(Plant).where(Plant.id.in_({a.plant_id for a in assignments})))}
    chiefs_by_id = {c.id: c for c in db.scalars(select(Chief).where(Chief.id.in_({a.chief_id for a in assignments})))}
    assignment_items = _assignments_to_dict(assignments, plants_by_id, chiefs_by_id)
    shift = db.get(Shift, assignments[0].shift_id) if assignments else None
    # "Tesis İçi Sıralaması" formen birden fazla tesise bağlı olabileceğinden, sıralama
    # yalnızca formenin en düşük sıra numaralı (birincil) tesisine göre hesaplanır.
    primary_plant = min(
        (plants_by_id[a.plant_id] for a in assignments), key=lambda p: p.sequence_number, default=None
    )

    scoped_filters = Filters(date_from=filters.date_from, date_to=filters.date_to)
    all_scores = {s.key: s for s in analytics.foreman_scores(db, scoped_filters)}
    my_score = all_scores.get(foreman_id)
    total_score = my_score.total_score if my_score else 0.0

    ranked = sorted(all_scores.values(), key=lambda s: s.total_score, reverse=True)
    company_rank = next((i + 1 for i, s in enumerate(ranked) if s.key == foreman_id), None)

    plant_filters = Filters(
        date_from=filters.date_from, date_to=filters.date_to,
        plant_ids=[primary_plant.id] if primary_plant else None,
    )
    plant_scores = sorted(analytics.foreman_scores(db, plant_filters), key=lambda s: s.total_score, reverse=True)
    plant_rank = next((i + 1 for i, s in enumerate(plant_scores) if s.key == foreman_id), None)

    return {
        "id": str(foreman.id), "employee_number": foreman.employee_number,
        "full_name": f"{foreman.first_name} {foreman.last_name}",
        "hire_date": foreman.hire_date.isoformat(), "is_active": foreman.is_active,
        "assignments": assignment_items,
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
        # KPI'a özel ek alanlar (spec bölüm 14) — mevcut dönemsel toplamlardan (yeni sorgu gerektirmeden)
        # türetilir; ham teknik/imalat/diğer dakika kırılımı veya plan/fiili ayrı miktarları gibi daha
        # ayrıntılı alanlar bilinçli olarak kapsam dışı bırakıldı.
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
            direction = "OVER_PLAN" if avg_actual > 100 else ("UNDER_PLAN" if avg_actual < 100 else "ON_PLAN")
            item["plana_uyum"] = {
                "avg_attainment_pct": round(avg_actual, kpi.decimal_places),
                "direction": direction,
            }
        items.append(item)
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


@router.get("/{foreman_id}/contribution-summary")
def foreman_contribution_summary(
    foreman_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_user)
) -> dict:
    """Formen detay sayfasındaki kompakt Katkı ve İyileştirme Çalışmaları kartı için hafif özet.

    Yalnızca yayımlanmış çalışmalar dahil edilir. Ortak çalışmalarda maddi kazanç ve zaman
    tasarrufu, formen kendi tek başına ürettiği kazanç gibi gösterilmesin diye çalışmadaki
    formen sayısına eşit bölünerek (pay bulunmuyorsa otomatik eşit dağıtım) toplanır.
    """
    if db.get(Foreman, foreman_id) is None:
        raise HTTPException(404, "Formen bulunamadı.")

    rows = db.execute(
        select(ContributionWork, ContributionWorkForeman.role)
        .join(ContributionWorkForeman, ContributionWorkForeman.work_id == ContributionWork.id)
        .where(
            ContributionWorkForeman.foreman_id == foreman_id,
            ContributionWork.status == ContributionStatus.PUBLISHED,
        )
    ).all()

    empty = {
        "total_contributions": 0, "smed_count": 0, "led_contributions": 0,
        "verified_financial_gain": {}, "estimated_financial_gain": {},
        "total_time_saving_minutes": 0.0, "last_contribution_date": None,
    }
    if not rows:
        return empty

    work_ids = [work.id for work, _ in rows]
    participant_counts = dict(
        db.execute(
            select(ContributionWorkForeman.work_id, func.count())
            .where(ContributionWorkForeman.work_id.in_(work_ids))
            .group_by(ContributionWorkForeman.work_id)
        ).all()
    )

    smed_count = 0
    led_count = 0
    verified: dict[str, float] = {}
    estimated: dict[str, float] = {}
    total_time_saving = 0.0
    last_date: date | None = None

    for work, role in rows:
        share = 1 / participant_counts.get(work.id, 1)
        if work.work_type == ContributionWorkType.SMED:
            smed_count += 1
        if role == ContributionRole.LEAD:
            led_count += 1
        if work.verified_amount is not None and work.currency is not None:
            key = work.currency.value
            verified[key] = verified.get(key, 0.0) + float(work.verified_amount) * share
        if work.estimated_amount is not None and work.currency is not None:
            key = work.currency.value
            estimated[key] = estimated.get(key, 0.0) + float(work.estimated_amount) * share
        if work.monthly_total_saving_minutes is not None:
            total_time_saving += float(work.monthly_total_saving_minutes) * share
        work_date = work.work_date or (work.published_at.date() if work.published_at else None)
        if work_date and (last_date is None or work_date > last_date):
            last_date = work_date

    return {
        "total_contributions": len(rows),
        "smed_count": smed_count,
        "led_contributions": led_count,
        "verified_financial_gain": {k: round(v, 2) for k, v in verified.items()},
        "estimated_financial_gain": {k: round(v, 2) for k, v in estimated.items()},
        "total_time_saving_minutes": round(total_time_saving, 2),
        "last_contribution_date": last_date.isoformat() if last_date else None,
    }
