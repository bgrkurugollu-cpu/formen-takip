from __future__ import annotations

from app.models.enums import ContributionWorkType, OtherGainType, RepeatPeriod, SuccessDirection, TimeUnit

MINUTES_PER_UNIT = {
    TimeUnit.SECOND: 1 / 60,
    TimeUnit.MINUTE: 1.0,
    TimeUnit.HOUR: 60.0,
}

OCCURRENCES_PER_MONTH = {
    RepeatPeriod.DAILY: 30.0,
    RepeatPeriod.WEEKLY: 4.345,
    RepeatPeriod.MONTHLY: 1.0,
}

GAIN_TYPE_DIRECTION: dict[OtherGainType, SuccessDirection] = {
    OtherGainType.CAPACITY_INCREASE: SuccessDirection.HIGHER_IS_BETTER,
    OtherGainType.LABOR_SAVING: SuccessDirection.HIGHER_IS_BETTER,
    OtherGainType.DOWNTIME_REDUCTION: SuccessDirection.LOWER_IS_BETTER,
    OtherGainType.GSF_REDUCTION: SuccessDirection.LOWER_IS_BETTER,
    OtherGainType.SCRAP_REDUCTION: SuccessDirection.LOWER_IS_BETTER,
    OtherGainType.SLOW_RUNNING_REDUCTION: SuccessDirection.LOWER_IS_BETTER,
    OtherGainType.SAFETY_RISK_REDUCTION: SuccessDirection.LOWER_IS_BETTER,
    OtherGainType.ENERGY_REDUCTION: SuccessDirection.LOWER_IS_BETTER,
    OtherGainType.QUALITY_DEFECT_REDUCTION: SuccessDirection.LOWER_IS_BETTER,
    OtherGainType.OTHER: SuccessDirection.LOWER_IS_BETTER,
}

_CAPACITY_BUCKET = {OtherGainType.CAPACITY_INCREASE}
_REDUCTION_BUCKET = {
    OtherGainType.DOWNTIME_REDUCTION,
    OtherGainType.GSF_REDUCTION,
    OtherGainType.SCRAP_REDUCTION,
    OtherGainType.SLOW_RUNNING_REDUCTION,
}
_QUALITY_SAFETY_ENERGY_BUCKET = {
    OtherGainType.QUALITY_DEFECT_REDUCTION,
    OtherGainType.SAFETY_RISK_REDUCTION,
    OtherGainType.ENERGY_REDUCTION,
}


def duration_to_minutes(value: float | None, unit: TimeUnit | None) -> float | None:
    if value is None or unit is None:
        return None
    return round(float(value) * MINUTES_PER_UNIT[unit], 4)


def compute_time_saving(previous_duration: float | None, new_duration: float | None) -> float | None:
    """Önceki - yeni süre; yeni süre öncekinden büyük/eşitse kazanç yok (None döner).

    Girdiler Postgres `Numeric` kolonlarından geldiğinde SQLAlchemy `Decimal` döndürür;
    burada `float`'a çevirmek, formül genelinde Decimal/float karışık aritmetiği önler.
    """
    if previous_duration is None or new_duration is None:
        return None
    previous_duration, new_duration = float(previous_duration), float(new_duration)
    if new_duration >= previous_duration:
        return None
    return round(previous_duration - new_duration, 2)


def compute_monthly_total(
    per_occurrence_minutes: float | None, repeat_period: RepeatPeriod | None, repeat_count: float | None
) -> float | None:
    if per_occurrence_minutes is None or repeat_period is None or repeat_count is None:
        return None
    return round(float(per_occurrence_minutes) * float(repeat_count) * OCCURRENCES_PER_MONTH[repeat_period], 2)


def compute_change(previous: float | None, next_value: float | None) -> tuple[float | None, float | None]:
    """(değişim miktarı, değişim yüzdesi). previous None veya 0 ise yüzde None döner."""
    if previous is None or next_value is None:
        return None, None
    previous, next_value = float(previous), float(next_value)
    amount = round(next_value - previous, 4)
    if previous == 0:
        return amount, None
    percent = round((amount / abs(previous)) * 100, 3)
    return amount, percent


