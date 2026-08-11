from datetime import date
from uuid import uuid4

import pytest

from app.services.shift_analysis import (
    ForemanCellStat,
    ForemanShiftCell,
    ForemanShiftRow,
    ShiftAnomalyThresholds,
    _build_matrix_insight,
    _compare_pair,
    _extreme_pair,
    _is_consistent_pattern,
    _shift_diff_classification,
    _week_index,
    classify_diff_level,
    month_label,
    previous_completed_month,
)


def make_stat(avg_actual: float, record_count: int = 10, week_indices: list[int] | None = None) -> ForemanCellStat:
    return ForemanCellStat(
        foreman_id=uuid4(), avg_actual=avg_actual, record_count=record_count,
        week_indices=week_indices if week_indices is not None else [0, 1],
    )


class _StubShift:
    """`_build_matrix_insight` yalnızca `.id` ve `.name`'e ihtiyaç duyar — gerçek `Shift` ORM
    modelini (Time sütunları, DB bağlantısı gerektirmeyen) kurmak yerine hafif bir stub yeterli."""

    def __init__(self, name: str):
        self.id = uuid4()
        self.name = name


def make_shift(name: str) -> _StubShift:
    return _StubShift(name)


class TestPreviousCompletedMonth:
    def test_mid_year(self):
        start, end = previous_completed_month(date(2026, 8, 7))
        assert start == date(2026, 7, 1)
        assert end == date(2026, 7, 31)

    def test_january_crosses_year_boundary(self):
        start, end = previous_completed_month(date(2026, 1, 15))
        assert start == date(2025, 12, 1)
        assert end == date(2025, 12, 31)

    def test_first_of_month(self):
        start, end = previous_completed_month(date(2026, 3, 1))
        assert start == date(2026, 2, 1)
        assert end == date(2026, 2, 28)


class TestMonthLabel:
    def test_turkish_label(self):
        assert month_label(date(2026, 7, 31)) == "Temmuz 2026"

    def test_december(self):
        assert month_label(date(2025, 12, 1)) == "Aralık 2025"


class TestWeekIndex:
    def test_epoch_is_week_zero(self):
        assert _week_index(date(2024, 1, 1)) == 0

    def test_seven_days_later_is_week_one(self):
        assert _week_index(date(2024, 1, 8)) == 1

    def test_day_before_epoch_is_negative(self):
        assert _week_index(date(2023, 12, 31)) == -1


class TestComparePair:
    def test_high_severity_above_15_percent(self):
        a, b = make_stat(92.0), make_stat(108.0)
        result = _compare_pair(a, b, higher_is_better=True, thresholds=ShiftAnomalyThresholds())
        assert result is not None
        assert result.severity == "high"
        assert result.better.avg_actual == 108.0
        assert result.worse.avg_actual == 92.0
        assert result.pct_diff == pytest.approx(16 / 100 * 100, rel=1e-3)

    def test_medium_severity_between_8_and_15_percent(self):
        a, b = make_stat(100.0), make_stat(110.0)
        result = _compare_pair(a, b, higher_is_better=True, thresholds=ShiftAnomalyThresholds())
        assert result is not None
        assert result.severity == "medium"

    def test_below_threshold_returns_none(self):
        a, b = make_stat(100.0), make_stat(103.0)
        result = _compare_pair(a, b, higher_is_better=True, thresholds=ShiftAnomalyThresholds())
        assert result is None

    def test_lower_is_better_direction(self):
        # Iskarta gibi düşük-iyi bir KPI'da düşük değerli taraf "better" olmalı.
        a, b = make_stat(5.0), make_stat(8.0)
        result = _compare_pair(a, b, higher_is_better=False, thresholds=ShiftAnomalyThresholds())
        assert result is not None
        assert result.better.avg_actual == 5.0
        assert result.worse.avg_actual == 8.0

    def test_insufficient_records_returns_none(self):
        a = make_stat(92.0, record_count=2)
        b = make_stat(108.0, record_count=10)
        result = _compare_pair(a, b, higher_is_better=True, thresholds=ShiftAnomalyThresholds())
        assert result is None

    def test_both_zero_returns_none(self):
        a, b = make_stat(0.0), make_stat(0.0)
        result = _compare_pair(a, b, higher_is_better=True, thresholds=ShiftAnomalyThresholds())
        assert result is None

    def test_near_zero_ideal_value_does_not_explode_percentage(self):
        # Ağır Gitme gibi "düşük değer iyi" bir KPI'da ideal değer sıfıra çok yakındır (ör. 0.01
        # vs 4.04) — küçük tarafı taban alan eski formül burada binlerce yüzdelik anlamsız bir
        # fark üretiyordu. Ortalamayı taban alan yeni formül kararlı kalmalı.
        a, b = make_stat(0.01), make_stat(4.04)
        result = _compare_pair(a, b, higher_is_better=False, thresholds=ShiftAnomalyThresholds())
        assert result is not None
        assert result.pct_diff == pytest.approx(4.03 / 2.025 * 100, rel=1e-3)
        assert result.pct_diff < 250

    def test_tiny_absolute_gap_near_zero_scale_is_filtered_even_if_pct_high(self):
        # İki taraf da neredeyse sıfırsa (ör. %0.04 vs %0.43 Ağır Gitme) yüzdesel fark kolayca
        # eşiği geçer ama mutlak fark (0.39 puan) yönetim için önemsizdir — min_abs_diff_points
        # bunu filtrelemeli.
        a, b = make_stat(0.04), make_stat(0.43)
        result = _compare_pair(a, b, higher_is_better=False, thresholds=ShiftAnomalyThresholds())
        assert result is None

    def test_custom_thresholds(self):
        a, b = make_stat(100.0), make_stat(105.0)
        strict = ShiftAnomalyThresholds(medium_pct=3.0, high_pct=10.0)
        result = _compare_pair(a, b, higher_is_better=True, thresholds=strict)
        assert result is not None
        assert result.severity == "medium"


