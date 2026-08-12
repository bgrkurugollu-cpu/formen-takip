from datetime import date, datetime, time

from app.services.shift_utils import resolve_production_date, shift_crosses_midnight


class TestShiftCrossesMidnight:
    def test_night_shift_crosses(self):
        assert shift_crosses_midnight(time(22, 0), time(6, 0)) is True

    def test_day_shift_does_not_cross(self):
        assert shift_crosses_midnight(time(8, 0), time(16, 0)) is False

    def test_shift_ending_exactly_at_midnight_crosses(self):
        assert shift_crosses_midnight(time(16, 0), time(0, 0)) is True


class TestResolveProductionDate:
    def test_non_crossing_shift_uses_calendar_date(self):
        dt = datetime(2026, 3, 15, 10, 30)
        result = resolve_production_date(dt, time(8, 0), time(16, 0))
        assert result == date(2026, 3, 15)

    def test_night_shift_early_morning_belongs_to_previous_day(self):
        dt = datetime(2026, 3, 15, 3, 0)
        result = resolve_production_date(dt, time(0, 0), time(8, 0))
        assert result == date(2026, 3, 15)

    def test_crossing_shift_after_midnight_belongs_to_previous_evening(self):
        dt = datetime(2026, 3, 15, 2, 0)
        result = resolve_production_date(dt, time(22, 0), time(6, 0))
        assert result == date(2026, 3, 14)

    def test_crossing_shift_before_midnight_belongs_to_same_day(self):
        dt = datetime(2026, 3, 15, 23, 0)
        result = resolve_production_date(dt, time(22, 0), time(6, 0))
        assert result == date(2026, 3, 15)
