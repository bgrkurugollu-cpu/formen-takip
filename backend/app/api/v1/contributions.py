from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.turkish import turkish_sort_key
from app.db.session import get_db
from app.models.contribution import ContributionGain, ContributionWork, ContributionWorkForeman
from app.models.enums import (
    ContributionRole,
    ContributionStatus,
    ContributionWorkType,
    FinancialGainStatus,
    ImpactLevel,
)
from app.models.foreman import Foreman
from app.models.organization import Plant
from app.models.user import User
from app.schemas.common import PageParams, page_params, parse_uuid_list
from app.schemas.contribution import ContributionWorkCreate, ContributionWorkUpdate
from app.services import contribution_calc as calc
from app.services.audit import record_audit
from app.services.contribution_pdf import render_contribution_pdf

router = APIRouter(prefix="/contribution-works", tags=["contribution-works"])


def _num(value) -> float | None:
    """Postgres `Numeric` kolonlarından gelen `Decimal` değerleri JSON yanıtı için float'a çevirir."""
    return float(value) if value is not None else None

WORK_TYPE_LABELS = {
    ContributionWorkType.SMED: "SMED",
    ContributionWorkType.KAIZEN: "Kaizen",
    ContributionWorkType.PROBLEM_SOLVING: "Problem Çözme",
    ContributionWorkType.COST_REDUCTION: "Maliyet Azaltma",
    ContributionWorkType.TIME_SAVING: "Zaman Kazancı",
    ContributionWorkType.QUALITY_IMPROVEMENT: "Kalite İyileştirme",
    ContributionWorkType.SAFETY_IMPROVEMENT: "İş Güvenliği İyileştirmesi",
    ContributionWorkType.ENERGY_RESOURCE_SAVING: "Enerji veya Kaynak Tasarrufu",
    ContributionWorkType.PRODUCTION_EFFICIENCY: "Üretim Verimliliği",
    ContributionWorkType.DIGITALIZATION: "Dijitalleşme",
    ContributionWorkType.OTHER: "Diğer",
}


def _foreman_refs(db: Session, work_id: UUID) -> list[dict]:
    rows = db.execute(
        select(Foreman, ContributionWorkForeman.role)
        .join(ContributionWorkForeman, ContributionWorkForeman.foreman_id == Foreman.id)
        .where(ContributionWorkForeman.work_id == work_id)
        .order_by(Foreman.first_name)
    ).all()
    return [
        {"id": str(f.id), "name": f"{f.first_name} {f.last_name}", "employee_number": f.employee_number, "role": role.value}
        for f, role in rows
    ]


def _plant_ref(db: Session, plant_id: UUID | None) -> dict | None:
    if plant_id is None:
        return None
    plant = db.get(Plant, plant_id)
    if plant is None:
        return None
    return {
        "id": str(plant.id), "name": plant.name, "code": plant.code,
        "factory_id": str(plant.factory_id), "factory_name": plant.factory.name, "factory_code": plant.factory.code,
    }


def _gain_to_dict(g: ContributionGain) -> dict:
    return {
        "id": str(g.id),
        "gain_type": g.gain_type.value,
        "gain_type_label": calc.gain_type_label(g.gain_type),
        "gain_type_other_note": g.gain_type_other_note,
        "previous_value": _num(g.previous_value),
        "next_value": _num(g.next_value),
        "change_amount": _num(g.change_amount),
        "change_percent": _num(g.change_percent),
        "is_improvement": calc.is_improvement(g.gain_type, g.change_amount),
        "unit": g.unit,
        "measurement_period": g.measurement_period,
        "description": g.description,
    }


