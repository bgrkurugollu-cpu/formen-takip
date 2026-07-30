
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.enums import DataQualityStatus, IntegrationStatus
from app.models.foreman import Chief, Foreman
from app.models.integration import DataQualityIssue, IntegrationRun
from app.models.kpi import Kpi, KpiCalculationRule, KpiTarget
from app.models.organization import Plant, Shift
from app.models.performance import PerformanceRecord, PerformanceScore
from app.services.kpi_engine import CalculationRuleParams, calculate_score
from app.services.providers.base import PerformanceDataProvider, RawPerformanceRecord
from app.services.target_resolver import NoTargetFoundError, resolve_target

BATCH_SIZE = 1000


class _Lookups:
    def __init__(self, db: Session) -> None:
        self.plants = {p.code: p for p in db.scalars(select(Plant))}
        self.chiefs = {c.employee_number: c for c in db.scalars(select(Chief))}
        self.shifts = {s.code: s for s in db.scalars(select(Shift))}
        self.foremen = {f.employee_number: f for f in db.scalars(select(Foreman))}
        self.kpis = {k.code: k for k in db.scalars(select(Kpi))}

        self.calculation_rules: dict[str, KpiCalculationRule] = {}
        for rule in db.scalars(select(KpiCalculationRule).where(KpiCalculationRule.is_active.is_(True))):
            kpi = next((k for k in self.kpis.values() if k.id == rule.kpi_id), None)
            if kpi:
                self.calculation_rules[kpi.code] = rule

        self.targets_by_kpi: dict[uuid.UUID, list[KpiTarget]] = {}
        for target in db.scalars(select(KpiTarget).where(KpiTarget.is_active.is_(True))):
            self.targets_by_kpi.setdefault(target.kpi_id, []).append(target)


_ISSUE_DESCRIPTIONS = {
    DataQualityStatus.MISSING: "Gerçekleşen değer kaynaktan gelmedi (boş).",
    DataQualityStatus.INVALID: "Gerçekleşen değer KPI için tanımlı geçerli aralığın dışında.",
    DataQualityStatus.NEEDS_SOURCE_CORRECTION: "Bu KPI/tarih/kapsam için geçerli bir hedef bulunamadı — kaynak sistemde düzeltilmesi gerekiyor.",
    DataQualityStatus.DUPLICATE: "Aynı formen/KPI/şef/vardiya/tarih için zaten işlenmiş bir kayıtla çakışıyor (doğal anahtar tekrarı).",
}


def _issue_description(status: DataQualityStatus, source_record_id: str) -> str:
    base = _ISSUE_DESCRIPTIONS.get(status, "Veri kalitesi sorunu tespit edildi.")
    return f"{base} (kaynak kayıt: {source_record_id})"


