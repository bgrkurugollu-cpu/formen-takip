import pytest
from sqlalchemy import select

from app.models.anomaly import Anomaly
from app.models.enums import AnomalyType
from app.services.data_providers import get_data_providers
from app.services.tools.definitions import TOOL_REGISTRY, get_tool, list_tool_specs, parse_tool_arguments
from app.services.tools.errors import ToolError, ToolErrorCode


def _sample_anomaly(db_session) -> Anomaly:
    anomaly = db_session.scalars(select(Anomaly).order_by(Anomaly.code)).first()
    assert anomaly is not None, "Testler için önce 'python -m app.cli seed-anomalies' çalıştırılmalı."
    return anomaly


def _run(db_session, name: str, raw: dict) -> dict:
    tool = get_tool(name)
    providers = get_data_providers(db_session)
    args = parse_tool_arguments(tool, raw)
    return tool.handler(db_session, providers, args)


class TestToolRegistry:
    def test_at_least_ten_read_only_tools_registered(self):
        assert len(TOOL_REGISTRY) >= 10
        assert all(t.read_only for t in TOOL_REGISTRY.values())

    def test_tool_specs_have_strict_json_schema_shape(self):
        specs = list_tool_specs()
        assert len(specs) == len(TOOL_REGISTRY)
        for spec in specs:
            fn = spec["function"]
            assert spec["type"] == "function"
            assert fn["strict"] is True
            assert fn["parameters"]["additionalProperties"] is False
            assert set(fn["parameters"]["required"]) == set(fn["parameters"]["properties"].keys())


class TestGetAnomalyDetails:
    def test_success(self, db_session):
        anomaly = _sample_anomaly(db_session)
        result = _run(db_session, "get_anomaly_details", {"anomaly_id": anomaly.code})
        assert result["code"] == anomaly.code
        assert result["kpi_code"] is not None

    def test_unknown_anomaly_raises_validation_error(self, db_session):
        with pytest.raises(ToolError) as exc_info:
            _run(db_session, "get_anomaly_details", {"anomaly_id": "ANM-9999-9999"})
        assert exc_info.value.code == ToolErrorCode.TOOL_VALIDATION_ERROR

    def test_missing_required_parameter_raises(self, db_session):
        with pytest.raises(ToolError) as exc_info:
            _run(db_session, "get_anomaly_details", {})
        assert exc_info.value.code == ToolErrorCode.TOOL_VALIDATION_ERROR


class TestGetKpiHistory:
    def test_success_daily(self, db_session):
        anomaly = _sample_anomaly(db_session)
        result = _run(
            db_session, "get_kpi_history",
            {
                "plant_id": str(anomaly.plant_id), "kpi": str(anomaly.kpi_id),
                "start_date": anomaly.period_start.isoformat(), "end_date": anomaly.period_end.isoformat(),
                "granularity": "daily",
            },
        )
        assert len(result["points"]) == (anomaly.period_end - anomaly.period_start).days + 1

    def test_invalid_plant_raises(self, db_session):
        anomaly = _sample_anomaly(db_session)
        with pytest.raises(ToolError):
            _run(
                db_session, "get_kpi_history",
                {
                    "plant_id": "NOT-A-PLANT", "kpi": str(anomaly.kpi_id),
                    "start_date": "2026-01-01", "end_date": "2026-01-05", "granularity": "daily",
                },
            )

    def test_start_after_end_raises(self, db_session):
        anomaly = _sample_anomaly(db_session)
        with pytest.raises(ToolError) as exc_info:
            _run(
                db_session, "get_kpi_history",
                {
                    "plant_id": str(anomaly.plant_id), "kpi": str(anomaly.kpi_id),
                    "start_date": "2026-02-01", "end_date": "2026-01-01", "granularity": "daily",
                },
            )
        assert exc_info.value.code == ToolErrorCode.TOOL_VALIDATION_ERROR

    def test_date_range_exceeding_max_raises(self, db_session):
        anomaly = _sample_anomaly(db_session)
        with pytest.raises(ToolError) as exc_info:
            _run(
                db_session, "get_kpi_history",
                {
                    "plant_id": str(anomaly.plant_id), "kpi": str(anomaly.kpi_id),
                    "start_date": "2020-01-01", "end_date": "2026-01-01", "granularity": "daily",
                },
            )
        assert exc_info.value.code == ToolErrorCode.TOOL_VALIDATION_ERROR

    def test_weekly_granularity_buckets(self, db_session):
        anomaly = _sample_anomaly(db_session)
        result = _run(
            db_session, "get_kpi_history",
            {
                "plant_id": str(anomaly.plant_id), "kpi": str(anomaly.kpi_id),
                "start_date": anomaly.period_start.isoformat(), "end_date": anomaly.period_end.isoformat(),
                "granularity": "weekly",
            },
        )
        assert len(result["points"]) <= (anomaly.period_end - anomaly.period_start).days + 1