def _before_after(work: ContributionWork) -> dict | None:
    if work.previous_duration is None or work.new_duration is None:
        return None
    unit_label = {"second": "saniye", "minute": "dakika", "hour": "saat"}.get(
        work.duration_unit.value if work.duration_unit else "minute", "dakika"
    )
    previous_duration, new_duration = float(work.previous_duration), float(work.new_duration)
    saving = calc.compute_time_saving(previous_duration, new_duration)
    return {
        "metric_label": "Süre Karşılaştırması",
        "before": f"{previous_duration} {unit_label}",
        "after": f"{new_duration} {unit_label}",
        "change": f"-{saving} {unit_label}" if saving is not None else "İyileşme yok",
        "is_improvement": saving is not None,
    }


def _to_dict(db: Session, work: ContributionWork) -> dict:
    gains = list(db.scalars(select(ContributionGain).where(ContributionGain.work_id == work.id)))
    creator = db.get(User, work.created_by_user_id)

    return {
        "id": str(work.id),
        "title": work.title,
        "status": work.status.value,
        "work_type": work.work_type.value if work.work_type else None,
        "work_type_label": WORK_TYPE_LABELS.get(work.work_type) if work.work_type else None,
        "work_type_other_note": work.work_type_other_note,
        "summary": work.summary,
        "detailed_description": work.detailed_description,
        "problem_description": work.problem_description,
        "solution_description": work.solution_description,
        "result_description": work.result_description,
        "foremen": _foreman_refs(db, work.id),
        "plant": _plant_ref(db, work.plant_id),
        "work_date": work.work_date.isoformat() if work.work_date else None,
        "work_date_end": work.work_date_end.isoformat() if work.work_date_end else None,
        "impact_level": work.impact_level.value if work.impact_level else None,
        "created_by": creator.full_name if creator else None,
        "created_by_user_id": str(work.created_by_user_id),
        "published_at": work.published_at.isoformat() if work.published_at else None,
        "is_standardized": work.is_standardized,
        "is_applicable_other_plants": work.is_applicable_other_plants,
        "is_permanent_solution": work.is_permanent_solution,
        "work_instruction_updated": work.work_instruction_updated,
        "financial_gain_status": work.financial_gain_status.value,
        "estimated_amount": _num(work.estimated_amount),
        "verified_amount": _num(work.verified_amount),
        "currency": work.currency.value if work.currency else None,
        "gain_period": work.gain_period.value if work.gain_period else None,
        "calculation_method": work.calculation_method,
        "is_gain_verified": work.is_gain_verified,
        "verified_by_department": work.verified_by_department.value if work.verified_by_department else None,
        "verified_by_department_other_note": work.verified_by_department_other_note,
        "verification_date": work.verification_date.isoformat() if work.verification_date else None,
        "verification_note": work.verification_note,
        "previous_duration": _num(work.previous_duration),
        "new_duration": _num(work.new_duration),
        "duration_unit": work.duration_unit.value if work.duration_unit else None,
        "per_occurrence_saving": _num(work.per_occurrence_saving),
        "repeat_period": work.repeat_period.value if work.repeat_period else None,
        "repeat_count": _num(work.repeat_count),
        "monthly_total_saving_minutes": _num(work.monthly_total_saving_minutes),
        "gains": [_gain_to_dict(g) for g in gains],
        "highlighted_gain_mode": work.highlighted_gain_mode.value,
        "highlighted_gain_ref": work.highlighted_gain_ref,
        "highlighted_gain": calc.resolve_highlighted_gain(work, gains),
        "before_after": _before_after(work),
        "badges": calc.resolve_badges(work),
        "created_at": work.created_at.isoformat(),
        "updated_at": work.updated_at.isoformat(),
    }


def _publish_check_data(work: ContributionWork, foreman_ids: list[UUID]) -> dict:
    return {
        "title": work.title,
        "foreman_ids": foreman_ids,
        "plant_id": work.plant_id,
        "work_date": work.work_date,
        "work_date_end": work.work_date_end,
        "work_type": work.work_type,
        "work_type_other_note": work.work_type_other_note,
        "summary": work.summary,
        "problem_description": work.problem_description,
        "solution_description": work.solution_description,
    }