def is_improvement(gain_type: OtherGainType, change_amount: float | None) -> bool | None:
    if change_amount is None:
        return None
    direction = GAIN_TYPE_DIRECTION.get(gain_type, SuccessDirection.LOWER_IS_BETTER)
    if direction == SuccessDirection.HIGHER_IS_BETTER:
        return change_amount > 0
    return change_amount < 0


def resolve_highlighted_gain(work, gains: list) -> dict | None:
    """Öne çıkan kazanımı önceliğe göre (veya manuel referansa göre) çözer.

    `work` bir ContributionWork, `gains` ilişkili ContributionGain listesi.
    """
    if work.highlighted_gain_mode.value == "manual" and work.highlighted_gain_ref:
        manual = _resolve_manual_ref(work, gains)
        if manual is not None:
            return manual

    if work.verified_amount is not None:
        return {
            "source": "verified_financial",
            "label": "Doğrulanmış Maddi Kazanç",
            "value": float(work.verified_amount),
            "unit": work.currency.value if work.currency else None,
            "is_verified": True,
        }
    if work.estimated_amount is not None:
        return {
            "source": "estimated_financial",
            "label": "Tahmini Maddi Kazanç",
            "value": float(work.estimated_amount),
            "unit": work.currency.value if work.currency else None,
            "is_verified": False,
        }
    if work.monthly_total_saving_minutes is not None:
        return {
            "source": "time_saving",
            "label": "Aylık Zaman Kazancı",
            "value": float(work.monthly_total_saving_minutes),
            "unit": "dakika",
            "is_verified": False,
        }

    for bucket, label in (
        (_CAPACITY_BUCKET, None),
        (_REDUCTION_BUCKET, None),
        (_QUALITY_SAFETY_ENERGY_BUCKET, None),
    ):
        candidate = _best_gain_in_bucket(gains, bucket)
        if candidate is not None:
            return candidate

    candidate = _best_gain_in_bucket(gains, {g.gain_type for g in gains})
    return candidate


def _resolve_manual_ref(work, gains: list) -> dict | None:
    ref = work.highlighted_gain_ref
    if ref == "verified_financial" and work.verified_amount is not None:
        return {
            "source": "verified_financial", "label": "Doğrulanmış Maddi Kazanç",
            "value": float(work.verified_amount), "unit": work.currency.value if work.currency else None, "is_verified": True,
        }
    if ref == "estimated_financial" and work.estimated_amount is not None:
        return {
            "source": "estimated_financial", "label": "Tahmini Maddi Kazanç",
            "value": float(work.estimated_amount), "unit": work.currency.value if work.currency else None, "is_verified": False,
        }
    if ref == "time_saving" and work.monthly_total_saving_minutes is not None:
        return {
            "source": "time_saving", "label": "Aylık Zaman Kazancı",
            "value": float(work.monthly_total_saving_minutes), "unit": "dakika", "is_verified": False,
        }
    if ref.startswith("gain:"):
        gain_id = ref.split(":", 1)[1]
        for g in gains:
            if str(g.id) == gain_id:
                amount, percent = compute_change(g.previous_value, g.next_value)
                value = percent if percent is not None else amount
                return {
                    "source": f"gain:{g.id}", "label": gain_type_label(g.gain_type),
                    "value": float(value) if value is not None else None,
                    "unit": "%" if percent is not None else g.unit, "is_verified": False,
                }
    return None


def _best_gain_in_bucket(gains: list, bucket: set) -> dict | None:
    candidates = [g for g in gains if g.gain_type in bucket and g.change_percent is not None]
    if not candidates:
        return None
    best = max(candidates, key=lambda g: abs(g.change_percent))
    return {
        "source": f"gain:{best.id}",
        "label": gain_type_label(best.gain_type),
        "value": abs(float(best.change_percent)),
        "unit": "%",
        "is_verified": False,
    }


