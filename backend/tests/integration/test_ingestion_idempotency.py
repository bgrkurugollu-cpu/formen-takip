
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.enums import DataQualityStatus, SourceSystem
from app.models.foreman import Chief, Foreman, ForemanAssignment
from app.models.integration import DataQualityIssue
from app.models.kpi import Kpi
from app.models.organization import Plant, Shift
from app.models.performance import PerformanceRecord, PerformanceScore
from app.models.production import ProductionRecord
from app.services.ingestion import run_ingestion
from app.services.providers.base import PerformanceDataProvider, RawPerformanceRecord
from app.services.shift_rotation import actual_shift_for_date


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


def _earliest_real_production_date(db):
    return db.scalar(select(func.min(ProductionRecord.production_date)))


def _pick_existing_entities(db):
    earliest_production = _earliest_real_production_date(db)
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
    kpi = db.scalar(select(Kpi).where(Kpi.code == "GSF"))
    as_of = assignment.start_date + timedelta(days=1)
    shift = actual_shift_for_date(as_of, anchor_shift, all_shifts)
    return plant, chief, shift, foreman, kpi, as_of


def _pick_multi_plant_foreman(db):
    earliest_production = _earliest_real_production_date(db)
    foreman_id = db.scalar(
        select(ForemanAssignment.foreman_id)
        .where(
            ForemanAssignment.is_active.is_(True), ForemanAssignment.start_date < earliest_production
        )
        .group_by(ForemanAssignment.foreman_id, ForemanAssignment.chief_id, ForemanAssignment.shift_id)
        .having(func.count(ForemanAssignment.plant_id.distinct()) >= 2)
        .limit(1)
    )
    assignments = list(
        db.scalars(
            select(ForemanAssignment).where(
                ForemanAssignment.foreman_id == foreman_id, ForemanAssignment.is_active.is_(True)
            )
        )
    )
    chief = db.get(Chief, assignments[0].chief_id)
    foreman = db.get(Foreman, foreman_id)
    anchor_shift = db.get(Shift, assignments[0].shift_id)
    all_shifts = list(db.scalars(select(Shift)))
    plants = [db.get(Plant, a.plant_id) for a in assignments[:2]]
    kpi = db.scalar(select(Kpi).where(Kpi.code == "GSF"))
    as_of = assignments[0].start_date + timedelta(days=1)
    shift = actual_shift_for_date(as_of, anchor_shift, all_shifts)
    return plants, chief, shift, foreman, kpi, as_of


def _pick_unassigned_plant(db, foreman_id):
    assigned_plant_ids = set(
        db.scalars(select(ForemanAssignment.plant_id).where(ForemanAssignment.foreman_id == foreman_id))
    )
    return db.scalar(select(Plant).where(Plant.id.notin_(assigned_plant_ids)).limit(1))


def _pick_other_chief(db, exclude_chief_id):
    return db.scalar(select(Chief).where(Chief.id != exclude_chief_id).limit(1))