def _apply_derived_fields(work: ContributionWork, overridden_fields: set[str]) -> None:
    """Süre kazancı alanlarını yeniden hesaplar; kullanıcı bu istekte açıkça bir değer
    göndermişse (manuel düzeltme) o alana dokunmaz."""
    if "per_occurrence_saving" not in overridden_fields:
        work.per_occurrence_saving = calc.compute_time_saving(work.previous_duration, work.new_duration)
    if "monthly_total_saving_minutes" not in overridden_fields:
        per_occurrence_minutes = calc.duration_to_minutes(work.per_occurrence_saving, work.duration_unit)
        work.monthly_total_saving_minutes = calc.compute_monthly_total(
            per_occurrence_minutes, work.repeat_period, work.repeat_count
        )


def _sync_foremen(db: Session, work_id: UUID, foreman_ids: list[UUID] | None) -> None:
    if foreman_ids is None:
        return
    db.execute(delete(ContributionWorkForeman).where(ContributionWorkForeman.work_id == work_id))
    unique_ids = list(dict.fromkeys(foreman_ids))
    # Tek formenli çalışmada o formen tek başına sorumlu olduğundan LEAD sayılır; ortak
    # çalışmalarda rol ataması şimdilik formdan alınmadığından tümü CONTRIBUTOR kalır.
    solo_role = ContributionRole.LEAD if len(unique_ids) == 1 else ContributionRole.CONTRIBUTOR
    for fid in unique_ids:
        db.add(ContributionWorkForeman(work_id=work_id, foreman_id=fid, role=solo_role))


def _sync_gains(db: Session, work_id: UUID, gains_input: list | None) -> None:
    if gains_input is None:
        return
    db.execute(delete(ContributionGain).where(ContributionGain.work_id == work_id))
    for g in gains_input:
        amount, percent = calc.compute_change(g.previous_value, g.next_value)
        db.add(
            ContributionGain(
                work_id=work_id, gain_type=g.gain_type, gain_type_other_note=g.gain_type_other_note,
                previous_value=g.previous_value, next_value=g.next_value,
                change_amount=amount, change_percent=percent,
                unit=g.unit, measurement_period=g.measurement_period, description=g.description,
            )
        )


def _filtered_query(
    date_from: date | None,
    date_to: date | None,
    plant_ids: str | None,
    factory_ids: str | None,
    foreman_ids: str | None,
    work_type: ContributionWorkType | None,
    status_filter: ContributionStatus | None,
    impact_level: ImpactLevel | None,
    financial_gain_status: FinancialGainStatus | None,
    search: str | None,
):
    query = select(ContributionWork)

    plant_id_list = parse_uuid_list(plant_ids)
    factory_id_list = parse_uuid_list(factory_ids)
    foreman_id_list = parse_uuid_list(foreman_ids)

    if date_from:
        query = query.where(or_(ContributionWork.work_date >= date_from, ContributionWork.work_date.is_(None)))
    if date_to:
        query = query.where(or_(ContributionWork.work_date <= date_to, ContributionWork.work_date.is_(None)))
    if plant_id_list:
        query = query.where(ContributionWork.plant_id.in_(plant_id_list))
    if factory_id_list:
        query = query.where(ContributionWork.plant_id.in_(select(Plant.id).where(Plant.factory_id.in_(factory_id_list))))
    if foreman_id_list:
        query = query.where(
            ContributionWork.id.in_(
                select(ContributionWorkForeman.work_id).where(ContributionWorkForeman.foreman_id.in_(foreman_id_list))
            )
        )
    if work_type:
        query = query.where(ContributionWork.work_type == work_type)
    if status_filter:
        query = query.where(ContributionWork.status == status_filter)
    if impact_level:
        query = query.where(ContributionWork.impact_level == impact_level)
    if financial_gain_status:
        query = query.where(ContributionWork.financial_gain_status == financial_gain_status)
    if search:
        like = f"%{search}%"
        foreman_match = select(ContributionWorkForeman.work_id).join(
            Foreman, Foreman.id == ContributionWorkForeman.foreman_id
        ).where(func.concat(Foreman.first_name, " ", Foreman.last_name).ilike(like))
        query = query.where(
            or_(ContributionWork.title.ilike(like), ContributionWork.summary.ilike(like), ContributionWork.id.in_(foreman_match))
        )

    return query