_GAIN_TYPE_LABELS = {
    OtherGainType.CAPACITY_INCREASE: "Üretim Kapasitesi Artışı",
    OtherGainType.DOWNTIME_REDUCTION: "Duruş Süresi Azalması",
    OtherGainType.GSF_REDUCTION: "GSF Azalması",
    OtherGainType.SCRAP_REDUCTION: "Iskarta Azalması",
    OtherGainType.SLOW_RUNNING_REDUCTION: "Ağır Gitme Azalması",
    OtherGainType.SAFETY_RISK_REDUCTION: "İş Kazası Riski Azalması",
    OtherGainType.ENERGY_REDUCTION: "Enerji Tüketimi Azalması",
    OtherGainType.LABOR_SAVING: "İş Gücü Tasarrufu",
    OtherGainType.QUALITY_DEFECT_REDUCTION: "Kalite Hatası Azalması",
    OtherGainType.OTHER: "Diğer Kazanım",
}


def gain_type_label(gain_type: OtherGainType) -> str:
    return _GAIN_TYPE_LABELS.get(gain_type, "Kazanım")


def resolve_badges(work) -> list[str]:
    badges: list[str] = []
    if work.is_gain_verified:
        badges.append("Doğrulanmış Kazanç")
    if work.impact_level and work.impact_level.value == "high":
        badges.append("Yüksek Etki")
    if work.is_standardized:
        badges.append("Standartlaştırıldı")
    if work.is_permanent_solution:
        badges.append("Kalıcı Çözüm")
    if work.is_applicable_other_plants:
        badges.append("Diğer Tesislere Uygulanabilir")
    if work.work_instruction_updated:
        badges.append("İş Talimatı Güncellendi")
    if work.is_gain_verified and work.verified_by_department and work.verified_by_department.value == "finance":
        badges.append("Finans Tarafından Doğrulandı")
    return badges


REQUIRED_FOR_PUBLISH_MESSAGES = {
    "foreman_ids": "En az bir ilgili formen seçilmelidir.",
    "plant_id": "Tesis seçilmelidir.",
    "work_date": "Çalışma tarihi girilmelidir.",
    "work_type": "Çalışma türü seçilmelidir.",
    "work_type_other_note": "'Diğer' seçildiğinde çalışma türünü açıklayan bir not girilmelidir.",
    "title": "Çalışma başlığı girilmelidir.",
    "summary": "Kısa özet girilmelidir.",
    "problem_description": "Tespit edilen problem girilmelidir.",
    "solution_description": "Uygulanan çözüm girilmelidir.",
}


def validate_for_publish(data: dict) -> dict[str, str]:
    """`data` alan adı -> değer sözlüğü (payload veya mevcut kayıttan). Hata yoksa boş dict döner."""
    errors: dict[str, str] = {}

    if not data.get("title"):
        errors["title"] = REQUIRED_FOR_PUBLISH_MESSAGES["title"]
    if not data.get("foreman_ids"):
        errors["foreman_ids"] = REQUIRED_FOR_PUBLISH_MESSAGES["foreman_ids"]
    if not data.get("plant_id"):
        errors["plant_id"] = REQUIRED_FOR_PUBLISH_MESSAGES["plant_id"]
    if not data.get("work_date"):
        errors["work_date"] = REQUIRED_FOR_PUBLISH_MESSAGES["work_date"]
    elif data.get("work_date_end") and data["work_date_end"] < data["work_date"]:
        errors["work_date_end"] = "Bitiş tarihi başlangıç tarihinden önce olamaz."
    work_type = data.get("work_type")
    if not work_type:
        errors["work_type"] = REQUIRED_FOR_PUBLISH_MESSAGES["work_type"]
    else:
        work_type_value = work_type.value if isinstance(work_type, ContributionWorkType) else work_type
        if work_type_value == ContributionWorkType.OTHER.value and not data.get("work_type_other_note"):
            errors["work_type_other_note"] = REQUIRED_FOR_PUBLISH_MESSAGES["work_type_other_note"]
    if not data.get("summary"):
        errors["summary"] = REQUIRED_FOR_PUBLISH_MESSAGES["summary"]
    if not data.get("problem_description"):
        errors["problem_description"] = REQUIRED_FOR_PUBLISH_MESSAGES["problem_description"]
    if not data.get("solution_description"):
        errors["solution_description"] = REQUIRED_FOR_PUBLISH_MESSAGES["solution_description"]

    return errors