class TestIngestionIdempotency:
    def test_duplicate_natural_key_is_skipped_not_duplicated(self):
        db = SessionLocal()
        try:
            plant, chief, shift, foreman, kpi, as_of = _pick_existing_entities(db)

            def make_record(source_id: str) -> RawPerformanceRecord:
                return RawPerformanceRecord(
                    source_record_id=source_id,
                    performance_date=as_of,
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
            run = run_ingestion(db, provider, as_of, as_of)

            assert run.processed_count == 2
            assert run.success_count == 1
            assert run.skipped_count == 1

            count = db.scalar(
                select(func.count()).select_from(PerformanceRecord).where(
                    PerformanceRecord.foreman_id == foreman.id,
                    PerformanceRecord.kpi_id == kpi.id,
                    PerformanceRecord.chief_id == chief.id,
                    PerformanceRecord.shift_id == shift.id,
                    PerformanceRecord.performance_date == as_of,
                )
            )
            assert count == 1
        finally:
            db.rollback()
            _delete_test_records(db, ["TEST-DUP-1", "TEST-DUP-2"])
            db.close()

    def test_multi_plant_same_foreman_kpi_shift_date_is_not_a_duplicate(self):
        db = SessionLocal()
        try:
            plants, chief, shift, foreman, kpi, as_of = _pick_multi_plant_foreman(db)

            def make_record(source_id: str, plant: Plant) -> RawPerformanceRecord:
                return RawPerformanceRecord(
                    source_record_id=source_id,
                    performance_date=as_of,
                    plant_code=plant.code,
                    chief_employee_number=chief.employee_number,
                    shift_code=shift.code,
                    foreman_employee_number=foreman.employee_number,
                    kpi_code=kpi.code,
                    actual_value=88.0,
                    unit=kpi.unit,
                    source_updated_at=datetime.now(timezone.utc),
                )

            provider = _FixedProvider(
                [
                    make_record("TEST-MULTIPLANT-1", plants[0]),
                    make_record("TEST-MULTIPLANT-2", plants[1]),
                ]
            )
            run = run_ingestion(db, provider, as_of, as_of)

            assert run.processed_count == 2
            assert run.success_count == 2
            assert run.skipped_count == 0

            count = db.scalar(
                select(func.count()).select_from(PerformanceRecord).where(
                    PerformanceRecord.foreman_id == foreman.id,
                    PerformanceRecord.kpi_id == kpi.id,
                    PerformanceRecord.chief_id == chief.id,
                    PerformanceRecord.shift_id == shift.id,
                    PerformanceRecord.performance_date == as_of,
                )
            )
            assert count == 2
        finally:
            db.rollback()
            _delete_test_records(db, ["TEST-MULTIPLANT-1", "TEST-MULTIPLANT-2"])
            db.close()

    def test_missing_actual_value_marks_status_missing(self):
        db = SessionLocal()
        try:
            plant, chief, shift, foreman, kpi, as_of = _pick_existing_entities(db)

            record = RawPerformanceRecord(
                source_record_id="TEST-MISSING-1",
                performance_date=as_of,
                plant_code=plant.code, chief_employee_number=chief.employee_number,
                shift_code=shift.code,
                foreman_employee_number=foreman.employee_number, kpi_code=kpi.code,
                actual_value=None, unit=kpi.unit, source_updated_at=datetime.now(timezone.utc),
            )
            provider = _FixedProvider([record])
            run_ingestion(db, provider, as_of, as_of)

            saved = db.scalar(select(PerformanceRecord).where(PerformanceRecord.source_record_id == "TEST-MISSING-1"))
            assert saved is not None
            assert saved.data_quality_status == DataQualityStatus.MISSING
        finally:
            db.rollback()
            _delete_test_records(db, ["TEST-MISSING-1"])
            db.close()

    def test_foreman_not_assigned_to_plant_is_marked_suspicious(self):
        db = SessionLocal()
        try:
            plant, chief, shift, foreman, kpi, as_of = _pick_existing_entities(db)
            other_plant = _pick_unassigned_plant(db, foreman.id)
            other_chief = db.get(Chief, other_plant.chief_id)

            record = RawPerformanceRecord(
                source_record_id="TEST-UNASSIGNED-1",
                performance_date=as_of,
                plant_code=other_plant.code,
                chief_employee_number=other_chief.employee_number,
                shift_code=shift.code,
                foreman_employee_number=foreman.employee_number,
                kpi_code=kpi.code,
                actual_value=88.0, unit=kpi.unit, source_updated_at=datetime.now(timezone.utc),
            )
            provider = _FixedProvider([record])
            run = run_ingestion(db, provider, as_of, as_of)

            assert run.success_count == 1
            saved = db.scalar(
                select(PerformanceRecord).where(PerformanceRecord.source_record_id == "TEST-UNASSIGNED-1")
            )
            assert saved is not None
            assert saved.data_quality_status == DataQualityStatus.SUSPICIOUS
            assert db.scalar(
                select(func.count()).select_from(PerformanceScore).where(
                    PerformanceScore.performance_record_id == saved.id
                )
            ) == 0
        finally:
            db.rollback()
            _delete_test_records(db, ["TEST-UNASSIGNED-1"])
            db.close()

    def test_corrected_replay_updates_existing_record_and_rescores(self):
        db = SessionLocal()
        try:
            plant, chief, shift, foreman, kpi, as_of = _pick_existing_entities(db)

            def make_record(actual_value: float) -> RawPerformanceRecord:
                return RawPerformanceRecord(
                    source_record_id="TEST-CORRECTED-1",
                    performance_date=as_of,
                    plant_code=plant.code, chief_employee_number=chief.employee_number,
                    shift_code=shift.code, foreman_employee_number=foreman.employee_number,
                    kpi_code=kpi.code, actual_value=actual_value, unit=kpi.unit,
                    source_updated_at=datetime.now(timezone.utc),
                )

            first_run = run_ingestion(db, _FixedProvider([make_record(4.0)]), as_of, as_of)
            assert first_run.success_count == 1
            first = db.scalar(select(PerformanceRecord).where(PerformanceRecord.source_record_id == "TEST-CORRECTED-1"))
            first_id = first.id
            first_score = db.scalar(select(PerformanceScore).where(PerformanceScore.performance_record_id == first_id))
            assert first.actual_value == 4.0
            assert first_score is not None
            first_raw_score = first_score.raw_score

            second_run = run_ingestion(db, _FixedProvider([make_record(7.5)]), as_of, as_of)
            assert second_run.success_count == 1
            assert second_run.skipped_count == 0

            db.expire_all()

            count = db.scalar(
                select(func.count()).select_from(PerformanceRecord).where(
                    PerformanceRecord.source_record_id == "TEST-CORRECTED-1"
                )
            )
            assert count == 1

            updated = db.get(PerformanceRecord, first_id)
            assert updated.actual_value == 7.5

            updated_score = db.scalar(select(PerformanceScore).where(PerformanceScore.performance_record_id == first_id))
            assert updated_score is not None
            assert updated_score.raw_score != first_raw_score

            issue = db.scalar(
                select(DataQualityIssue).where(
                    DataQualityIssue.performance_record_id == first_id,
                    DataQualityIssue.issue_type == DataQualityStatus.REPROCESSED,
                )
            )
            assert issue is not None
        finally:
            db.rollback()
            _delete_test_records(db, ["TEST-CORRECTED-1"])
            db.close()

    def test_unchanged_replay_is_idempotent_noop(self):
        db = SessionLocal()
        try:
            plant, chief, shift, foreman, kpi, as_of = _pick_existing_entities(db)

            def make_record() -> RawPerformanceRecord:
                return RawPerformanceRecord(
                    source_record_id="TEST-REPLAY-1",
                    performance_date=as_of,
                    plant_code=plant.code, chief_employee_number=chief.employee_number,
                    shift_code=shift.code, foreman_employee_number=foreman.employee_number,
                    kpi_code=kpi.code, actual_value=5.0, unit=kpi.unit,
                    source_updated_at=None,
                )

            first_run = run_ingestion(db, _FixedProvider([make_record()]), as_of, as_of)
            assert first_run.success_count == 1
            first = db.scalar(select(PerformanceRecord).where(PerformanceRecord.source_record_id == "TEST-REPLAY-1"))
            first_updated_at = first.updated_at

            second_run = run_ingestion(db, _FixedProvider([make_record()]), as_of, as_of)
            assert second_run.success_count == 1
            assert second_run.skipped_count == 0

            count = db.scalar(
                select(func.count()).select_from(PerformanceRecord).where(
                    PerformanceRecord.source_record_id == "TEST-REPLAY-1"
                )
            )
            assert count == 1

            unchanged = db.get(PerformanceRecord, first.id)
            assert unchanged.updated_at == first_updated_at

            duplicate_issue_count = db.scalar(
                select(func.count()).select_from(DataQualityIssue).where(
                    DataQualityIssue.description.ilike("%TEST-REPLAY-1%")
                )
            )
            assert duplicate_issue_count == 0
        finally:
            db.rollback()
            _delete_test_records(db, ["TEST-REPLAY-1"])
            db.close()

    def test_same_source_id_with_different_identity_is_flagged_not_silently_applied(self):
        db = SessionLocal()
        try:
            plant, chief, shift, foreman, kpi, as_of = _pick_existing_entities(db)
            other_date = as_of + timedelta(days=1)

            first = RawPerformanceRecord(
                source_record_id="TEST-IDENTITY-1", performance_date=as_of,
                plant_code=plant.code, chief_employee_number=chief.employee_number,
                shift_code=shift.code, foreman_employee_number=foreman.employee_number,
                kpi_code=kpi.code, actual_value=6.0, unit=kpi.unit,
                source_updated_at=datetime.now(timezone.utc),
            )
            first_run = run_ingestion(db, _FixedProvider([first]), as_of, as_of)
            assert first_run.success_count == 1
            saved = db.scalar(select(PerformanceRecord).where(PerformanceRecord.source_record_id == "TEST-IDENTITY-1"))
            first_id = saved.id

            corrected_identity = RawPerformanceRecord(
                source_record_id="TEST-IDENTITY-1", performance_date=other_date,
                plant_code=plant.code, chief_employee_number=chief.employee_number,
                shift_code=shift.code, foreman_employee_number=foreman.employee_number,
                kpi_code=kpi.code, actual_value=6.0, unit=kpi.unit,
                source_updated_at=datetime.now(timezone.utc),
            )
            second_run = run_ingestion(db, _FixedProvider([corrected_identity]), other_date, other_date)
            assert second_run.skipped_count == 1

            unchanged = db.get(PerformanceRecord, first_id)
            assert unchanged.performance_date == as_of

            issue = db.scalar(
                select(DataQualityIssue).where(
                    DataQualityIssue.issue_type == DataQualityStatus.SUSPICIOUS,
                    DataQualityIssue.description.ilike("%TEST-IDENTITY-1%"),
                )
            )
            assert issue is not None
        finally:
            db.rollback()
            _delete_test_records(db, ["TEST-IDENTITY-1"])
            db.close()

    def test_batch_with_preexisting_source_id_does_not_crash_other_rows(self):
        db = SessionLocal()
        try:
            plant, chief, shift, foreman, kpi, as_of = _pick_existing_entities(db)

            existing = RawPerformanceRecord(
                source_record_id="TEST-BATCH-EXISTING-1", performance_date=as_of,
                plant_code=plant.code, chief_employee_number=chief.employee_number,
                shift_code=shift.code, foreman_employee_number=foreman.employee_number,
                kpi_code=kpi.code, actual_value=3.0, unit=kpi.unit,
                source_updated_at=datetime.now(timezone.utc),
            )
            run_ingestion(db, _FixedProvider([existing]), as_of, as_of)

            corrected = RawPerformanceRecord(
                source_record_id="TEST-BATCH-EXISTING-1", performance_date=as_of,
                plant_code=plant.code, chief_employee_number=chief.employee_number,
                shift_code=shift.code, foreman_employee_number=foreman.employee_number,
                kpi_code=kpi.code, actual_value=9.0, unit=kpi.unit,
                source_updated_at=datetime.now(timezone.utc),
            )
            fresh_ids = [f"TEST-BATCH-FRESH-{i}" for i in range(3)]
            fresh_records = [
                RawPerformanceRecord(
                    source_record_id=sid, performance_date=as_of + timedelta(days=2 + i),
                    plant_code=plant.code, chief_employee_number=chief.employee_number,
                    shift_code=shift.code, foreman_employee_number=foreman.employee_number,
                    kpi_code=kpi.code, actual_value=2.0, unit=kpi.unit,
                    source_updated_at=datetime.now(timezone.utc),
                )
                for i, sid in enumerate(fresh_ids)
            ]

            second_run = run_ingestion(
                db, _FixedProvider([corrected, *fresh_records]), as_of, as_of + timedelta(days=5)
            )

            assert second_run.processed_count == 4
            assert second_run.success_count == 4
            assert second_run.error_count == 0

            for sid in fresh_ids:
                assert db.scalar(select(PerformanceRecord).where(PerformanceRecord.source_record_id == sid)) is not None

            updated = db.scalar(
                select(PerformanceRecord).where(PerformanceRecord.source_record_id == "TEST-BATCH-EXISTING-1")
            )
            assert updated.actual_value == 9.0
        finally:
            db.rollback()
            _delete_test_records(db, ["TEST-BATCH-EXISTING-1", *[f"TEST-BATCH-FRESH-{i}" for i in range(3)]])
            db.close()

    def test_chief_plant_mismatch_is_marked_suspicious_and_uses_real_chief(self):
        db = SessionLocal()
        try:
            plant, chief, shift, foreman, kpi, as_of = _pick_existing_entities(db)
            wrong_chief = _pick_other_chief(db, chief.id)

            record = RawPerformanceRecord(
                source_record_id="TEST-CHIEF-MISMATCH-1",
                performance_date=as_of,
                plant_code=plant.code,
                chief_employee_number=wrong_chief.employee_number,
                shift_code=shift.code,
                foreman_employee_number=foreman.employee_number,
                kpi_code=kpi.code,
                actual_value=88.0, unit=kpi.unit, source_updated_at=datetime.now(timezone.utc),
            )
            provider = _FixedProvider([record])
            run = run_ingestion(db, provider, as_of, as_of)

            assert run.success_count == 1
            saved = db.scalar(
                select(PerformanceRecord).where(PerformanceRecord.source_record_id == "TEST-CHIEF-MISMATCH-1")
            )
            assert saved is not None
            assert saved.data_quality_status == DataQualityStatus.SUSPICIOUS
            assert saved.chief_id == plant.chief_id
            assert saved.chief_id != wrong_chief.id
        finally:
            db.rollback()
            _delete_test_records(db, ["TEST-CHIEF-MISMATCH-1"])
            db.close()
