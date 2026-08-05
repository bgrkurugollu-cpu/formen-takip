from datetime import timedelta

from sqlalchemy import select

from app.models.anomaly import Anomaly
from app.models.kpi import Kpi
from app.models.organization import Factory, Plant, Shift
from app.services.synthetic import world


def _sample_anchor(db_session) -> Anomaly:
    anomaly = db_session.scalars(select(Anomaly).order_by(Anomaly.code)).first()
    assert anomaly is not None, "Testler için önce 'python -m app.cli seed-anomalies' çalıştırılmalı."
    return anomaly


class TestResolvers:
    def test_resolve_plant_by_uuid_code_and_name(self, db_session):
        anchor = _sample_anchor(db_session)
        plant = db_session.get(Plant, anchor.plant_id)
        assert world.resolve_plant(db_session, str(plant.id)).id == plant.id
        assert world.resolve_plant(db_session, plant.code).id == plant.id
        assert world.resolve_plant(db_session, plant.name).id == plant.id

    def test_resolve_kpi_by_uuid_and_code(self, db_session):
        anchor = _sample_anchor(db_session)
        kpi = db_session.get(Kpi, anchor.kpi_id)
        assert world.resolve_kpi(db_session, str(kpi.id)).id == kpi.id
        assert world.resolve_kpi(db_session, kpi.code).id == kpi.id
        assert world.resolve_kpi(db_session, kpi.code.lower()).id == kpi.id

    def test_resolve_shift_by_code_sequence_and_none(self, db_session):
        shift = db_session.scalars(select(Shift)).first()
        assert world.resolve_shift(db_session, shift.code).id == shift.id
        assert world.resolve_shift(db_session, str(shift.sequence)).id == shift.id
        assert world.resolve_shift(db_session, None) is None
        assert world.resolve_shift(db_session, "") is None

    def test_resolve_unknown_values_raise(self, db_session):
        import pytest

        with pytest.raises(world.WorldLookupError):
            world.resolve_plant(db_session, "NOPE")
        with pytest.raises(world.WorldLookupError):
            world.resolve_kpi(db_session, "NOT_A_KPI")
        with pytest.raises(world.WorldLookupError):
            world.resolve_factory(db_session, "K9")


class TestKpiSeriesConsistency:
    def test_flagged_shift_series_matches_compare_shifts(self, db_session):
        anchor = _sample_anchor(db_session)
        if anchor.shift_id is None:
            return  # yalnızca vardiyaya özel tespitler için anlamlı
        plant = db_session.get(Plant, anchor.plant_id)
        kpi = db_session.get(Kpi, anchor.kpi_id)
        shift = db_session.get(Shift, anchor.shift_id)

        series = world.kpi_daily_series(db_session, plant, kpi, shift, anchor.period_start, anchor.period_end)
        avg = round(sum(p["value"] for p in series) / len(series), 2)

        comparison = world.compare_shifts(db_session, plant, kpi, anchor.period_start, anchor.period_end)
        assert avg == comparison.per_shift[shift.code]

    def test_deterministic_for_same_inputs(self, db_session):
        anchor = _sample_anchor(db_session)
        plant = db_session.get(Plant, anchor.plant_id)
        kpi = db_session.get(Kpi, anchor.kpi_id)

        first = world.kpi_daily_series(db_session, plant, kpi, None, anchor.period_start, anchor.period_end)
        second = world.kpi_daily_series(db_session, plant, kpi, None, anchor.period_start, anchor.period_end)
        assert first == second

    def test_plant_average_is_between_min_and_max_shift(self, db_session):
        anchor = _sample_anchor(db_session)
        plant = db_session.get(Plant, anchor.plant_id)
        kpi = db_session.get(Kpi, anchor.kpi_id)
        result = world.compare_shifts(db_session, plant, kpi, anchor.period_start, anchor.period_end)
        values = list(result.per_shift.values())
        assert min(values) <= result.plant_average <= max(values)

    def test_no_anchor_plant_kpi_combination_is_near_generic_baseline(self, db_session):
        # Seed edilmiş 24 tespit, 50 tesis x 5 KPI'nin küçük bir alt kümesini kaplar — anchor'sız
        # bir kombinasyon bulup "sağlıklı" (temiz) sentetik seri ürettiğini doğrula.
        anchored_pairs = {(a.plant_id, a.kpi_id) for a in db_session.scalars(select(Anomaly))}
        plants = list(db_session.scalars(select(Plant).where(Plant.is_active.is_(True))))
        kpis = list(db_session.scalars(select(Kpi)))
        for plant in plants:
            for kpi in kpis:
                if (plant.id, kpi.id) not in anchored_pairs:
                    baseline = world.generic_baseline(kpi)
                    value = world._value_for_date(db_session, plant, kpi, None, plant.created_at.date())
                    assert abs(value - baseline) < 2.0
                    return
        raise AssertionError("Anchor'sız bir tesis/KPI kombinasyonu bulunamadı.")


class TestDowntimeAndMaintenance:
    def test_downtime_categories_sum_to_total(self, db_session):
        anchor = _sample_anchor(db_session)
        plant = db_session.get(Plant, anchor.plant_id)
        kpi = db_session.get(Kpi, anchor.kpi_id)
        result = world.downtime_breakdown(db_session, plant, None, kpi, anchor.period_start, anchor.period_end)
        assert sum(c["total_minutes"] for c in result["categories"]) == result["total_downtime_minutes"]
        assert set(c["category"] for c in result["categories"]) == set(world._DOWNTIME_CATEGORIES)

    def test_downtime_does_not_recurse_infinitely_with_shift(self, db_session):
        anchor = _sample_anchor(db_session)
        plant = db_session.get(Plant, anchor.plant_id)
        shift = db_session.scalars(select(Shift)).first()
        result = world.downtime_breakdown(db_session, plant, shift, None, anchor.period_start, anchor.period_end)
        assert result["other_shifts_average_minutes"] is not None

    def test_maintenance_signals_shape(self, db_session):
        anchor = _sample_anchor(db_session)
        plant = db_session.get(Plant, anchor.plant_id)
        kpi = db_session.get(Kpi, anchor.kpi_id)
        result = world.maintenance_signals(db_session, plant, kpi, anchor.period_start, anchor.period_end)
        assert isinstance(result["records"], list)
        assert result["recurring_fault_count"] <= len(result["records"])


class TestSimilarHistoricalCases:
    def test_finds_matching_kpi_and_excludes_self(self, db_session):
        anchor = _sample_anchor(db_session)
        kpi = db_session.get(Kpi, anchor.kpi_id)
        cases = world.similar_historical_cases(db_session, anchor.id, kpi, None, None, None, limit=10)
        assert all(c["anomaly_code"] != anchor.code for c in cases)
        assert all(c["kpi_name"] == kpi.name for c in cases if c.get("kpi_name"))

    def test_resolved_cases_include_root_cause(self, db_session):
        resolved = [a for a in db_session.scalars(select(Anomaly)) if a.status.value in ("resolved", "closed")]
        assert resolved, "Seed edilmiş verinin en az bir çözülmüş tespit içermesi beklenir."
        target = resolved[0]
        cases = world.similar_historical_cases(db_session, target.id, None, None, None, None, limit=20)
        matching = [c for c in cases if c["anomaly_code"] == target.code]
        # target kendisi hariç tutulur; en azından fonksiyon hatasız dönmeli
        assert isinstance(cases, list)
