
from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.models.enums import CalculationType

WEIGHT_SUM_TOLERANCE = 0.01
DEFAULT_BASE_SCORE = 100.0

# Genel puan için: kapsanan ağırlık bu oranın altındaysa genel puan üretilmez (spec bölüm 10 —
# "eksik KPI sayısı izin verilen sınırı aşarsa genel puan üretme"). Spec bir sayı vermediği için
# burada tek bir yerde tutulan, ayarlanabilir bir varsayılan.
MIN_COVERED_WEIGHT_RATIO = 0.5


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



# ---------------------------------------------------------------------------------------------
# KPI'a özel puanlama formülleri (spec bölüm 4-8). Her formül yalnızca kendi katsayılarını alır —
# kpi_calculation_rules.parameters içindeki formula_type + katsayılar, calculate_custom_score
# üzerinden buraya yönlendirilir. Nihai puan yalnızca 0'da taban görür (rule 6/7) — manuel bir üst
# sınır uygulanmaz.
# ---------------------------------------------------------------------------------------------


def _heavy_weight_from_ratio(ratio: float, good_coefficient: float, bad_coefficient: float) -> float:
    if ratio <= 1:
        return 100.0 + good_coefficient * (1.0 - ratio)
    return 100.0 - bad_coefficient * math.log2(ratio)


def score_heavy_weight(actual: float, target: float, good_coefficient: float = 9.0, bad_coefficient: float = 12.0) -> ScoreResult:
    """Ağır Gitme (bölüm 4). `actual` işaretlidir (OVERWEIGHT pozitif, UNDERWEIGHT negatif);
    puanlamada mutlak büyüklüğü kullanılır."""
    if target is None or target <= 0:
        raise KpiCalculationError("Ağır Gitme hedefi sıfır, negatif veya eksik olamaz.")
    raw = _heavy_weight_from_ratio(abs(actual) / target, good_coefficient, bad_coefficient)
    return ScoreResult(raw_score=raw, capped_score=max(0.0, raw))


def score_heavy_weight_from_period_ratio(period_ratio: float, good_coefficient: float = 9.0, bad_coefficient: float = 12.0) -> ScoreResult:
    """Dönemsel Ağır Gitme (bölüm 11.4): üretim ağırlıklı oran zaten hesaplanmış olarak gelir."""
    raw = _heavy_weight_from_ratio(max(0.0, period_ratio), good_coefficient, bad_coefficient)
    return ScoreResult(raw_score=raw, capped_score=max(0.0, raw))


def _hybrid_base_piecewise_log(
    actual: float, target: float, minimum_normalization_base: float, good_coefficient: float, bad_coefficient: float
) -> float:
    if actual < 0 or target < 0:
        raise KpiCalculationError("Değerler negatif olamaz.")
    base = max(target, minimum_normalization_base)
    if actual <= target:
        return 100.0 + good_coefficient * ((target - actual) / base)
    return 100.0 - bad_coefficient * math.log2(1.0 + ((actual - target) / base))


def score_gsf(actual: float, target: float, minimum_normalization_base: float = 0.05, good_coefficient: float = 10.0, bad_coefficient: float = 16.0) -> ScoreResult:
    """GSF (bölüm 5): geri kazanılamayan nihai kayıp — Iskarta'dan daha sert puanlanır."""
    raw = _hybrid_base_piecewise_log(actual, target, minimum_normalization_base, good_coefficient, bad_coefficient)
    return ScoreResult(raw_score=raw, capped_score=max(0.0, raw))


def score_inkita(actual: float, target: float, minimum_normalization_base: float = 0.50, good_coefficient: float = 6.0, bad_coefficient: float = 10.0) -> ScoreResult:
    """İnkita (bölüm 7): `actual` yalnızca Teknik% + İmalat% toplamı olmalı — Diğer% dahil edilmez."""
    raw = _hybrid_base_piecewise_log(actual, target, minimum_normalization_base, good_coefficient, bad_coefficient)
    return ScoreResult(raw_score=raw, capped_score=max(0.0, raw))


