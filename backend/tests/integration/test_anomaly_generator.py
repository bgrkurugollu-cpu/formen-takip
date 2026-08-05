import random

import pytest

from app.models.enums import AnomalySeverity, AnomalyType
from app.services.synthetic.anomaly_generator import generate_anomaly_fixtures


class TestGenerateAnomalyFixtures:
    def test_generates_at_least_20_cases(self, db_session):
        cases = generate_anomaly_fixtures(db_session, random.Random(42))
        assert len(cases) >= 20

    def test_codes_are_unique(self, db_session):
        cases = generate_anomaly_fixtures(db_session, random.Random(42))
        codes = [c["code"] for c in cases]
        assert len(codes) == len(set(codes))

    def test_covers_all_required_scenario_types(self, db_session):
        cases = generate_anomaly_fixtures(db_session, random.Random(42))
        types_present = {c["anomaly_type"] for c in cases}
        assert types_present == set(AnomalyType)

    def test_deviation_percent_consistent_with_observed_and_expected(self, db_session):
        cases = generate_anomaly_fixtures(db_session, random.Random(42))
        for c in cases:
            expected = c["expected_value"]
            observed = c["observed_value"]
            implied_deviation = (observed - expected) / expected * 100
            assert implied_deviation == pytest.approx(c["deviation_percent"], abs=1.5)

    def test_affected_days_never_exceeds_total_days(self, db_session):
        cases = generate_anomaly_fixtures(db_session, random.Random(42))
        for c in cases:
            assert c["affected_days"] <= c["total_days"]
            assert c["affected_days"] >= 1

    def test_severity_values_are_valid(self, db_session):
        cases = generate_anomaly_fixtures(db_session, random.Random(42))
        for c in cases:
            assert c["severity"] in set(AnomalySeverity)

    def test_deterministic_for_same_seed(self, db_session):
        first = generate_anomaly_fixtures(db_session, random.Random(42))
        second = generate_anomaly_fixtures(db_session, random.Random(42))
        assert [c["code"] for c in first] == [c["code"] for c in second]
        assert [c["observed_value"] for c in first] == [c["observed_value"] for c in second]

    def test_balanced_across_k1_and_k2(self, db_session):
        from sqlalchemy import select

        from app.models.organization import Factory, Plant

        cases = generate_anomaly_fixtures(db_session, random.Random(42))
        factories_by_plant = {
            p.id: db_session.get(Factory, p.factory_id).code
            for p in db_session.scalars(select(Plant))
        }
        k1_count = sum(1 for c in cases if factories_by_plant.get(c["plant_id"]) == "K1")
        k2_count = sum(1 for c in cases if factories_by_plant.get(c["plant_id"]) == "K2")
        assert k1_count > 0 and k2_count > 0
        assert abs(k1_count - k2_count) <= 4
