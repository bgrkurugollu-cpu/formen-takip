
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.enums import DataQualityStatus, SourceSystem
from app.models.foreman import Chief, Foreman, ForemanAssignment
from app.models.integration import IntegrationRun
from app.models.kpi import Kpi
from app.models.organization import Plant, Shift
from app.models.performance import PerformanceRecord
from app.models.production import ProductionRecord
from app.schemas.common import Filters
from app.services import analytics
from app.services.shift_rotation import actual_shift_for_date


def _pick_entities(db):
    earliest_production = db.scalar(select(func.min(ProductionRecord.production_date)))
    assignment = db.scalar(
        select(ForemanAssignment).where(
            ForemanAssignment.is_active.is_(True), ForemanAssignment.start_date < earliest_production
        ).limit(1)
    )
    plant = db.get(Plant, assignment.plant_id)
    chief = db.get(Chief, assignment.chief_id)
    foreman = db.get(Foreman, assignment.foreman_id)
    anchor_shift = db.get(Shift, assignment.shift_id)
    all_shifts = list(db.scalars(select(Shift)))
    kpi = db.scalar(select(Kpi).where(Kpi.code == "AGIR_GITME"))
    as_of = assignment.start_date + timedelta(days=1)
    shift = actual_shift_for_date(as_of, anchor_shift, all_shifts)
    return plant, chief, shift, foreman, kpi, as_of


def _pick_integration_run_id(db):
    return db.scalar(select(IntegrationRun.id).limit(1))


def _make_record(plant, chief, shift, foreman, kpi, performance_date, actual_value: float, integration_run_id) -> PerformanceRecord:
    now = datetime.now(timezone.utc)
    return PerformanceRecord(
        id=uuid.uuid4(), source_system=SourceSystem.SYNTHETIC,
        source_record_id=f"TEST-AGIRGITME-DISPLAY-{uuid.uuid4().hex[:8]}",
        integration_run_id=integration_run_id, performance_date=performance_date,
        plant_id=plant.id, chief_id=chief.id, shift_id=shift.id, foreman_id=foreman.id, kpi_id=kpi.id,
        target_value=float(kpi.default_target_value), actual_value=actual_value,
        numerator_value=actual_value * 100.0, denominator_value=10000.0, unit=kpi.unit,
        data_quality_status=DataQualityStatus.COMPLETE, source_updated_at=now, imported_at=now,
    )


class TestAgirGitmeDisplayMatchesScoreDirection:

    def test_kpi_breakdown_avg_actual_reflects_absolute_not_net_deviation(self):
        db = SessionLocal()
        record_ids: list = []
        try:
            plant, chief, shift, foreman, kpi, as_of = _pick_entities(db)
            run_id = _pick_integration_run_id(db)
            positive = _make_record(plant, chief, shift, foreman, kpi, as_of, 8.0, run_id)
            negative = _make_record(plant, chief, shift, foreman, kpi, as_of + timedelta(days=1), -8.0, run_id)
            db.add_all([positive, negative])
            db.flush()
            record_ids = [positive.id, negative.id]
            db.commit()

            filters = Filters(
                date_from=as_of, date_to=as_of + timedelta(days=1),
                plant_ids=[plant.id], chief_ids=[chief.id], shift_ids=[shift.id],
                kpi_ids=[kpi.id],
            )
            breakdown = analytics.kpi_breakdown(db, filters, foreman_id=foreman.id)
            entry = next(e for e in breakdown if e["kpi_id"] == kpi.id)

            assert entry["avg_actual"] == 8.0
            assert entry["avg_capped_score"] < 100.0
        finally:
            db.rollback()
            if record_ids:
                db.execute(PerformanceRecord.__table__.delete().where(PerformanceRecord.id.in_(record_ids)))
                db.commit()
            db.close()

    def test_foreman_kpi_values_avg_actual_reflects_absolute_not_net_deviation(self):
        db = SessionLocal()
        record_ids: list = []
        try:
            plant, chief, shift, foreman, kpi, as_of = _pick_entities(db)
            run_id = _pick_integration_run_id(db)
            positive = _make_record(plant, chief, shift, foreman, kpi, as_of, 8.0, run_id)
            negative = _make_record(plant, chief, shift, foreman, kpi, as_of + timedelta(days=1), -8.0, run_id)
            db.add_all([positive, negative])
            db.flush()
            record_ids = [positive.id, negative.id]
            db.commit()

            filters = Filters(
                date_from=as_of, date_to=as_of + timedelta(days=1),
                plant_ids=[plant.id], chief_ids=[chief.id], shift_ids=[shift.id],
                kpi_ids=[kpi.id],
            )
            values = analytics.foreman_kpi_values(db, filters, kpi, reference_target=float(kpi.default_target_value))
            entry = next(v for v in values if v.foreman_id == foreman.id)

            assert entry.avg_actual == 8.0
            assert entry.capped_score < 100.0
        finally:
            db.rollback()
            if record_ids:
                db.execute(PerformanceRecord.__table__.delete().where(PerformanceRecord.id.in_(record_ids)))
                db.commit()
            db.close()