def score_iskarta(actual: float, target: float, good_coefficient: float = 12.0, bad_coefficient: float = 12.0) -> ScoreResult:
    """Iskarta (bölüm 6): geri dönüştürülebilir kayıp — GSF'ye göre daha yumuşak puanlanır."""
    if target is None or target <= 0:
        raise KpiCalculationError("Iskarta hedefi sıfır, negatif veya eksik olamaz.")
    ratio = actual / target
    if actual <= target:
        raw = 100.0 + good_coefficient * (1.0 - ratio)
    else:
        raw = 100.0 - bad_coefficient * math.log2(ratio)
    return ScoreResult(raw_score=raw, capped_score=max(0.0, raw))


def _plan_compliance_from_deviation(deviation_rate: float, normal_deviation_limit: float, excess_deviation_coefficient: float) -> float:
    if deviation_rate <= normal_deviation_limit:
        return 100.0 - deviation_rate
    # (100 - limit) ile başlar, böylece limit noktasında iki dal aynı değeri üretir (spec bölüm 8:
    # örnekte limit=5 -> 95'ten başlar). Sabit "95" yerine limitten türetilir ki limit değişirse
    # sıçrama oluşmasın.
    base_at_limit = 100.0 - normal_deviation_limit
    return base_at_limit - excess_deviation_coefficient * math.log2(deviation_rate / normal_deviation_limit)


def score_plan_compliance(planned: float, actual: float, normal_deviation_limit: float = 5.0, excess_deviation_coefficient: float = 10.0) -> ScoreResult:
    """Plana Uyum (bölüm 8): plan altı ve plan üstü sapmalar aynı formülle, mutlak sapma üzerinden."""
    if planned is None or planned <= 0:
        raise KpiCalculationError("Planlanan üretim sıfır, negatif veya eksik olamaz.")
    deviation_rate = abs(actual - planned) / planned * 100.0
    raw = _plan_compliance_from_deviation(deviation_rate, normal_deviation_limit, excess_deviation_coefficient)
    return ScoreResult(raw_score=raw, capped_score=max(0.0, raw))


def score_plan_compliance_from_period_deviation(deviation_rate: float, normal_deviation_limit: float = 5.0, excess_deviation_coefficient: float = 10.0) -> ScoreResult:
    """Dönemsel Plana Uyum (bölüm 11.5): sapma oranı zaten mutlak farkların toplamından hesaplanmış olarak gelir."""
    raw = _plan_compliance_from_deviation(max(0.0, deviation_rate), normal_deviation_limit, excess_deviation_coefficient)
    return ScoreResult(raw_score=raw, capped_score=max(0.0, raw))


def _dispatch_hybrid_base_piecewise_log(actual: float, target: float, params: dict) -> ScoreResult:
    raw = _hybrid_base_piecewise_log(
        actual, target,
        params.get("minimum_normalization_base", 0.05),
        params.get("good_coefficient", 10.0),
        params.get("bad_coefficient", 16.0),
    )
    return ScoreResult(raw_score=raw, capped_score=max(0.0, raw))


_CUSTOM_FORMULA_DISPATCH = {
    "SIGNED_ABSOLUTE_PIECEWISE": lambda actual, target, p: score_heavy_weight(
        actual, target, p.get("good_coefficient", 9.0), p.get("bad_coefficient", 12.0)
    ),
    "TARGET_RATIO_PIECEWISE": lambda actual, target, p: score_iskarta(
        actual, target, p.get("good_coefficient", 12.0), p.get("bad_coefficient", 12.0)
    ),
    "HYBRID_BASE_PIECEWISE_LOG": _dispatch_hybrid_base_piecewise_log,
}