class TestCompareShiftsAndPlants:
    def test_compare_shifts_success(self, db_session):
        anomaly = _sample_anomaly(db_session)
        result = _run(
            db_session, "compare_shifts",
            {
                "plant_id": str(anomaly.plant_id), "kpi": str(anomaly.kpi_id),
                "start_date": anomaly.period_start.isoformat(), "end_date": anomaly.period_end.isoformat(),
            },
        )
        assert "V1" in result["shift_averages"]
        assert result["worst_shift"] in result["shift_averages"]

    def test_compare_plants_rejects_plant_outside_factory(self, db_session):
        anomaly = _sample_anomaly(db_session)
        other_factory = "K2" if _plant_factory_code(db_session, anomaly.plant_id) == "K1" else "K1"
        with pytest.raises(ToolError) as exc_info:
            _run(
                db_session, "compare_plants",
                {
                    "factory": other_factory, "plant_id": str(anomaly.plant_id), "kpi": str(anomaly.kpi_id),
                    "start_date": anomaly.period_start.isoformat(), "end_date": anomaly.period_end.isoformat(),
                },
            )
        assert exc_info.value.code == ToolErrorCode.TOOL_VALIDATION_ERROR

    def test_compare_plants_invalid_factory_raises(self, db_session):
        anomaly = _sample_anomaly(db_session)
        with pytest.raises(ToolError):
            _run(
                db_session, "compare_plants",
                {
                    "factory": "K9", "plant_id": str(anomaly.plant_id), "kpi": str(anomaly.kpi_id),
                    "start_date": "2026-01-01", "end_date": "2026-01-05",
                },
            )


def _plant_factory_code(db_session, plant_id) -> str:
    from app.models.organization import Factory, Plant

    plant = db_session.get(Plant, plant_id)
    factory = db_session.get(Factory, plant.factory_id)
    return factory.code


class TestFindSimilarAnomalies:
    def test_success(self, db_session):
        anomaly = _sample_anomaly(db_session)
        result = _run(db_session, "find_similar_anomalies", {"anomaly_id": anomaly.code, "limit": 3})
        assert result["count"] <= 3
        assert all(c["anomaly_code"] != anomaly.code for c in result["cases"])

    def test_invalid_anomaly_type_raises(self, db_session):
        anomaly = _sample_anomaly(db_session)
        with pytest.raises(ToolError) as exc_info:
            _run(
                db_session, "find_similar_anomalies",
                {"anomaly_id": anomaly.code, "anomaly_type": "not_a_real_type", "limit": 3},
            )
        assert exc_info.value.code == ToolErrorCode.TOOL_VALIDATION_ERROR

    def test_valid_anomaly_type_enum_accepted(self, db_session):
        anomaly = _sample_anomaly(db_session)
        result = _run(
            db_session, "find_similar_anomalies",
            {"anomaly_id": anomaly.code, "anomaly_type": AnomalyType.CHRONIC_ANOMALY.value, "limit": 2},
        )
        assert result["count"] <= 2

    def test_limit_out_of_range_raises(self, db_session):
        anomaly = _sample_anomaly(db_session)
        with pytest.raises(ToolError):
            _run(db_session, "find_similar_anomalies", {"anomaly_id": anomaly.code, "limit": 999})


class TestDowntimeMaintenanceProductTools:
    def test_get_downtime_breakdown(self, db_session):
        anomaly = _sample_anomaly(db_session)
        result = _run(
            db_session, "get_downtime_breakdown",
            {
                "plant_id": str(anomaly.plant_id),
                "start_date": anomaly.period_start.isoformat(), "end_date": anomaly.period_end.isoformat(),
            },
        )
        assert result["total_downtime_minutes"] >= 0

    def test_get_maintenance_signals(self, db_session):
        anomaly = _sample_anomaly(db_session)
        result = _run(
            db_session, "get_maintenance_signals",
            {"plant_id": str(anomaly.plant_id), "start_date": anomaly.period_start.isoformat(), "end_date": anomaly.period_end.isoformat()},
        )
        assert "records" in result

    def test_get_product_mix_shares_sum_to_100(self, db_session):
        anomaly = _sample_anomaly(db_session)
        result = _run(
            db_session, "get_product_mix",
            {"plant_id": str(anomaly.plant_id), "start_date": anomaly.period_start.isoformat(), "end_date": anomaly.period_end.isoformat()},
        )
        total_share = sum(g["share_percent"] for g in result["product_groups"])
        assert total_share == pytest.approx(100.0, abs=0.5)

    def test_get_shift_notes(self, db_session):
        anomaly = _sample_anomaly(db_session)
        result = _run(
            db_session, "get_shift_notes",
            {"plant_id": str(anomaly.plant_id), "start_date": anomaly.period_start.isoformat(), "end_date": anomaly.period_end.isoformat()},
        )
        assert isinstance(result["notes"], list)