class TestExtremePair:
    """Bir hücrede normalde tam 2 formen olur, ama personel değişikliği aynı aya denk gelirse
    3+ formen görülebilir — seçim kayıt SAYISINA göre değil, en uç DEĞERE göre yapılmalı
    (bkz. shift_analysis.py::_extreme_pair docstring'i)."""

    def test_exactly_two_candidates_returns_both(self):
        a, b = make_stat(90.0), make_stat(110.0)
        result = _extreme_pair([a, b], ShiftAnomalyThresholds())
        assert result is not None
        assert {result[0].foreman_id, result[1].foreman_id} == {a.foreman_id, b.foreman_id}

    def test_three_candidates_picks_true_extremes_not_highest_record_count(self):
        # En çok kaydı olan (30) orta değerli — eski "kayıt sayısına göre ilk iki" davranışı
        # bunu ve en düşük değerlisini (mid) seçip asıl en büyük farkı (low vs high) kaçırırdı.
        low = make_stat(70.0, record_count=10)
        mid = make_stat(95.0, record_count=30)
        high = make_stat(120.0, record_count=10)
        result = _extreme_pair([low, mid, high], ShiftAnomalyThresholds())
        assert result is not None
        assert {result[0].foreman_id, result[1].foreman_id} == {low.foreman_id, high.foreman_id}

    def test_candidate_with_too_few_records_is_excluded_even_if_most_extreme(self):
        # `low` en uç değere sahip ama tek başına anlamlı sayılamayacak kadar az kaydı var
        # (ör. geçici/tek günlük yedek formen) — dahil edilirse yanıltıcı bir "anomali" doğardı.
        low = make_stat(10.0, record_count=1)
        mid_a = make_stat(90.0, record_count=10)
        mid_b = make_stat(110.0, record_count=10)
        result = _extreme_pair([low, mid_a, mid_b], ShiftAnomalyThresholds())
        assert result is not None
        assert {result[0].foreman_id, result[1].foreman_id} == {mid_a.foreman_id, mid_b.foreman_id}

    def test_fewer_than_two_qualifying_candidates_returns_none(self):
        only_one_qualifies = make_stat(90.0, record_count=10)
        too_few_records = make_stat(110.0, record_count=1)
        result = _extreme_pair([only_one_qualifies, too_few_records], ShiftAnomalyThresholds())
        assert result is None

    def test_empty_list_returns_none(self):
        assert _extreme_pair([], ShiftAnomalyThresholds()) is None


