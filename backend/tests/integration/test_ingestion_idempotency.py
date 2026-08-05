
from collections.abc import Iterator
from datetime import date, datetime, timezone

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.enums import DataQualityStatus, SourceSystem
from app.models.foreman import Chief, Foreman, ForemanAssignment
from app.models.integration import DataQualityIssue
from app.models.kpi import Kpi
from app.models.organization import Plant, Shift
from app.models.performance import PerformanceRecord, PerformanceScore
from app.services.ingestion import run_ingestion
from app.services.providers.base import PerformanceDataProvider, RawPerformanceRecord


class _FixedProvider(PerformanceDataProvider):
    source_system = SourceSystem.SYNTHETIC

    def __init__(self, records: list[RawPerformanceRecord]) -> None:
        self._records = records

    def fetch(self, date_from, date_to, plant_codes=None) -> Iterator[RawPerformanceRecord]:
        yield from self._records


def _delete_test_records(db, source_record_ids: list[str]) -> None:
    record_ids = list(
        db.scalars(select(PerformanceRecord.id).where(PerformanceRecord.source_record_id.in_(source_record_ids)))
    )
    if record_ids:
        db.execute(DataQualityIssue.__table__.delete().where(DataQualityIssue.performance_record_id.in_(record_ids)))
        db.execute(PerformanceScore.__table__.delete().where(PerformanceScore.performance_record_id.in_(record_ids)))
        db.execute(PerformanceRecord.__table__.delete().where(PerformanceRecord.id.in_(record_ids)))
    for source_id in source_record_ids:
        db.execute(
            DataQualityIssue.__table__.delete().where(
                DataQualityIssue.performance_record_id.is_(None),
                DataQualityIssue.description.ilike(f"%{source_id}%"),
            )
        )
    db.commit()


def _pick_existing_entities(db):
    assignment = db.scalar(select(ForemanAssignment).limit(1))
    plant = db.get(Plant, assignment.plant_id)
    chief = db.get(Chief, assignment.chief_id)
    shift = db.get(Shift, assignment.shift_id)
    foreman = db.get(Foreman, assignment.foreman_id)
    kpi = db.scalar(select(Kpi).where(Kpi.code == "PLANA_UYUM"))
    return plant, chief, shift, foreman, kpi


class TestIngestionIdempotency:
    def test_duplicate_natural_key_is_skipped_not_duplicated(self):
        db = SessionLocal()
        try:
            plant, chief, shift, foreman, kpi = _pick_existing_entities(db)
            unique_date = date(2019, 3, 3)

            def make_record(source_id: str) -> RawPerformanceRecord:
                return RawPerformanceRecord(
                    source_record_id=source_id,
                    performance_date=unique_date,
                    plant_code=plant.code,
                    chief_employee_number=chief.employee_number,
                    shift_code=shift.code,
                    foreman_employee_number=foreman.employee_number,
                    kpi_code=kpi.code,
                    actual_value=88.0,
                    unit=kpi.unit,
                    source_updated_at=datetime.now(timezone.utc),
                )

            provider = _FixedProvider([make_record("TEST-DUP-1"), make_record("TEST-DUP-2")])
            run = run_ingestion(db, provider, unique_date, unique_date)

            assert run.processed_count == 2
            assert run.success_count == 1
            assert run.skipped_count == 1

            count = db.scalar(
                select(func.count()).select_from(PerformanceRecord).where(
                    PerformanceRecord.foreman_id == foreman.id,
                    PerformanceRecord.kpi_id == kpi.id,
                    PerformanceRecord.chief_id == chief.id,
                    PerformanceRecord.shift_id == shift.id,
                    PerformanceRecord.performance_date == unique_date,
                )
            )
            assert count == 1
        finally:
            db.rollback()
            _delete_test_records(db, ["TEST-DUP-1", "TEST-DUP-2"])
            db.close()

    def test_missing_actual_value_marks_status_missing(self):
        db = SessionLocal()
        try:
            plant, chief, shift, foreman, kpi = _pick_existing_entities(db)
            unique_date = date(2019, 3, 4)

            record = RawPerformanceRecord(
                source_record_id="TEST-MISSING-1",
                performance_date=unique_date,
                plant_code=plant.code, chief_employee_number=chief.employee_number,
                shift_code=shift.code,
                foreman_employee_number=foreman.employee_number, kpi_code=kpi.code,
                actual_value=None, unit=kpi.unit, source_updated_at=datetime.now(timezone.utc),
            )
            provider = _FixedProvider([record])
            run_ingestion(db, provider, unique_date, unique_date)

            saved = db.scalar(select(PerformanceRecord).where(PerformanceRecord.source_record_id == "TEST-MISSING-1"))
            assert saved is not None
            assert saved.data_quality_status == DataQualityStatus.MISSING
        finally:
            db.rollback()
            _delete_test_records(db, ["TEST-MISSING-1"])
            db.close()
