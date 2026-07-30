import pytest

from app.models.enums import CalculationType
from app.services.kpi_engine import (
    CalculationRuleParams,
    KpiCalculationError,
    KpiScoreInput,
    PerformanceLevel,
    aggregate_ratio_kpi,
    calculate_raw_score,
    calculate_score,
    compute_weighted_total,
    direct_score,
    higher_is_better,
    lower_is_better,
    proportional_penalty,
    range_target,
    resolve_performance_level,
    validate_kpi_weights,
)


class TestHigherIsBetter:
    def test_exact_target(self):
        assert higher_is_better(1000, 1000, 0, 120) == 100

    def test_below_target(self):
        assert higher_is_better(950, 1000, 0, 120) == pytest.approx(95)

    def test_exceeds_max_score_is_capped(self):
        assert higher_is_better(1300, 1000, 0, 120) == 120

    def test_zero_target_zero_actual(self):
        assert higher_is_better(0, 0, 0, 120) == 0

    def test_zero_target_positive_actual(self):
        assert higher_is_better(5, 0, 0, 120) == 120

    def test_negative_actual_raises(self):
        with pytest.raises(KpiCalculationError):
            higher_is_better(-1, 1000, 0, 120)


class TestLowerIsBetter:
    def test_below_target_is_better_than_100(self):
        assert lower_is_better(20, 30, 0, 120) == 120

    def test_above_target(self):
        assert lower_is_better(40, 30, 0, 120) == pytest.approx(75)

    def test_zero_actual_is_best(self):
        assert lower_is_better(0, 30, 0, 120) == 120

    def test_zero_target_zero_actual(self):
        assert lower_is_better(0, 0, 0, 120) == 120

    def test_zero_target_positive_actual_is_worst(self):
        assert lower_is_better(5, 0, 0, 120) == 0

    def test_negative_raises(self):
        with pytest.raises(KpiCalculationError):
            lower_is_better(-1, 30, 0, 120)


class TestRangeTarget:
    def test_within_range_full_score(self):
        assert range_target(95, 90, 100, 0, 5, 0, 120) == 100

    def test_below_range_within_tolerance(self):
        assert range_target(88, 90, 100, 3, 5, 0, 120) == 100

    def test_below_range_beyond_tolerance(self):
        assert range_target(85, 90, 100, 3, 5, 0, 120) == pytest.approx(90)

    def test_above_range_beyond_tolerance(self):
        assert range_target(108, 90, 100, 3, 5, 0, 120) == pytest.approx(75)

    def test_score_floored_at_min(self):
        assert range_target(0, 90, 100, 0, 50, 10, 120) == 10

    def test_invalid_bounds_raise(self):
        with pytest.raises(KpiCalculationError):
            range_target(50, 100, 90, 0, 5, 0, 120)


class TestDirectScore:
    def test_within_bounds(self):
        assert direct_score(85, 0, 100) == 85

    def test_capped_at_max(self):
        assert direct_score(150, 0, 100) == 100

    def test_floored_at_min(self):
        assert direct_score(-10, 0, 100) == 0


class TestProportionalPenalty:
    def test_within_target_full_score(self):
        assert proportional_penalty(25, 30, 5, 5, 0, 120) == 100

    def test_overage_penalty(self):
        assert proportional_penalty(40, 30, 5, 5, 0, 120) == pytest.approx(90)

    def test_floored_at_min_score(self):
        assert proportional_penalty(1000, 30, 5, 5, 20, 120) == 20

    def test_zero_unit_size_raises(self):
        with pytest.raises(KpiCalculationError):
            proportional_penalty(40, 30, 5, 0, 0, 120)


class TestDispatch:
    def test_calculate_raw_score_dispatches_higher_is_better(self):
        rule = CalculationRuleParams(calculation_type=CalculationType.HIGHER_IS_BETTER, min_score=0, max_score=120)
        assert calculate_raw_score(950, 1000, rule) == pytest.approx(95)

    def test_custom_formula_not_supported(self):
        rule = CalculationRuleParams(calculation_type=CalculationType.CUSTOM_FORMULA, min_score=0, max_score=120)
        with pytest.raises(KpiCalculationError):
            calculate_raw_score(10, 10, rule)

    def test_range_target_requires_bounds(self):
        rule = CalculationRuleParams(calculation_type=CalculationType.RANGE_TARGET, min_score=0, max_score=120)
        with pytest.raises(KpiCalculationError):
            calculate_raw_score(50, 50, rule)