class TestIsConsistentPattern:
    def test_non_overlapping_ranges_is_consistent(self):
        better_id, worse_id = uuid4(), uuid4()
        points = [
            {"foreman_id": better_id, "avg_actual": 105.0},
            {"foreman_id": better_id, "avg_actual": 110.0},
            {"foreman_id": worse_id, "avg_actual": 90.0},
            {"foreman_id": worse_id, "avg_actual": 95.0},
        ]
        assert _is_consistent_pattern(points, better_id, worse_id, higher_is_better=True) is True

    def test_overlapping_ranges_is_not_consistent(self):
        better_id, worse_id = uuid4(), uuid4()
        points = [
            {"foreman_id": better_id, "avg_actual": 105.0},
            {"foreman_id": better_id, "avg_actual": 80.0},
            {"foreman_id": worse_id, "avg_actual": 90.0},
            {"foreman_id": worse_id, "avg_actual": 95.0},
        ]
        assert _is_consistent_pattern(points, better_id, worse_id, higher_is_better=True) is False

    def test_missing_side_is_not_consistent(self):
        better_id, worse_id = uuid4(), uuid4()
        points = [{"foreman_id": better_id, "avg_actual": 105.0}]
        assert _is_consistent_pattern(points, better_id, worse_id, higher_is_better=True) is False

    def test_lower_is_better_direction(self):
        better_id, worse_id = uuid4(), uuid4()
        points = [
            {"foreman_id": better_id, "avg_actual": 4.0},
            {"foreman_id": better_id, "avg_actual": 5.0},
            {"foreman_id": worse_id, "avg_actual": 9.0},
            {"foreman_id": worse_id, "avg_actual": 10.0},
        ]
        assert _is_consistent_pattern(points, better_id, worse_id, higher_is_better=False) is True


class TestClassifyDiffLevel:
    """Heatmap sınıflandırması — `_compare_pair` ile aynı normalize edilmiş fark formülünü
    paylaşır ama eşiğin altında kalan hücreleri de (None yerine) "normal" olarak döner."""

    def test_no_data_when_one_side_missing(self):
        a = make_stat(100.0)
        level, abs_diff, pct_diff = classify_diff_level(a, None, ShiftAnomalyThresholds())
        assert level == "no_data"
        assert abs_diff is None and pct_diff is None

    def test_no_data_when_insufficient_records(self):
        a = make_stat(100.0, record_count=1)
        b = make_stat(120.0, record_count=10)
        level, _, _ = classify_diff_level(a, b, ShiftAnomalyThresholds())
        assert level == "no_data"

    def test_normal_below_medium_threshold(self):
        a, b = make_stat(100.0), make_stat(102.0)
        level, abs_diff, _ = classify_diff_level(a, b, ShiftAnomalyThresholds())
        assert level == "normal"
        assert abs_diff == pytest.approx(2.0)

    def test_attention_between_medium_and_high(self):
        a, b = make_stat(100.0), make_stat(110.0)
        level, _, _ = classify_diff_level(a, b, ShiftAnomalyThresholds())
        assert level == "attention"

    def test_significant_between_high_and_critical(self):
        a, b = make_stat(100.0), make_stat(118.0)
        level, _, _ = classify_diff_level(a, b, ShiftAnomalyThresholds())
        assert level == "significant"

    def test_critical_above_critical_threshold(self):
        a, b = make_stat(80.0), make_stat(130.0)
        level, _, _ = classify_diff_level(a, b, ShiftAnomalyThresholds())
        assert level == "critical"

    def test_tiny_absolute_gap_near_zero_scale_is_normal_even_if_pct_high(self):
        # `_compare_pair`'daki aynı davranış (bkz. yukarıdaki eşdeğer test) — heatmap'te kart
        # listesinden farklı olarak None değil "normal" döner, hücre matriste hâlâ görünür.
        a, b = make_stat(0.04), make_stat(0.43)
        level, _, _ = classify_diff_level(a, b, ShiftAnomalyThresholds())
        assert level == "normal"

    def test_both_zero_is_normal(self):
        a, b = make_stat(0.0), make_stat(0.0)
        level, abs_diff, pct_diff = classify_diff_level(a, b, ShiftAnomalyThresholds())
        assert level == "normal"
        assert abs_diff == 0.0 and pct_diff == 0.0


class TestShiftDiffClassification:
    def test_matches_classify_diff_level_magnitude(self):
        t = ShiftAnomalyThresholds()
        assert _shift_diff_classification(100.0, 110.0, t) == "attention"
        assert _shift_diff_classification(100.0, 118.0, t) == "significant"
        assert _shift_diff_classification(80.0, 130.0, t) == "critical"
        assert _shift_diff_classification(100.0, 100.5, t) == "normal"


