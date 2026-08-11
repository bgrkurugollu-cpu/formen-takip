from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from statistics import pstdev
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.foreman import Chief, Foreman, ForemanAssignment
from app.models.foreman_report import ForemanMonthlyReport
from app.models.kpi import Kpi
from app.models.organization import Factory, Plant
from app.schemas.common import Filters
from app.services import analytics
from app.services.kpi_engine import PerformanceLevel, resolve_performance_level
from app.services.level_lookup import get_performance_levels, level_to_dict
from app.services.shift_analysis import month_label

INSUFFICIENT_DATA_MESSAGE = "Bu dönem için değerlendirme oluşturmak adına yeterli veri bulunmamaktadır."

# Bölüm 6/7/8/10'daki kategorizasyon, yeni bir eşik icat etmez — doğrudan mevcut
# `performance_level_rules` seed adlarını kullanır (aynı desen `reporting.py::_foreman_performance`'ta
# `level.name == "Kritik"` karşılaştırmasıyla zaten kullanılıyor).
STRONG_LEVEL_NAMES = {"İyi", "Çok İyi", "Mükemmel"}
IMPROVEMENT_LEVEL_NAMES = {"Geliştirilmeli", "Kritik"}
CRITICAL_LEVEL_NAMES = {"Kritik"}
TOP_LEVEL_NAMES = {"Çok İyi", "Mükemmel"}

_EPSILON_ABS = 1e-4
_EPSILON_REL = 0.001

# Aylık trend şekli sınıflandırması için basit, dokümante edilmiş sezgisel eşikler —
# `shift_analysis.py::ShiftAnomalyThresholds` ile aynı ruhta: akademik bir istatistik
# modeli değil, yönetime okunabilir bir özet sunmak için sabit bir eşik.
_TREND_FLAT_STDEV = 3.0
_TREND_FLAT_DIFF = 3.0
_TREND_MIN_RELIABLE_WEEKS = 3


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def _previous_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def is_month_completed(year: int, month: int) -> bool:
    _, period_end = _month_bounds(year, month)
    return period_end < date.today()


def _compare_to_reference(
    actual: float | None, reference: float | None, success_direction_higher: bool
) -> dict | None:
    """Bir (gerçekleşen, referans) çiftini yön farkındalıklı olarak karşılaştırır — referans,
    bağlama göre kişisel/tesis hedefi veya fabrika ortalaması olabilir. `is_favorable`,
    KPI'nın yönüne (`success_direction_higher`) göre gerçekleşenin referanstan İYİ olup
    olmadığını taşır; ham `status` ise yalnızca sayısal büyüklük ilişkisini anlatır."""
    if actual is None or reference is None:
        return None
    diff = actual - reference
    tolerance = max(_EPSILON_ABS, abs(reference) * _EPSILON_REL)
    if abs(diff) <= tolerance:
        status = "at"
        is_favorable = True
    else:
        status = "above" if diff > 0 else "below"
        is_favorable = (status == "above") == success_direction_higher
    diff_pct = (diff / reference * 100.0) if reference else None
    return {
        "value": round(reference, 4),
        "diff": round(diff, 4),
        "diff_pct": round(diff_pct, 2) if diff_pct is not None else None,
        "status": status,
        "is_favorable": is_favorable,
    }


def _classify_trend_shape(weekly_scores: list[float]) -> str | None:
    if len(weekly_scores) < _TREND_MIN_RELIABLE_WEEKS:
        return None
    half = len(weekly_scores) // 2
    first_half_avg = sum(weekly_scores[:half]) / half
    second_half_avg = sum(weekly_scores[-half:]) / half
    diff = second_half_avg - first_half_avg
    stdev = pstdev(weekly_scores)
    if stdev < _TREND_FLAT_STDEV and abs(diff) < _TREND_FLAT_DIFF:
        return "stabil"
    if diff > _TREND_FLAT_DIFF:
        return "iyileşme"
    if diff < -_TREND_FLAT_DIFF:
        return "kötüleşme"
    return "dalgalı"


_TREND_TEXT = {
    "iyileşme": "Genel performansınız ay boyunca istikrarlı bir iyileşme göstermiştir.",
    "kötüleşme": "Genel performansınızda ay içerisinde bir gerileme gözlenmektedir.",
    "stabil": "Genel performansınız ay boyunca istikrarlı bir şekilde seyretmiştir.",
    "dalgalı": "Genel performansınız ay içerisinde dalgalı bir seyir izlemiştir.",
}


