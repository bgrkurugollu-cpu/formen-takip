import pytest

from app.models.enums import OtherGainType, RepeatPeriod, TimeUnit
from app.services.contribution_calc import (
    compute_change,
    compute_monthly_total,
    compute_time_saving,
    duration_to_minutes,
    is_improvement,
    validate_for_publish,
)


class TestDurationToMinutes:
    def test_minute_passthrough(self):
        assert duration_to_minutes(17, TimeUnit.MINUTE) == 17

    def test_hour_conversion(self):
        assert duration_to_minutes(2, TimeUnit.HOUR) == 120

    def test_second_conversion(self):
        assert duration_to_minutes(120, TimeUnit.SECOND) == pytest.approx(2.0)

    def test_none_value_returns_none(self):
        assert duration_to_minutes(None, TimeUnit.MINUTE) is None


class TestComputeTimeSaving:
    def test_spec_example(self):
        assert compute_time_saving(45, 28) == 17

    def test_new_duration_equal_returns_none(self):
        assert compute_time_saving(30, 30) is None

    def test_new_duration_greater_returns_none(self):
        assert compute_time_saving(20, 25) is None

    def test_missing_input_returns_none(self):
        assert compute_time_saving(None, 10) is None


class TestComputeMonthlyTotal:
    def test_spec_example(self):
        assert compute_monthly_total(17, RepeatPeriod.MONTHLY, 30) == 510

    def test_daily_repeat_scales_by_days_per_month(self):
        result = compute_monthly_total(10, RepeatPeriod.DAILY, 1)
        assert result == pytest.approx(300, rel=0.01)

    def test_missing_repeat_period_returns_none(self):
        assert compute_monthly_total(10, None, 5) is None


class TestComputeChange:
    def test_spec_example_scrap_reduction(self):
        amount, percent = compute_change(4.2, 3.1)
        assert amount == pytest.approx(-1.1)
        assert percent == pytest.approx(-26.19, rel=0.01)

    def test_zero_previous_guards_percent(self):
        amount, percent = compute_change(0, 5)
        assert amount == 5
        assert percent is None

    def test_missing_values_return_none_tuple(self):
        assert compute_change(None, 5) == (None, None)


class TestIsImprovement:
    def test_capacity_increase_is_improvement_when_positive(self):
        assert is_improvement(OtherGainType.CAPACITY_INCREASE, 5) is True
        assert is_improvement(OtherGainType.CAPACITY_INCREASE, -5) is False

    def test_scrap_reduction_is_improvement_when_negative(self):
        assert is_improvement(OtherGainType.SCRAP_REDUCTION, -1.1) is True
        assert is_improvement(OtherGainType.SCRAP_REDUCTION, 1.1) is False

    def test_none_change_returns_none(self):
        assert is_improvement(OtherGainType.SCRAP_REDUCTION, None) is None


class TestValidateForPublish:
    VALID = {
        "title": "Başlık", "foreman_ids": ["id"], "plant_id": "id", "work_date": "2026-01-01",
        "work_type": "smed", "summary": "Özet", "problem_description": "Problem", "solution_description": "Çözüm",
    }

    def test_complete_payload_has_no_errors(self):
        assert validate_for_publish(self.VALID) == {}

    def test_missing_title_is_reported(self):
        data = {**self.VALID, "title": ""}
        assert "title" in validate_for_publish(data)

    def test_missing_foremen_is_reported(self):
        data = {**self.VALID, "foreman_ids": []}
        assert "foreman_ids" in validate_for_publish(data)

    def test_other_work_type_requires_note(self):
        data = {**self.VALID, "work_type": "other"}
        errors = validate_for_publish(data)
        assert "work_type_other_note" in errors

    def test_other_work_type_with_note_is_valid(self):
        data = {**self.VALID, "work_type": "other", "work_type_other_note": "Açıklama"}
        assert validate_for_publish(data) == {}

    def test_date_range_end_before_start_is_reported(self):
        data = {**self.VALID, "work_date": "2026-02-01", "work_date_end": "2026-01-01"}
        assert "work_date_end" in validate_for_publish(data)