def _sort_key_fn(db: Session, works: list[ContributionWork], sort_by: str):
    work_ids = [w.id for w in works]

    foreman_names: dict[UUID, list[str]] = {}
    gains_by_work: dict[UUID, list[ContributionGain]] = {}
    if sort_by == "foreman" and work_ids:
        for work_id, first, last in db.execute(
            select(ContributionWorkForeman.work_id, Foreman.first_name, Foreman.last_name)
            .join(Foreman, Foreman.id == ContributionWorkForeman.foreman_id)
            .where(ContributionWorkForeman.work_id.in_(work_ids))
        ).all():
            foreman_names.setdefault(work_id, []).append(f"{first} {last}")
    if sort_by == "gain" and work_ids:
        for g in db.scalars(select(ContributionGain).where(ContributionGain.work_id.in_(work_ids))):
            gains_by_work.setdefault(g.work_id, []).append(g)

    plants_by_id = {p.id: p for p in db.scalars(select(Plant))} if sort_by == "plant" else {}

    def key(work: ContributionWork):
        if sort_by == "title":
            return turkish_sort_key(work.title)
        if sort_by == "type":
            label = WORK_TYPE_LABELS.get(work.work_type, "") if work.work_type else ""
            return turkish_sort_key(label)
        if sort_by == "foreman":
            names = sorted(foreman_names.get(work.id, []), key=turkish_sort_key)
            return turkish_sort_key(names[0]) if names else ()
        if sort_by == "plant":
            plant = plants_by_id.get(work.plant_id) if work.plant_id else None
            return plant.sequence_number if plant else -1
        if sort_by == "gain":
            gain = calc.resolve_highlighted_gain(work, gains_by_work.get(work.id, []))
            return gain["value"] if gain else float("-inf")
        if sort_by == "status":
            return work.status.value
        return work.work_date or date.min

    return key


