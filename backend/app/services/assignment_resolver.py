
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
