
import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.db.session import SessionLocal
from app.models.foreman import Chief, Foreman, ForemanAssignment
from app.models.organization import Plant


def _pick_assignment(db) -> ForemanAssignment:
    return db.scalar(select(ForemanAssignment).where(ForemanAssignment.is_active.is_(True)).limit(1))


def _pick_other_chief(db, exclude_chief_id) -> Chief:
    return db.scalar(select(Chief).where(Chief.id != exclude_chief_id).limit(1))


def _pick_foreman_with_same_chief(db, chief_id, exclude_foreman_id):
    return db.scalar(
        select(ForemanAssignment.foreman_id).where(
            ForemanAssignment.chief_id == chief_id, ForemanAssignment.foreman_id != exclude_foreman_id
        ).limit(1)
    )


class TestForemanAssignmentDateRangeCheck:
    def test_end_date_before_start_date_is_rejected(self):
        db = SessionLocal()
        try:
            existing = _pick_assignment(db)
            bad = ForemanAssignment(
                id=uuid.uuid4(), foreman_id=existing.foreman_id, plant_id=existing.plant_id,
                chief_id=existing.chief_id, shift_id=existing.shift_id,
                start_date=date(2026, 1, 10), end_date=date(2026, 1, 1), is_active=False,
            )
            db.add(bad)
            with pytest.raises(IntegrityError):
                db.commit()
        finally:
            db.rollback()
            db.close()


class TestForemanAssignmentInactiveRequiresEndDate:
    def test_inactive_without_end_date_is_rejected(self):
        db = SessionLocal()
        try:
            existing = _pick_assignment(db)
            bad = ForemanAssignment(
                id=uuid.uuid4(), foreman_id=existing.foreman_id, plant_id=existing.plant_id,
                chief_id=existing.chief_id, shift_id=existing.shift_id,
                start_date=date(2026, 1, 1), end_date=None, is_active=False,
            )
            db.add(bad)
            with pytest.raises(IntegrityError):
                db.commit()
        finally:
            db.rollback()
            db.close()


class TestForemanAssignmentNoOverlappingDateRanges:
    def test_overlapping_historical_range_for_same_plant_shift_is_rejected(self):
        db = SessionLocal()
        try:
            existing = _pick_assignment(db)
            # Aynı şefe bağlı BAŞKA bir formen kullanılıyor ki tetikleyici (single-chief) değil,
            # asıl test edilmek istenen EXCLUDE (tarih aralığı çakışması) kısıtı devreye girsin.
            other_foreman_id = _pick_foreman_with_same_chief(db, existing.chief_id, existing.foreman_id)
            overlapping = ForemanAssignment(
                id=uuid.uuid4(), foreman_id=other_foreman_id, plant_id=existing.plant_id,
                chief_id=existing.chief_id, shift_id=existing.shift_id,
                start_date=existing.start_date, end_date=existing.start_date + timedelta(days=5),
                is_active=False,
            )
            db.add(overlapping)
            with pytest.raises(IntegrityError):
                db.commit()
        finally:
            db.rollback()
            db.close()


class TestForemanSingleChiefInvariant:
    def test_second_assignment_for_foreman_with_different_chief_is_rejected(self):
        db = SessionLocal()
        try:
            existing = _pick_assignment(db)
            other_chief = _pick_other_chief(db, existing.chief_id)
            other_plant = db.scalar(
                select(Plant).where(Plant.chief_id == other_chief.id).limit(1)
            )
            bad = ForemanAssignment(
                id=uuid.uuid4(), foreman_id=existing.foreman_id, plant_id=other_plant.id,
                chief_id=other_chief.id, shift_id=existing.shift_id,
                start_date=date(2030, 1, 1), end_date=None, is_active=True,
            )
            db.add(bad)
            # Tetikleyici PL/pgSQL `RAISE EXCEPTION` ile hata verir — psycopg bunu
            # ProgrammingError'a sarar (CHECK/EXCLUDE'daki IntegrityError'dan farklı).
            with pytest.raises(ProgrammingError):
                db.commit()
        finally:
            db.rollback()
            db.close()

    def test_second_plant_for_same_foreman_same_chief_is_allowed(self):
        db = SessionLocal()
        temp_plant_id = None
        try:
            existing = _pick_assignment(db)
            reference_plant = db.get(Plant, existing.plant_id)

            # Gerçek tesislerin her ikisi (V1/V2) de zaten açık uçlu satırlarla dolu — tetikleyicinin
            # "aynı şef" satırlarını EXCLUDE kısıtına takılmadan izole test etmek için aynı şefe
            # bağlı, boş bir geçici tesis kullanılıyor.
            temp_plant = Plant(
                id=uuid.uuid4(), code=f"TEST-{uuid.uuid4().hex[:8]}", name="Test Tesis (geçici)",
                sequence_number=100_000 + (uuid.uuid4().int % 800_000),
                factory_id=reference_plant.factory_id, chief_id=existing.chief_id, is_active=True,
            )
            db.add(temp_plant)
            db.flush()
            temp_plant_id = temp_plant.id

            ok = ForemanAssignment(
                id=uuid.uuid4(), foreman_id=existing.foreman_id, plant_id=temp_plant.id,
                chief_id=existing.chief_id, shift_id=existing.shift_id,
                start_date=date(2031, 1, 1), end_date=date(2031, 1, 2), is_active=False,
            )
            db.add(ok)
            db.commit()
        finally:
            db.rollback()
            if temp_plant_id is not None:
                db.execute(ForemanAssignment.__table__.delete().where(ForemanAssignment.plant_id == temp_plant_id))
                db.execute(Plant.__table__.delete().where(Plant.id == temp_plant_id))
                db.commit()
            db.close()
