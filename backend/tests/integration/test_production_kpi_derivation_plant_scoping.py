
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.enums import SourceSystem
from app.models.foreman import Chief, Foreman, ForemanAssignment
from app.models.organization import Plant, Shift
from app.models.production import ForemanWorkCalendar, Product, ProductionLine, ProductionRecord
from app.services.production_kpi_derivation import derive_raw_performance_records

_TEST_DATE = date(2019, 5, 1)


def _pick_multi_plant_assignments(db):
    foreman_id = db.scalar(
        select(ForemanAssignment.foreman_id)
        .where(ForemanAssignment.is_active.is_(True))
        .group_by(ForemanAssignment.foreman_id)
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
    return assignments[:2]


def _cleanup(db, ids: dict) -> None:
    db.execute(ProductionRecord.__table__.delete().where(ProductionRecord.id.in_(ids["production"])))
    db.execute(ForemanWorkCalendar.__table__.delete().where(ForemanWorkCalendar.id.in_(ids["calendar"])))
    db.commit()


class TestWorkCalendarIsPlantScoped:
    """Formen aynı gün bir tesiste çalışırken diğerinde izinli/devamsız olabilir (bkz.
    `ForemanWorkCalendar`'ın `plant_id` içeren doğal anahtarı) — `derive_raw_performance_records`
    bu ayrımı foreman+tarih değil foreman+tarih+tesis üçlüsüyle yapmalı."""

    def test_absent_at_one_plant_does_not_leak_into_its_production_record(self):
        db = SessionLocal()
        ids = {"production": [], "calendar": []}
        try:
            a1, a2 = _pick_multi_plant_assignments(db)
            chief = db.get(Chief, a1.chief_id)
            shift = db.get(Shift, a1.shift_id)
            foreman = db.get(Foreman, a1.foreman_id)
            plant_working = db.get(Plant, a1.plant_id)
            plant_absent = db.get(Plant, a2.plant_id)

            line_working = db.scalar(select(ProductionLine).where(ProductionLine.plant_id == plant_working.id))
            line_absent = db.scalar(select(ProductionLine).where(ProductionLine.plant_id == plant_absent.id))
            product = db.scalar(select(Product))

            cal_working = ForemanWorkCalendar(
                id=uuid.uuid4(), foreman_id=foreman.id, work_date=_TEST_DATE, plant_id=plant_working.id,
                chief_id=chief.id, shift_id=shift.id, line_id=line_working.id, is_working=True,
            )
            cal_absent = ForemanWorkCalendar(
                id=uuid.uuid4(), foreman_id=foreman.id, work_date=_TEST_DATE, plant_id=plant_absent.id,
                chief_id=chief.id, shift_id=shift.id, line_id=line_absent.id, is_working=False,
            )
            db.add_all([cal_working, cal_absent])
            ids["calendar"] = [cal_working.id, cal_absent.id]

            def make_production(plant, line) -> ProductionRecord:
                pr = ProductionRecord(
                    id=uuid.uuid4(), source_system=SourceSystem.SYNTHETIC,
                    source_record_id=f"TEST-PKS-{plant.code}-{uuid.uuid4().hex[:8]}",
                    production_order_number="PO-TEST", batch_number="B-TEST",
                    plant_id=plant.id, line_id=line.id, product_id=product.id,
                    foreman_id=foreman.id, chief_id=chief.id, shift_id=shift.id,
                    production_date=_TEST_DATE, unit="kg",
                    planned_qty=1000.0, actual_qty=900.0,
                    source_updated_at=datetime.now(timezone.utc),
                    imported_at=datetime.now(timezone.utc),
                )
                db.add(pr)
                ids["production"].append(pr.id)
                return pr

            prod_working = make_production(plant_working, line_working)
            prod_absent = make_production(plant_absent, line_absent)
            db.flush()

            raws = list(derive_raw_performance_records(db, _TEST_DATE, _TEST_DATE))
            plant_codes_yielded = {r.plant_code for r in raws if r.production_record_id in (prod_working.id, prod_absent.id)}

            assert plant_working.code in plant_codes_yielded
            assert plant_absent.code not in plant_codes_yielded
        finally:
            db.rollback()
            _cleanup(db, ids)
            db.close()
