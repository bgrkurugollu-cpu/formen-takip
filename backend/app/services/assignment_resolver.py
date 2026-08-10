
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from app.models.organization import Shift
from app.services.shift_rotation import actual_shift_for_date


class AssignmentCandidate(Protocol):
    foreman_id: UUID
    plant_id: UUID
    shift_id: UUID
    start_date: date
    end_date: date | None
    is_active: bool


@dataclass
class ResolvedAssignment:
    expected_shift_id: UUID


class NoActiveAssignmentError(LookupError):
    pass


def resolve_assignment(
    candidates: list[AssignmentCandidate],
    as_of: date,
    foreman_id: UUID,
    plant_id: UUID,
    shifts: list[Shift],
) -> ResolvedAssignment:
    """Formen+tesis+tarih için geçerli atamayı ve o tarihteki GERÇEK vardiyayı çözer.

    Şef atamayı çözmez — `Plant.chief_id` her zaman o tesisin tek yetkili şefidir (bkz.
    `fk_performance_records_plant_chief`), çağıran taraf şef uyumunu doğrudan buna karşı
    kontrol eder. `ForemanAssignment.shift_id` bir rotasyon çıpasıdır, günlük gerçek vardiya
    değil — bu yüzden beklenen vardiya `actual_shift_for_date` ile bu çıpadan yeniden
    hesaplanır (bkz. app/services/shift_rotation.py). Eşleşen aktif atama yoksa (formen o
    tesise o tarihte atanmamış ya da atama süresi dolmuş/başlamamış) `NoActiveAssignmentError`
    fırlatılır.
    """
    for candidate in candidates:
        if (
            candidate.is_active
            and candidate.foreman_id == foreman_id
            and candidate.plant_id == plant_id
            and candidate.start_date <= as_of
            and (candidate.end_date is None or candidate.end_date >= as_of)
        ):
            anchor_shift = next(s for s in shifts if s.id == candidate.shift_id)
            expected_shift = actual_shift_for_date(as_of, anchor_shift, shifts)
            return ResolvedAssignment(expected_shift_id=expected_shift.id)

    raise NoActiveAssignmentError(
        f"Formen {foreman_id} tesise {plant_id} {as_of} tarihinde atanmış değil."
    )