def _active_assignments_as_of(db: Session, foreman_id: UUID, as_of: date) -> list[ForemanAssignment]:
    return list(
        db.scalars(
            select(ForemanAssignment)
            .where(ForemanAssignment.foreman_id == foreman_id, ForemanAssignment.start_date <= as_of)
            .where((ForemanAssignment.end_date.is_(None)) | (ForemanAssignment.end_date >= as_of))
        )
    )


def _kpi_entry(
    kpi: Kpi,
    row: dict | None,
    factory_rows_by_kpi: dict[UUID, dict],
    levels: list[PerformanceLevel],
) -> dict:
    avg_actual = float(row["avg_actual"]) if row and row["avg_actual"] is not None else None
    avg_target = float(row["avg_target"]) if row and row["avg_target"] is not None else None
    capped_score = float(row["avg_capped_score"]) if row else 0.0
    record_count = row["record_count"] if row else 0
    factory_row = factory_rows_by_kpi.get(kpi.id)
    factory_actual = float(factory_row["avg_actual"]) if factory_row and factory_row["avg_actual"] is not None else None

    level = resolve_performance_level(capped_score, levels) if row else None
    dp = kpi.decimal_places
    return {
        "kpi_id": str(kpi.id),
        "code": kpi.code,
        "name": kpi.name,
        "unit": kpi.unit,
        "weight": float(kpi.weight),
        "success_direction_higher": kpi.success_direction_higher,
        "has_data": record_count > 0,
        "record_count": record_count,
        "actual": round(avg_actual, dp) if avg_actual is not None else None,
        "score": round(capped_score, 2) if row else None,
        "level": level_to_dict(level) if level else None,
        "vs_personal_target": _compare_to_reference(avg_actual, avg_target, kpi.success_direction_higher),
        "vs_factory_average": _compare_to_reference(avg_actual, factory_actual, kpi.success_direction_higher),
    }


def _build_summary_text(period_label: str, total_with_data: int, strong: list[dict], improve: list[dict]) -> str:
    if total_with_data == 0:
        return f"{period_label} için değerlendirilebilir KPI verisi bulunmamaktadır."
    parts = [f"{period_label} ayında değerlendirilen {total_with_data} KPI'dan {len(strong)}'inde hedef seviyesinde veya üzerinde performans gösterdiniz."]
    if strong:
        names = ", ".join(k["name"] for k in strong)
        parts.append(f"{names} alanlarında güçlü bir performans sergilediniz.")
    if improve:
        names = ", ".join(k["name"] for k in improve)
        parts.append(f"{names} alanında/alanlarında ise gelişim fırsatı bulunmaktadır.")
    return " ".join(parts)


def _investigation_hint(kpi_code: str) -> str:
    if kpi_code == "INKITA":
        return "Duruş nedenlerinin detaylı incelenmesi önerilir."
    return "Performansı etkileyen faktörlerin ayrıntılı incelenmesi önerilir."


def _build_closing_text(
    period_label: str, overall_level: PerformanceLevel, strong: list[dict], improve: list[dict], critical: list[dict]
) -> str:
    sentences = [f"{period_label} ayında genel performansınız \"{overall_level.name}\" seviyesinde gerçekleşmiştir."]
    if strong:
        names = ", ".join(k["name"] for k in strong)
        sentences.append(f"Özellikle {names} KPI'larında güçlü sonuçlar elde ettiniz.")
    if improve:
        names = ", ".join(k["name"] for k in improve)
        sentences.append(f"{names} KPI'larında ise hedef seviyesinden uzaklaşma görülmektedir.")
    if critical:
        sentences.append("Önümüzdeki ay bu alanlara odaklanmanız ve yöneticinizle birlikte değerlendirmeniz önerilir.")
    sentences.append("Genel olarak performansınızı sürdürmeniz ve geliştirmeniz önemlidir.")
    return " ".join(sentences)