def run_ingestion(
    db: Session,
    provider: PerformanceDataProvider,
    date_from: date,
    date_to: date,
    plant_codes: list[str] | None = None,
) -> IntegrationRun:
    run = IntegrationRun(
        source_system=provider.source_system,
        started_at=datetime.now(timezone.utc),
        status=IntegrationStatus.RUNNING,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    lookups = _Lookups(db)

    processed = success = errors = skipped = 0
    record_batch: list[dict] = []
    score_batch: list[dict] = []
    quality_meta_batch: list[dict] = []

    def flush() -> None:
        nonlocal record_batch, score_batch, quality_meta_batch, success, skipped
        if not record_batch:
            return
        stmt = pg_insert(PerformanceRecord.__table__).values(record_batch)
        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_perf_record_natural_key"
        ).returning(PerformanceRecord.__table__.c.id)
        inserted_ids = {row[0] for row in db.execute(stmt)}

        skipped += len(record_batch) - len(inserted_ids)
        success += len(inserted_ids)

        filtered_scores = [s for s in score_batch if s["performance_record_id"] in inserted_ids]
        if filtered_scores:
            score_stmt = pg_insert(PerformanceScore.__table__).values(filtered_scores)
            score_stmt = score_stmt.on_conflict_do_nothing(index_elements=["performance_record_id"])
            db.execute(score_stmt)

        issue_rows = []
        now = datetime.now(timezone.utc)
        for meta in quality_meta_batch:
            if meta["id"] in inserted_ids:
                if meta["status"] != DataQualityStatus.COMPLETE:
                    issue_rows.append(
                        {
                            "id": uuid.uuid4(),
                            "performance_record_id": meta["id"],
                            "issue_type": meta["status"],
                            "description": _issue_description(meta["status"], meta["source_record_id"]),
                            "detected_at": now,
                            "status": "open",
                            "created_at": now,
                            "updated_at": now,
                        }
                    )
            else:
                issue_rows.append(
                    {
                        "id": uuid.uuid4(),
                        "performance_record_id": None,
                        "issue_type": DataQualityStatus.DUPLICATE,
                        "description": _issue_description(DataQualityStatus.DUPLICATE, meta["source_record_id"]),
                        "detected_at": now,
                        "status": "open",
                        "created_at": now,
                        "updated_at": now,
                    }
                )
        if issue_rows:
            db.execute(pg_insert(DataQualityIssue.__table__).values(issue_rows))

        db.commit()
        record_batch = []
        score_batch = []
        quality_meta_batch = []

    for raw in provider.fetch(date_from, date_to, plant_codes):
        processed += 1
        try:
            plant = lookups.plants[raw.plant_code]
            chief = lookups.chiefs[raw.chief_employee_number]
            shift = lookups.shifts[raw.shift_code]
            foreman = lookups.foremen[raw.foreman_employee_number]
            kpi = lookups.kpis[raw.kpi_code]
        except KeyError:
            errors += 1
            continue

        record_id = uuid.uuid4()
        status = DataQualityStatus.COMPLETE
        target_value = raw.target_value

        if raw.actual_value is None:
            status = DataQualityStatus.MISSING
        elif raw.actual_value < float(kpi.min_valid_value) or raw.actual_value > float(kpi.max_valid_value):
            status = DataQualityStatus.INVALID

        if status == DataQualityStatus.COMPLETE and target_value is None:
            try:
                resolved = resolve_target(
                    lookups.targets_by_kpi.get(kpi.id, []),
                    raw.performance_date,
                    foreman.id,
                    chief.id,
                    plant.id,
                )
                target_value = resolved.target_value
            except NoTargetFoundError:
                status = DataQualityStatus.NEEDS_SOURCE_CORRECTION

        record_batch.append(
            {
                "id": record_id,
                "source_system": provider.source_system,
                "source_record_id": raw.source_record_id,
                "integration_run_id": run.id,
                "performance_date": raw.performance_date,
                "plant_id": plant.id,
                "chief_id": chief.id,
                "shift_id": shift.id,
                "foreman_id": foreman.id,
                "kpi_id": kpi.id,
                "target_value": target_value,
                "actual_value": raw.actual_value,
                "numerator_value": raw.numerator_value,
                "denominator_value": raw.denominator_value,
                "unit": raw.unit,
                "data_quality_status": status,
                "source_updated_at": raw.source_updated_at,
                "imported_at": datetime.now(timezone.utc),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        )
        quality_meta_batch.append(
            {"id": record_id, "status": status, "source_record_id": raw.source_record_id}
        )

        if status == DataQualityStatus.COMPLETE and target_value is not None:
            rule = lookups.calculation_rules.get(kpi.code)
            if rule is not None:
                params = CalculationRuleParams(
                    calculation_type=rule.calculation_type,
                    min_score=float(kpi.min_score),
                    max_score=float(kpi.max_score),
                    **rule.parameters,
                )
                score = calculate_score(float(raw.actual_value), float(target_value), params)
                weight = float(kpi.weight)
                score_batch.append(
                    {
                        "id": uuid.uuid4(),
                        "performance_record_id": record_id,
                        "calculation_rule_id": rule.id,
                        "raw_score": score.raw_score,
                        "capped_score": score.capped_score,
                        "kpi_weight": weight,
                        "weighted_contribution": score.capped_score * (weight / 100.0),
                        "calculation_version": rule.version,
                        "calculated_at": datetime.now(timezone.utc),
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    }
                )

        if len(record_batch) >= BATCH_SIZE:
            flush()

    flush()

    run.finished_at = datetime.now(timezone.utc)
    run.processed_count = processed
    run.success_count = success
    run.error_count = errors
    run.skipped_count = skipped
    run.status = IntegrationStatus.SUCCESS if errors == 0 else IntegrationStatus.PARTIAL_SUCCESS
    db.commit()
    db.refresh(run)
    return run


def backfill_data_quality_issues(db: Session, batch_size: int = 2000) -> int:
    existing_ids = {
        row for row in db.scalars(
            select(DataQualityIssue.performance_record_id).where(DataQualityIssue.performance_record_id.isnot(None))
        )
    }

    query = select(
        PerformanceRecord.id, PerformanceRecord.data_quality_status, PerformanceRecord.source_record_id
    ).where(PerformanceRecord.data_quality_status != DataQualityStatus.COMPLETE)

    now = datetime.now(timezone.utc)
    to_insert: list[dict] = []
    total = 0
    for rec_id, status, source_record_id in db.execute(query):
        if rec_id in existing_ids:
            continue
        to_insert.append(
            {
                "id": uuid.uuid4(),
                "performance_record_id": rec_id,
                "issue_type": status,
                "description": _issue_description(status, source_record_id),
                "detected_at": now,
                "status": "open",
                "created_at": now,
                "updated_at": now,
            }
        )
        if len(to_insert) >= batch_size:
            db.execute(pg_insert(DataQualityIssue.__table__).values(to_insert))
            db.commit()
            total += len(to_insert)
            to_insert = []

    if to_insert:
        db.execute(pg_insert(DataQualityIssue.__table__).values(to_insert))
        db.commit()
        total += len(to_insert)

    return total
