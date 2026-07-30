
from __future__ import annotations

from dataclasses import dataclass, field

from app.models.enums import CalculationType

WEIGHT_SUM_TOLERANCE = 0.01
DEFAULT_BASE_SCORE = 100.0


class KpiCalculationError(ValueError):
    pass


def _clip(value: float, min_score: float, max_score: float) -> float:
    return max(min_score, min(max_score, value))


def higher_is_better(actual: float, target: float, min_score: float, max_score: float) -> float:
    if actual < 0:
        raise KpiCalculationError("Gerçekleşen değer negatif olamaz.")
    if target <= 0:
        return max_score if actual > 0 else min_score
    raw = (actual / target) * 100
    return _clip(raw, min_score, max_score)


def lower_is_better(actual: float, target: float, min_score: float, max_score: float) -> float:
    if actual < 0 or target < 0:
        raise KpiCalculationError("Değerler negatif olamaz.")
    if actual == 0:
        return max_score
    if target == 0:
        return min_score
    raw = (target / actual) * 100
    return _clip(raw, min_score, max_score)


def range_target(
    actual: float,
    lower_bound: float,
    upper_bound: float,
    tolerance: float,
    penalty_rate: float,
    min_score: float,
    max_score: float,
    base_score: float = DEFAULT_BASE_SCORE,
) -> float:
    if lower_bound > upper_bound:
        raise KpiCalculationError("lower_bound, upper_bound'dan büyük olamaz.")
    if lower_bound <= actual <= upper_bound:
        return _clip(base_score, min_score, max_score)
    distance = (lower_bound - actual) if actual < lower_bound else (actual - upper_bound)
    effective_distance = max(0.0, distance - tolerance)
    raw = base_score - effective_distance * penalty_rate
    return _clip(raw, min_score, max_score)


def direct_score(actual: float, min_score: float, max_score: float) -> float:
    return _clip(actual, min_score, max_score)


def proportional_penalty(
    actual: float,
    target: float,
    penalty_per_unit: float,
    unit_size: float,
    min_score: float,
    max_score: float,
    base_score: float = DEFAULT_BASE_SCORE,
) -> float:
    if unit_size <= 0:
        raise KpiCalculationError("unit_size sıfır veya negatif olamaz.")
    overage = max(0.0, actual - target)
    penalty = (overage / unit_size) * penalty_per_unit
    raw = base_score - penalty
    return _clip(raw, min_score, max_score)


@dataclass
class CalculationRuleParams:
    calculation_type: CalculationType
    min_score: float
    max_score: float
    lower_bound: float | None = None
    upper_bound: float | None = None
    tolerance: float = 0.0
    penalty_rate: float = 0.0
    penalty_per_unit: float = 0.0
    unit_size: float = 1.0
    base_score: float = DEFAULT_BASE_SCORE


def _uncapped_score(actual: float, target: float, rule: CalculationRuleParams) -> float:
    if rule.calculation_type == CalculationType.HIGHER_IS_BETTER:
        if actual < 0:
            raise KpiCalculationError("Gerçekleşen değer negatif olamaz.")
        if target <= 0:
            return rule.max_score if actual > 0 else rule.min_score
        return (actual / target) * 100
    if rule.calculation_type == CalculationType.LOWER_IS_BETTER:
        if actual < 0 or target < 0:
            raise KpiCalculationError("Değerler negatif olamaz.")
        if actual == 0:
            return rule.max_score
        if target == 0:
            return rule.min_score
        return (target / actual) * 100
    if rule.calculation_type == CalculationType.RANGE_TARGET:
        if rule.lower_bound is None or rule.upper_bound is None:
            raise KpiCalculationError("range_target için lower_bound/upper_bound gerekli.")
        if rule.lower_bound > rule.upper_bound:
            raise KpiCalculationError("lower_bound, upper_bound'dan büyük olamaz.")
        if rule.lower_bound <= actual <= rule.upper_bound:
            return rule.base_score
        distance = (rule.lower_bound - actual) if actual < rule.lower_bound else (actual - rule.upper_bound)
        effective_distance = max(0.0, distance - rule.tolerance)
        return rule.base_score - effective_distance * rule.penalty_rate
    if rule.calculation_type == CalculationType.DIRECT_SCORE:
        return actual
    if rule.calculation_type == CalculationType.PROPORTIONAL_PENALTY:
        overage = max(0.0, actual - target)
        penalty = (overage / rule.unit_size) * rule.penalty_per_unit
        return rule.base_score - penalty
    raise KpiCalculationError(
        f"'{rule.calculation_type}' hesaplama türü desteklenmiyor (custom_formula bilinçli olarak "
        "kapsam dışı bırakıldı — bölüm 7.6)."
    )