def _build_report_data(db: Session, foreman: Foreman, year: int, month: int) -> dict:
    date_from, date_to = _month_bounds(year, month)
    period_label = month_label(date_to)
    generated_at = datetime.now(timezone.utc)

    header = {
        "foreman": {
            "id": str(foreman.id),
            "employee_number": foreman.employee_number,
            "full_name": f"{foreman.first_name} {foreman.last_name}",
            "hire_date": foreman.hire_date.isoformat(),
        },
        "period": {
            "year": year, "month": month, "label": period_label,
            "date_from": date_from.isoformat(), "date_to": date_to.isoformat(),
        },
        "generated_at": generated_at.isoformat(),
    }

    assignments = _active_assignments_as_of(db, foreman.id, date_to)
    if not assignments:
        return {
            **header,
            "org": None,
            "insufficient_data": True,
            "insufficient_data_reason": INSUFFICIENT_DATA_MESSAGE,
            "overall": None,
        }

    plants_by_id = {p.id: p for p in db.scalars(select(Plant).where(Plant.id.in_({a.plant_id for a in assignments})))}
    chief = db.get(Chief, assignments[0].chief_id)
    factory_id = next(iter(plants_by_id.values())).factory_id
    factory = db.get(Factory, factory_id)
    org = {
        "factory_name": factory.name if factory else None,
        "plants": [{"id": str(p.id), "name": p.name} for p in sorted(plants_by_id.values(), key=lambda p: p.sequence_number)],
        "chief_name": f"{chief.first_name} {chief.last_name}" if chief else None,
    }

    filters = Filters(date_from=date_from, date_to=date_to)
    overall_scores = {s.key: s for s in analytics.foreman_scores(db, filters)}
    overall = overall_scores.get(foreman.id)

    if overall is None or not overall.is_reliable:
        return {
            **header,
            "org": org,
            "insufficient_data": True,
            "insufficient_data_reason": INSUFFICIENT_DATA_MESSAGE,
            "overall": None,
        }

    levels = get_performance_levels(db)
    kpis_by_id = {k.id: k for k in db.scalars(select(Kpi).where(Kpi.is_active.is_(True)))}
    personal_rows = {r["kpi_id"]: r for r in analytics.foreman_kpi_breakdown(db, filters, foreman.id)}

    factory_filters = Filters(date_from=date_from, date_to=date_to, factory_ids=[factory_id])
    factory_rows = {r["kpi_id"]: r for r in analytics.kpi_breakdown(db, factory_filters)}

    kpi_entries = [
        _kpi_entry(kpi, personal_rows.get(kpi.id), factory_rows, levels)
        for kpi in sorted(kpis_by_id.values(), key=lambda k: k.display_order)
    ]
    entries_with_data = [e for e in kpi_entries if e["has_data"]]

    strong = [e for e in entries_with_data if e["level"] and e["level"]["name"] in STRONG_LEVEL_NAMES]
    improve = [e for e in entries_with_data if e["level"] and e["level"]["name"] in IMPROVEMENT_LEVEL_NAMES]
    critical = [e for e in entries_with_data if e["level"] and e["level"]["name"] in CRITICAL_LEVEL_NAMES]

    overall_level = resolve_performance_level(overall.total_score, levels)
    show_congrats = overall_level.name in TOP_LEVEL_NAMES
    congrats_kpis = [e for e in strong if e["level"]["name"] in TOP_LEVEL_NAMES] if show_congrats else []

    weekly_points = analytics.trend(db, filters, granularity="week", foreman_id=foreman.id)
    reliable_weekly_scores = [p.total_score for p in weekly_points if p.is_reliable]
    trend_shape = _classify_trend_shape(reliable_weekly_scores)

    prev_year, prev_month = _previous_month(year, month)
    prev_from, prev_to = _month_bounds(prev_year, prev_month)
    prev_filters = Filters(date_from=prev_from, date_to=prev_to)
    prev_overall = {s.key: s for s in analytics.foreman_scores(db, prev_filters)}.get(foreman.id)
    previous_month: dict = {"available": False}
    if prev_overall is not None and prev_overall.is_reliable:
        prev_rows = {r["kpi_id"]: r for r in analytics.foreman_kpi_breakdown(db, prev_filters, foreman.id)}
        per_kpi = []
        for kpi in kpis_by_id.values():
            cur_row = personal_rows.get(kpi.id)
            prev_row = prev_rows.get(kpi.id)
            if not cur_row or not prev_row or cur_row["avg_actual"] is None or prev_row["avg_actual"] is None:
                continue
            diff = float(cur_row["avg_actual"]) - float(prev_row["avg_actual"])
            is_improvement = (diff > 0) == kpi.success_direction_higher if abs(diff) > _EPSILON_ABS else True
            per_kpi.append({
                "code": kpi.code, "name": kpi.name,
                "diff": round(diff, kpi.decimal_places),
                "is_improvement": is_improvement,
            })
        previous_month = {
            "available": True,
            "label": month_label(prev_to),
            "overall_diff": round(overall.total_score - prev_overall.total_score, 2),
            "per_kpi": per_kpi,
        }

    return {
        **header,
        "org": org,
        "insufficient_data": False,
        "overall": {
            "score": round(overall.total_score, 2),
            "level": level_to_dict(overall_level),
            "kpi_count": {
                "total": len(entries_with_data),
                "above_or_at_target": len(strong),
                "below_target": len(improve),
                "critical": len(critical),
            },
        },
        "summary_text": _build_summary_text(period_label, len(entries_with_data), strong, improve),
        "closing_text": _build_closing_text(period_label, overall_level, strong, improve, critical),
        "kpis": kpi_entries,
        "strengths": [
            {"kpi_code": k["code"], "name": k["name"],
             "text": f"Bu ay {k['name']} alanında hedef seviyesinde veya üzerinde performans gösterdiniz."}
            for k in strong
        ],
        "improvements": [
            {"kpi_code": k["code"], "name": k["name"],
             "text": (f"Bu ay {k['name']} performansınız hedef seviyesinin altında kaldı. "
                      f"{_investigation_hint(k['code'])}")}
            for k in improve
        ],
        "critical_attention": [
            {"kpi_code": k["code"], "name": k["name"],
             "text": (f"{k['name']} KPI'ında bu ay hedef seviyesinin belirgin şekilde altında bir performans "
                      "görülmektedir. Performansı etkileyen nedenlerin değerlendirilmesi için yöneticinizle "
                      "birlikte bu KPI'ı incelemeniz önerilir."),
             "manager_prompt": "Bu konuyu yöneticiniz ile değerlendirmeniz önerilir."}
            for k in critical
        ],
        "congratulations": {
            "shown": show_congrats,
            "text": (
                f"Bu ay {', '.join(k['name'] for k in congrats_kpis)} KPI'larında hedef seviyesinin üzerinde "
                "performans gösterdiniz. Başarılı performansınızı sürdürmenizi dileriz."
            ) if show_congrats and congrats_kpis else None,
            "kpi_codes": [k["code"] for k in congrats_kpis],
        },
        "trend": {
            "weekly_points": [
                {"bucket": p.bucket.isoformat(), "total_score": round(p.total_score, 2), "is_reliable": p.is_reliable}
                for p in weekly_points
            ],
            "shape": trend_shape,
            "text": _TREND_TEXT.get(trend_shape) if trend_shape else None,
        },
        "previous_month": previous_month,
    }