class TestRawVsCappedScore:
    def test_raw_score_exceeds_cap_but_capped_is_limited(self):
        rule = CalculationRuleParams(calculation_type=CalculationType.HIGHER_IS_BETTER, min_score=0, max_score=120)
        result = calculate_score(1300, 1000, rule)
        assert result.raw_score == pytest.approx(130)
        assert result.capped_score == 120

    def test_raw_and_capped_equal_when_within_bounds(self):
        rule = CalculationRuleParams(calculation_type=CalculationType.HIGHER_IS_BETTER, min_score=0, max_score=120)
        result = calculate_score(950, 1000, rule)
        assert result.raw_score == pytest.approx(95)
        assert result.capped_score == pytest.approx(95)

    def test_raw_score_below_min_but_capped_is_floored(self):
        rule = CalculationRuleParams(calculation_type=CalculationType.DIRECT_SCORE, min_score=0, max_score=100)
        result = calculate_score(-25, 0, rule)
        assert result.raw_score == -25
        assert result.capped_score == 0


class TestWeightValidation:
    def test_valid_weights(self):
        ok, msg = validate_kpi_weights([30, 20, 20, 20, 10])
        assert ok is True
        assert msg is None

    def test_invalid_weights(self):
        ok, msg = validate_kpi_weights([30, 20, 20, 20, 5])
        assert ok is False
        assert "100" in msg


class TestWeightedTotal:
    def test_all_present_matches_spec_example(self):
        scores = [
            KpiScoreInput("uretim", 90, 30),
            KpiScoreInput("fire", 85, 20),
            KpiScoreInput("durus", 100, 20),
            KpiScoreInput("kalite", 95, 20),
            KpiScoreInput("guvenlik", 80, 10),
        ]
        result = compute_weighted_total(scores)
        assert result.total_score == pytest.approx(91.0)
        assert result.is_reliable is True

    def test_missing_kpi_renormalizes_and_flags_unreliable(self):
        scores = [
            KpiScoreInput("uretim", 90, 30),
            KpiScoreInput("fire", 85, 20),
            KpiScoreInput("durus", 100, 20),
            KpiScoreInput("kalite", 95, 20),
        ]
        result = compute_weighted_total(scores, missing_kpi_codes=["guvenlik"])
        assert result.is_reliable is False
        assert result.missing_kpi_codes == ["guvenlik"]
        expected = (90 * 30 + 85 * 20 + 100 * 20 + 95 * 20) / 90
        assert result.total_score == pytest.approx(expected)

    def test_no_scores_returns_unreliable_zero(self):
        result = compute_weighted_total([])
        assert result.total_score == 0
        assert result.is_reliable is False


class TestPerformanceLevel:
    LEVELS = [
        PerformanceLevel("Kritik", 0, 69.99, "", "red", "alert", 1),
        PerformanceLevel("Geliştirilmeli", 70, 79.99, "", "orange", "warning", 2),
        PerformanceLevel("İyi", 80, 89.99, "", "yellow", "thumbs-up", 3),
        PerformanceLevel("Çok İyi", 90, 99.99, "", "blue", "star", 4),
        PerformanceLevel("Mükemmel", 100, 120, "", "green", "trophy", 5),
    ]

    def test_mid_range(self):
        assert resolve_performance_level(91, self.LEVELS).name == "Çok İyi"

    def test_boundary_value(self):
        assert resolve_performance_level(100, self.LEVELS).name == "Mükemmel"

    def test_critical(self):
        assert resolve_performance_level(50, self.LEVELS).name == "Kritik"

    def test_above_max_clips_to_top(self):
        assert resolve_performance_level(150, self.LEVELS).name == "Mükemmel"

    def test_no_levels_raises(self):
        with pytest.raises(KpiCalculationError):
            resolve_performance_level(50, [])


class TestRatioAggregation:
    def test_ratio_recompute_not_simple_average(self):
        result = aggregate_ratio_kpi(numerator_sum=50, denominator_sum=150)
        assert result == pytest.approx(33.333, abs=0.01)

    def test_zero_denominator_returns_zero(self):
        assert aggregate_ratio_kpi(0, 0) == 0
