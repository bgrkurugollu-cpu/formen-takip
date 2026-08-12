from __future__ import annotations

from datetime import date

from app.models.organization import Shift

ROTATION_EPOCH = date(2024, 1, 1)


def actual_shift_for_date(d: date, anchor_shift: Shift, shifts: list[Shift]) -> Shift:
    ordered = sorted(shifts, key=lambda s: s.sequence)
    week_index = (d - ROTATION_EPOCH).days // 7
    anchor_idx = ordered.index(anchor_shift)
    return ordered[(anchor_idx + week_index) % len(ordered)]