def get_or_generate_monthly_report(
    db: Session, foreman_id: UUID, year: int, month: int, force: bool = False
) -> ForemanMonthlyReport:
    if not is_month_completed(year, month):
        raise ValueError("Yalnızca tamamlanmış aylar için rapor oluşturulabilir.")

    existing = db.scalar(
        select(ForemanMonthlyReport).where(
            ForemanMonthlyReport.foreman_id == foreman_id,
            ForemanMonthlyReport.year == year,
            ForemanMonthlyReport.month == month,
        )
    )
    if existing and not force:
        return existing

    foreman = db.get(Foreman, foreman_id)
    if foreman is None:
        raise ValueError("Formen bulunamadı.")

    report_data = _build_report_data(db, foreman, year, month)
    overall = report_data.get("overall")

    if existing and force:
        existing.generated_at = datetime.now(timezone.utc)
        existing.overall_score = overall["score"] if overall else None
        existing.overall_level_name = overall["level"]["name"] if overall else None
        existing.is_reliable = not report_data["insufficient_data"]
        existing.report_data = report_data
        existing.version += 1
        db.commit()
        return existing

    row = ForemanMonthlyReport(
        foreman_id=foreman_id, year=year, month=month,
        generated_at=datetime.now(timezone.utc),
        overall_score=overall["score"] if overall else None,
        overall_level_name=overall["level"]["name"] if overall else None,
        is_reliable=not report_data["insufficient_data"],
        report_data=report_data,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return db.scalar(
            select(ForemanMonthlyReport).where(
                ForemanMonthlyReport.foreman_id == foreman_id,
                ForemanMonthlyReport.year == year,
                ForemanMonthlyReport.month == month,
            )
        )
    return row


def latest_completed_period() -> tuple[int, int]:
    today = date.today()
    year, month = _previous_month(today.year, today.month)
    return year, month