@router.get("")
def list_contribution_works(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    plant_ids: str | None = Query(None, description="Virgülle ayrılmış tesis ID listesi"),
    factory_ids: str | None = Query(None, description="Virgülle ayrılmış fabrika ID listesi"),
    foreman_ids: str | None = Query(None, description="Virgülle ayrılmış formen ID listesi"),
    work_type: ContributionWorkType | None = Query(None),
    status_filter: ContributionStatus | None = Query(None, alias="status"),
    impact_level: ImpactLevel | None = Query(None),
    financial_gain_status: FinancialGainStatus | None = Query(None),
    search: str | None = Query(None),
    sort_by: str = Query("date", pattern="^(title|type|foreman|plant|date|gain|status)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    page: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    query = _filtered_query(
        date_from, date_to, plant_ids, factory_ids, foreman_ids,
        work_type, status_filter, impact_level, financial_gain_status, search,
    )

    if sort_by in ("title", "type", "foreman", "gain"):
        # Bu dört sıralama SQL'e taşınamaz: title/type/foreman Türkçe'ye özel bir harf sırası
        # kullanıyor (`turkish_sort_key` — Postgres'in varsayılan collation'ıyla BİREBİR
        # eşleşmiyor, ör. ç/ğ/ı/ö/ş/ü sırası), gain ise çok dallı bir iş kuralından
        # (`resolve_highlighted_gain`: manuel referans → doğrulanmış tutar → tahmini tutar →
        # zaman kazancı) doğuyor. Performans için sessizce yanlış bir sıra üretmektense burada
        # hâlâ bellekte (tüm eşleşen satırlar çekilip) sıralanır.
        all_works = list(db.scalars(query))
        all_works.sort(key=_sort_key_fn(db, all_works, sort_by), reverse=sort_dir == "desc")
        total = len(all_works)
        start = (page.page - 1) * page.page_size
        page_works = all_works[start : start + page.page_size]
    else:
        total = db.scalar(select(func.count()).select_from(query.subquery()))

        if sort_by == "plant":
            query = query.outerjoin(Plant, Plant.id == ContributionWork.plant_id)
            sort_col = func.coalesce(Plant.sequence_number, -1)
            order_expr = sort_col.desc() if sort_dir == "desc" else sort_col.asc()
        elif sort_by == "status":
            order_expr = ContributionWork.status.desc() if sort_dir == "desc" else ContributionWork.status.asc()
        else:  # "date" (varsayılan) — eski Python anahtarı (work_date or date.min) ile eşleşsin
            # diye NULL'lar en küçük değermiş gibi davranır: ASC'de en başta, DESC'te en sonda.
            order_expr = (
                ContributionWork.work_date.desc().nulls_last()
                if sort_dir == "desc" else ContributionWork.work_date.asc().nulls_first()
            )

        # `id` ikincil sıralama anahtarı: birincil alan eşit olan satırlarda tek başına sıralama,
        # sayfa 1/sayfa 2 ayrı SQL sorguları olduğundan tutarsız sıra üretip bir satırı iki
        # sayfada birden gösterebilir ya da hiç göstermeyebilir.
        query = (
            query.order_by(order_expr, ContributionWork.id)
            .offset((page.page - 1) * page.page_size).limit(page.page_size)
        )
        page_works = list(db.scalars(query))

    return {
        "items": [_to_dict(db, w) for w in page_works],
        "total": total or 0, "page": page.page, "page_size": page.page_size,
    }


@router.get("/summary")
def contribution_summary(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    plant_ids: str | None = Query(None, description="Virgülle ayrılmış tesis ID listesi"),
    factory_ids: str | None = Query(None, description="Virgülle ayrılmış fabrika ID listesi"),
    foreman_ids: str | None = Query(None, description="Virgülle ayrılmış formen ID listesi"),
    work_type: ContributionWorkType | None = Query(None),
    status_filter: ContributionStatus | None = Query(None, alias="status"),
    impact_level: ImpactLevel | None = Query(None),
    financial_gain_status: FinancialGainStatus | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    query = _filtered_query(
        date_from, date_to, plant_ids, factory_ids, foreman_ids,
        work_type, status_filter, impact_level, financial_gain_status, search,
    )

    works = list(db.scalars(query))
    total = len(works)
    now = datetime.now(timezone.utc)
    this_month = sum(1 for w in works if w.created_at.year == now.year and w.created_at.month == now.month)

    total_estimated = sum(w.estimated_amount for w in works if w.estimated_amount is not None)
    total_verified = sum(w.verified_amount for w in works if w.verified_amount is not None)
    total_monthly_time_saving = sum(w.monthly_total_saving_minutes for w in works if w.monthly_total_saving_minutes is not None)

    by_plant: dict[str, int] = {}
    plants_by_id = {p.id: p for p in db.scalars(select(Plant))}
    for w in works:
        if w.plant_id is None:
            continue
        plant = plants_by_id.get(w.plant_id)
        key = plant.name if plant else str(w.plant_id)
        by_plant[key] = by_plant.get(key, 0) + 1

    by_type: dict[str, int] = {}
    for w in works:
        if w.work_type is None:
            continue
        label = WORK_TYPE_LABELS[w.work_type]
        by_type[label] = by_type.get(label, 0) + 1

    foreman_counts: dict[UUID, int] = {}
    work_ids = [w.id for w in works]
    if work_ids:
        for row in db.scalars(select(ContributionWorkForeman).where(ContributionWorkForeman.work_id.in_(work_ids))):
            foreman_counts[row.foreman_id] = foreman_counts.get(row.foreman_id, 0) + 1
    foremen_by_id = {f.id: f for f in db.scalars(select(Foreman))}
    top_foremen = sorted(foreman_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]

    applicable_other_plants = sum(1 for w in works if w.is_applicable_other_plants)
    standardized_ratio = round((sum(1 for w in works if w.is_standardized) / total) * 100, 1) if total else 0.0

    return {
        "total_works": total,
        "added_this_month": this_month,
        "total_estimated_gain": round(total_estimated, 2),
        "total_verified_gain": round(total_verified, 2),
        "total_monthly_time_saving_minutes": round(total_monthly_time_saving, 2),
        "by_plant": [{"name": k, "count": v} for k, v in sorted(by_plant.items(), key=lambda kv: kv[1], reverse=True)],
        "by_work_type": [{"label": k, "count": v} for k, v in sorted(by_type.items(), key=lambda kv: kv[1], reverse=True)],
        "top_foremen": [
            {
                "id": str(fid), "name": f"{foremen_by_id[fid].first_name} {foremen_by_id[fid].last_name}" if fid in foremen_by_id else "-",
                "count": count,
            }
            for fid, count in top_foremen
        ],
        "applicable_other_plants_count": applicable_other_plants,
        "standardized_ratio": standardized_ratio,
    }


@router.post("", status_code=201)
def create_contribution_work(
    payload: ContributionWorkCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if payload.status == ContributionStatus.PUBLISHED:
        errors = calc.validate_for_publish(payload.model_dump())
        if errors:
            raise HTTPException(422, {"message": "Yayımlamak için zorunlu alanlar eksik.", "errors": errors})

    work = ContributionWork(
        title=payload.title, status=payload.status,
        work_type=payload.work_type, work_type_other_note=payload.work_type_other_note,
        summary=payload.summary, detailed_description=payload.detailed_description,
        problem_description=payload.problem_description, solution_description=payload.solution_description,
        result_description=payload.result_description,
        plant_id=payload.plant_id, work_date=payload.work_date, work_date_end=payload.work_date_end,
        impact_level=payload.impact_level, created_by_user_id=current_user.id,
        is_standardized=payload.is_standardized, is_applicable_other_plants=payload.is_applicable_other_plants,
        is_permanent_solution=payload.is_permanent_solution, work_instruction_updated=payload.work_instruction_updated,
        financial_gain_status=payload.financial_gain_status,
        estimated_amount=payload.estimated_amount, verified_amount=payload.verified_amount,
        currency=payload.currency, gain_period=payload.gain_period, calculation_method=payload.calculation_method,
        is_gain_verified=payload.is_gain_verified, verified_by_department=payload.verified_by_department,
        verified_by_department_other_note=payload.verified_by_department_other_note,
        verification_date=payload.verification_date, verification_note=payload.verification_note,
        previous_duration=payload.previous_duration, new_duration=payload.new_duration,
        duration_unit=payload.duration_unit, repeat_period=payload.repeat_period, repeat_count=payload.repeat_count,
        per_occurrence_saving=payload.per_occurrence_saving, monthly_total_saving_minutes=payload.monthly_total_saving_minutes,
        highlighted_gain_mode=payload.highlighted_gain_mode, highlighted_gain_ref=payload.highlighted_gain_ref,
        published_at=datetime.now(timezone.utc) if payload.status == ContributionStatus.PUBLISHED else None,
    )
    overridden = {
        f for f in ("per_occurrence_saving", "monthly_total_saving_minutes")
        if f in payload.model_fields_set and getattr(payload, f) is not None
    }
    _apply_derived_fields(work, overridden)
    db.add(work)
    db.flush()

    _sync_foremen(db, work.id, payload.foreman_ids)
    _sync_gains(db, work.id, payload.gains)

    db.commit()
    db.refresh(work)

    record_audit(
        db, current_user.id, "contribution_work_created", entity="contribution_work",
        new_value=payload.title, ip_address=request.client.host if request.client else None,
    )
    return _to_dict(db, work)


@router.get("/{work_id}")
def get_contribution_work(work_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_user)) -> dict:
    work = db.get(ContributionWork, work_id)
    if work is None:
        raise HTTPException(404, "Çalışma kaydı bulunamadı.")
    return _to_dict(db, work)


@router.patch("/{work_id}")
def update_contribution_work(
    work_id: UUID,
    payload: ContributionWorkUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    work = db.get(ContributionWork, work_id)
    if work is None:
        raise HTTPException(404, "Çalışma kaydı bulunamadı.")

    updates = payload.model_dump(exclude_unset=True, exclude={"foreman_ids", "gains"})

    is_publishing = updates.get("status") == ContributionStatus.PUBLISHED and work.status != ContributionStatus.PUBLISHED
    if updates.get("status") == ContributionStatus.PUBLISHED:
        current_foreman_ids = (
            payload.foreman_ids if payload.foreman_ids is not None
            else [row.foreman_id for row in db.scalars(select(ContributionWorkForeman).where(ContributionWorkForeman.work_id == work_id))]
        )
        relevant_keys = set(calc.REQUIRED_FOR_PUBLISH_MESSAGES) | {"work_date_end"}
        merged = {**_publish_check_data(work, current_foreman_ids), **{k: v for k, v in updates.items() if k in relevant_keys}}
        merged["foreman_ids"] = current_foreman_ids
        errors = calc.validate_for_publish(merged)
        if errors:
            raise HTTPException(422, {"message": "Yayımlamak için zorunlu alanlar eksik.", "errors": errors})

    changes: list[str] = []
    for field, new_value in updates.items():
        old_value = getattr(work, field)
        old_str = old_value.value if hasattr(old_value, "value") else str(old_value)
        new_str = new_value.value if hasattr(new_value, "value") else str(new_value)
        if old_str != new_str:
            changes.append(f"{field}: {old_str} -> {new_str}")
        setattr(work, field, new_value)

    if is_publishing:
        work.published_at = datetime.now(timezone.utc)

    _sync_foremen(db, work.id, payload.foreman_ids)
    _sync_gains(db, work.id, payload.gains)
    overridden = {
        f for f in ("per_occurrence_saving", "monthly_total_saving_minutes")
        if f in payload.model_fields_set and getattr(payload, f) is not None
    }
    _apply_derived_fields(work, overridden)

    db.commit()
    db.refresh(work)

    if changes or payload.foreman_ids is not None or payload.gains is not None:
        record_audit(
            db, current_user.id, "contribution_work_updated", entity="contribution_work",
            old_value=None, new_value="; ".join(changes) or "foremen/gains updated",
            ip_address=request.client.host if request.client else None,
        )
    return _to_dict(db, work)


@router.delete("/{work_id}", status_code=204)
def delete_contribution_work(
    work_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    work = db.get(ContributionWork, work_id)
    if work is None:
        raise HTTPException(404, "Çalışma kaydı bulunamadı.")

    title = work.title
    db.delete(work)
    db.commit()

    record_audit(
        db, current_user.id, "contribution_work_deleted", entity="contribution_work",
        old_value=title, ip_address=request.client.host if request.client else None,
    )
    return Response(status_code=204)


@router.get("/{work_id}/pdf")
def download_contribution_work_pdf(
    work_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Response:
    work = db.get(ContributionWork, work_id)
    if work is None:
        raise HTTPException(404, "Çalışma kaydı bulunamadı.")

    pdf_bytes = render_contribution_pdf(_to_dict(db, work))
    file_name = f"katki-calismasi_{work.id}.pdf"
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