def calculate_custom_score(actual: float, target: float, formula_type: str, params: dict) -> ScoreResult:
    """AGIR_GITME/GSF/ISKARTA/INKITA için ortak giriş noktası — hepsi (actual, target) çifti alır.
    PLANA_UYUM bunun dışındadır (planned/actual gerektirir) — bkz. `compute_score_for_rule`."""
    handler = _CUSTOM_FORMULA_DISPATCH.get(formula_type)
    if handler is None:
        raise KpiCalculationError(f"Bilinmeyen formula_type: '{formula_type}'.")
    return handler(actual, target, params)


def compute_score_for_rule(
    calculation_type: CalculationType,
    parameters: dict,
    *,
    actual: float,
    target: float,
    numerator: float | None = None,
    denominator: float | None = None,
    min_score: float = 0.0,
    max_score: float = 999999.99,
) -> ScoreResult:
    """Bir performans kaydı için aktif kuralın türü ne olursa olsun tek giriş noktası — ingestion.py
    ve rescoring.py aynı bu fonksiyonu çağırır (spec rule 17: sentetik ve SAP aynı servisleri kullanır).
    CUSTOM_FORMULA dışındaki türler mevcut generic motora (calculate_score) düşer; CUSTOM_FORMULA ise
    formula_type'a göre yeni KPI'a özel formüllere yönlendirilir. Plana Uyum, target yerine
    numerator/denominator'ı (fiili/planlanan miktar) kullanır."""
    if calculation_type != CalculationType.CUSTOM_FORMULA:
        rule_params = CalculationRuleParams(
            calculation_type=calculation_type, min_score=min_score, max_score=max_score, **parameters
        )
        return calculate_score(actual, target, rule_params)

    formula_type = parameters.get("formula_type")
    if formula_type == "PIECEWISE_LINEAR_LOGARITHMIC":
        if numerator is None or denominator is None:
            raise KpiCalculationError("Plana Uyum için fiili/planlanan miktar (numerator/denominator) gerekli.")
        return score_plan_compliance(
            planned=denominator, actual=numerator,
            normal_deviation_limit=parameters.get("normal_deviation_limit", 5.0),
            excess_deviation_coefficient=parameters.get("excess_deviation_coefficient", 10.0),
        )
    return calculate_custom_score(actual, target, formula_type, parameters)


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


def period_ratio_score(
    actual_sum: float,
    expected_sum: float,
    success_direction_higher: bool,
    epsilon: float = 1e-9,
    max_score: float | None = None,
) -> float:
    """Dönem bazlı puan: önce pay/payda toplanır, tek bir orandan tek bir puan üretilir
    (günlük puanların ortalaması alınmaz). Bant/eşik uygulanmaz. `max_score`, yalnızca
    gerçekleşen toplamın (neredeyse) sıfır olduğu tekil durumda (ör. dönem boyunca hiç
    fire oluşmaması) bölme sonucunun taşmasını önleyen bir sayısal güvenlik sınırıdır —
    normal aralıktaki puanlar bu değere hiçbir zaman yaklaşmaz, bu yüzden bir performans
    bandı/tavanı anlamına gelmez."""
    if success_direction_higher:
        raw = 100.0 * actual_sum / max(expected_sum, epsilon)
    else:
        raw = 100.0 * expected_sum / max(actual_sum, epsilon)
    if max_score is not None:
        return min(raw, max_score)
    return raw


def weighted_geometric_score(component_scores: list[tuple[float, float]]) -> float:
    """Ağırlıklı geometrik ortalama: tek bir KPI'daki aşırı yüksek puanın diğer kötü
    sonuçları gizlemesini engeller. Yalnızca verisi bulunan bileşenler geçirilmelidir —
    ağırlıklar kendi aralarında otomatik yeniden normalize edilir (eksik KPI durumunda)."""
    weight_sum = sum(w for _, w in component_scores)
    if weight_sum <= 0:
        return 0.0
    product = 1.0
    for score, weight in component_scores:
        product *= (max(score, 0.0) / 100.0) ** (weight / weight_sum)
    return 100.0 * product
