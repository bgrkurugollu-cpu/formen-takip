from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID, uuid4

import pytest

from app.services.assignment_resolver import NoActiveAssignmentError, resolve_assignment
from app.services.shift_rotation import ROTATION_EPOCH


@dataclass
class FakeAssignment:
    foreman_id: UUID
    plant_id: UUID
    chief_id: UUID
    shift_id: UUID
    start_date: date
    end_date: date | None
    is_active: bool = True


@dataclass
class FakeShift:
    id: UUID
    sequence: int


FOREMAN_ID = uuid4()
PLANT_ID = uuid4()
CHIEF_ID = uuid4()
V1_ID = uuid4()
V2_ID = uuid4()
SHIFTS = [FakeShift(V1_ID, 1), FakeShift(V2_ID, 2)]


def resolve(candidates, as_of=ROTATION_EPOCH):
    return resolve_assignment(candidates, as_of, FOREMAN_ID, PLANT_ID, SHIFTS)


class TestAssignmentResolution:
    def test_resolves_anchor_shift_in_epoch_week(self):
        candidates = [
            FakeAssignment(FOREMAN_ID, PLANT_ID, CHIEF_ID, V1_ID, date(2024, 1, 1), None),
        ]
        result = resolve(candidates)
        assert result.expected_shift_id == V1_ID

    def test_expected_shift_rotates_weekly_from_anchor(self):
        candidates = [
            FakeAssignment(FOREMAN_ID, PLANT_ID, CHIEF_ID, V1_ID, date(2024, 1, 1), None),
        ]
        one_week_later = ROTATION_EPOCH + timedelta(days=7)
        result = resolve(candidates, as_of=one_week_later)
        assert result.expected_shift_id == V2_ID

    def test_ignores_assignment_for_other_plant(self):
        other_plant = uuid4()
        candidates = [
            FakeAssignment(FOREMAN_ID, other_plant, CHIEF_ID, V1_ID, date(2024, 1, 1), None),
        ]
        with pytest.raises(NoActiveAssignmentError):
            resolve(candidates)

    def test_ignores_assignment_for_other_foreman(self):
        other_foreman = uuid4()
        candidates = [
            FakeAssignment(other_foreman, PLANT_ID, CHIEF_ID, V1_ID, date(2024, 1, 1), None),
        ]
        with pytest.raises(NoActiveAssignmentError):
            resolve(candidates)

    def test_ignores_assignment_before_start_date(self):
        candidates = [
            FakeAssignment(FOREMAN_ID, PLANT_ID, CHIEF_ID, V1_ID, date(2026, 1, 1), None),
        ]
        with pytest.raises(NoActiveAssignmentError):
            resolve(candidates, as_of=date(2025, 12, 31))

    def test_ignores_assignment_after_end_date(self):
        candidates = [
            FakeAssignment(FOREMAN_ID, PLANT_ID, CHIEF_ID, V1_ID, date(2020, 1, 1), date(2024, 6, 1)),
        ]
        with pytest.raises(NoActiveAssignmentError):
            resolve(candidates, as_of=date(2024, 6, 2))

    def test_ignores_inactive_assignment(self):
        candidates = [
            FakeAssignment(FOREMAN_ID, PLANT_ID, CHIEF_ID, V1_ID, date(2024, 1, 1), None, is_active=False),
        ]
        with pytest.raises(NoActiveAssignmentError):
            resolve(candidates)

    def test_no_candidates_raises(self):
        with pytest.raises(NoActiveAssignmentError):
            resolve([])