@dataclass
class ScoreResult:
    raw_score: float
    capped_score: float


def calculate_score(actual: float, target: float, rule: CalculationRuleParams) -> ScoreResult:
    raw = _uncapped_score(actual, target, rule)
    capped = _clip(raw, rule.min_score, rule.max_score)
    return ScoreResult(raw_score=raw, capped_score=capped)


def calculate_raw_score(actual: float, target: float, rule: CalculationRuleParams) -> float:
    if rule.calculation_type == CalculationType.HIGHER_IS_BETTER:
        return higher_is_better(actual, target, rule.min_score, rule.max_score)
    if rule.calculation_type == CalculationType.LOWER_IS_BETTER:
        return lower_is_better(actual, target, rule.min_score, rule.max_score)
    if rule.calculation_type == CalculationType.RANGE_TARGET:
        if rule.lower_bound is None or rule.upper_bound is None:
            raise KpiCalculationError("range_target için lower_bound/upper_bound gerekli.")
        return range_target(
            actual, rule.lower_bound, rule.upper_bound, rule.tolerance, rule.penalty_rate,
            rule.min_score, rule.max_score, rule.base_score,
        )
    if rule.calculation_type == CalculationType.DIRECT_SCORE:
        return direct_score(actual, rule.min_score, rule.max_score)
    if rule.calculation_type == CalculationType.PROPORTIONAL_PENALTY:
        return proportional_penalty(
            actual, target, rule.penalty_per_unit, rule.unit_size, rule.min_score, rule.max_score, rule.base_score,
        )
    raise KpiCalculationError(
        f"'{rule.calculation_type}' hesaplama türü desteklenmiyor (custom_formula bilinçli olarak "
        "kapsam dışı bırakıldı — bölüm 7.6, güvenlik nedeniyle kod çalıştırma izni verilmiyor)."
    )


def validate_kpi_weights(weights: list[float]) -> tuple[bool, str | None]:
    total = sum(weights)
    if abs(total - 100.0) > WEIGHT_SUM_TOLERANCE:
        return False, f"KPI ağırlıkları toplamı 100 değil: {total:.2f}"
    return True, None


@dataclass
class KpiScoreInput:
    kpi_code: str
    score: float
    weight: float


@dataclass
class TotalScoreResult:
    total_score: float
    is_reliable: bool
    missing_kpi_codes: list[str] = field(default_factory=list)
    contributions: dict[str, float] = field(default_factory=dict)


def compute_weighted_total(
    present_scores: list[KpiScoreInput],
    missing_kpi_codes: list[str] | None = None,
) -> TotalScoreResult:
    missing_kpi_codes = missing_kpi_codes or []
    if not present_scores:
        return TotalScoreResult(total_score=0.0, is_reliable=False, missing_kpi_codes=missing_kpi_codes)

    weight_sum = sum(s.weight for s in present_scores)
    is_reliable = len(missing_kpi_codes) == 0
    contributions: dict[str, float] = {}
    total = 0.0
    for item in present_scores:
        effective_weight = item.weight if is_reliable else (item.weight / weight_sum * 100.0)
        contribution = item.score * (effective_weight / 100.0)
        contributions[item.kpi_code] = contribution
        total += contribution

    return TotalScoreResult(
        total_score=total,
        is_reliable=is_reliable,
        missing_kpi_codes=missing_kpi_codes,
        contributions=contributions,
    )


@dataclass
class PerformanceLevel:
    name: str
    min_score: float
    max_score: float
    description: str
    color: str
    icon: str
    sort_order: int


def resolve_performance_level(score: float, levels: list[PerformanceLevel]) -> PerformanceLevel:
    if not levels:
        raise KpiCalculationError("Performans seviyesi kuralları tanımlı değil.")
    ordered = sorted(levels, key=lambda lv: lv.min_score)
    for level in ordered:
        if level.min_score <= score <= level.max_score:
            return level
    return ordered[0] if score < ordered[0].min_score else ordered[-1]


def aggregate_ratio_kpi(numerator_sum: float, denominator_sum: float) -> float:
    if denominator_sum == 0:
        return 0.0
    return (numerator_sum / denominator_sum) * 100
