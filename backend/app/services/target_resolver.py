
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from app.models.enums import TargetScopeType

SCOPE_PRIORITY: list[TargetScopeType] = [
    TargetScopeType.FOREMAN,
    TargetScopeType.CHIEF,
    TargetScopeType.PLANT,
    TargetScopeType.COMPANY,
]


class TargetCandidate(Protocol):
    scope_type: TargetScopeType
    scope_id: UUID | None
    target_value: float
    valid_from: date
    valid_to: date | None
    is_active: bool


@dataclass
class ResolvedTarget:
    target_value: float
    resolved_scope: TargetScopeType


class NoTargetFoundError(LookupError):
    pass


def resolve_target(
    candidates: list[TargetCandidate],
    as_of: date,
    foreman_id: UUID,
    chief_id: UUID,
    plant_id: UUID,
) -> ResolvedTarget:
    scope_ids: dict[TargetScopeType, UUID | None] = {
        TargetScopeType.FOREMAN: foreman_id,
        TargetScopeType.CHIEF: chief_id,
        TargetScopeType.PLANT: plant_id,
        TargetScopeType.COMPANY: None,
    }

    valid = [
        c
        for c in candidates
        if c.is_active and c.valid_from <= as_of and (c.valid_to is None or c.valid_to >= as_of)
    ]

    for scope in SCOPE_PRIORITY:
        expected_id = scope_ids[scope]
        for candidate in valid:
            if candidate.scope_type != scope:
                continue
            if scope == TargetScopeType.COMPANY or candidate.scope_id == expected_id:
                return ResolvedTarget(target_value=candidate.target_value, resolved_scope=scope)

    raise NoTargetFoundError("Hiçbir seviyede geçerli hedef bulunamadı.")