class TestBuildMatrixInsight:
    def test_single_shift_returns_generic_message(self):
        v1 = make_shift("1. Vardiya")
        row = ForemanShiftRow(
            foreman_id=uuid4(), name="Formen A", employee_number="SCL-V1-001",
            cells={v1.id: ForemanShiftCell(avg_actual=100.0, avg_target=100.0, capped_score=100.0, record_count=10)},
        )
        result = _build_matrix_insight([v1], [row], ShiftAnomalyThresholds())
        assert "yetecek veri" in result

    def test_both_foremen_show_shift_effect(self):
        v1, v2 = make_shift("1. Vardiya"), make_shift("2. Vardiya")
        row_a = ForemanShiftRow(
            foreman_id=uuid4(), name="Formen A", employee_number="A",
            cells={
                v1.id: ForemanShiftCell(110.0, 100.0, 110.0, 10),
                v2.id: ForemanShiftCell(90.0, 100.0, 90.0, 10),
            },
        )
        row_b = ForemanShiftRow(
            foreman_id=uuid4(), name="Formen B", employee_number="B",
            cells={
                v1.id: ForemanShiftCell(108.0, 100.0, 108.0, 10),
                v2.id: ForemanShiftCell(88.0, 100.0, 88.0, 10),
            },
        )
        result = _build_matrix_insight([v1, v2], [row_a, row_b], ShiftAnomalyThresholds())
        assert "vardiya etkisiyle" in result

    def test_only_one_foreman_shows_shift_effect(self):
        v1, v2 = make_shift("1. Vardiya"), make_shift("2. Vardiya")
        row_a = ForemanShiftRow(
            foreman_id=uuid4(), name="Formen A", employee_number="A",
            cells={
                v1.id: ForemanShiftCell(110.0, 100.0, 110.0, 10),
                v2.id: ForemanShiftCell(90.0, 100.0, 90.0, 10),
            },
        )
        row_b = ForemanShiftRow(
            foreman_id=uuid4(), name="Formen B", employee_number="B",
            cells={
                v1.id: ForemanShiftCell(101.0, 100.0, 101.0, 10),
                v2.id: ForemanShiftCell(100.0, 100.0, 100.0, 10),
            },
        )
        result = _build_matrix_insight([v1, v2], [row_a, row_b], ShiftAnomalyThresholds())
        assert "Formen A" in result
        assert "vardiyadan çok Formen A" in result

    def test_cross_foreman_same_shift_effect(self):
        # Formenler kendi içlerinde vardiyalar arasında istikrarlı ama AYNI vardiyada birbirinden
        # belirgin şekilde ayrışıyorlar — sorun formen performansıyla ilişkili, cümlede vardiya
        # adı ("1. Vardiya") tekrar etmeden ("... vardiyasında vardiyasında" gibi) doğal okunmalı.
        v1, v2 = make_shift("1. Vardiya"), make_shift("2. Vardiya")
        row_a = ForemanShiftRow(
            foreman_id=uuid4(), name="Formen A", employee_number="A",
            cells={
                v1.id: ForemanShiftCell(100.0, 100.0, 100.0, 10),
                v2.id: ForemanShiftCell(100.0, 100.0, 100.0, 10),
            },
        )
        row_b = ForemanShiftRow(
            foreman_id=uuid4(), name="Formen B", employee_number="B",
            cells={
                v1.id: ForemanShiftCell(130.0, 100.0, 130.0, 10),
                v2.id: ForemanShiftCell(131.0, 100.0, 131.0, 10),
            },
        )
        result = _build_matrix_insight([v1, v2], [row_a, row_b], ShiftAnomalyThresholds())
        assert "1. Vardiya içinde Formen A ile Formen B arasında" in result
        assert "vardiyasında vardiyasında" not in result
        assert "vardiyadan çok formen performansıyla" in result

    def test_stable_foremen_returns_neutral_message(self):
        v1, v2 = make_shift("1. Vardiya"), make_shift("2. Vardiya")
        row_a = ForemanShiftRow(
            foreman_id=uuid4(), name="Formen A", employee_number="A",
            cells={
                v1.id: ForemanShiftCell(100.0, 100.0, 100.0, 10),
                v2.id: ForemanShiftCell(101.0, 100.0, 101.0, 10),
            },
        )
        row_b = ForemanShiftRow(
            foreman_id=uuid4(), name="Formen B", employee_number="B",
            cells={
                v1.id: ForemanShiftCell(99.0, 100.0, 99.0, 10),
                v2.id: ForemanShiftCell(100.0, 100.0, 100.0, 10),
            },
        )
        result = _build_matrix_insight([v1, v2], [row_a, row_b], ShiftAnomalyThresholds())
        assert "istikrarlı" in result
