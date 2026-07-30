from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import ActionPlanPriority, ActionPlanStatus


class ActionPlanCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    plant_id: UUID | None = None
    chief_id: UUID | None = None
    shift_id: UUID | None = None
    foreman_id: UUID | None = None
    kpi_id: UUID | None = None
    owner: str = Field(min_length=1, max_length=200)
    priority: ActionPlanPriority = ActionPlanPriority.NORMAL
    status: ActionPlanStatus = ActionPlanStatus.OPEN
    start_date: date
    target_end_date: date
    completion_percentage: int = Field(default=0, ge=0, le=100)
    outcome_notes: str | None = None


class ActionPlanUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    owner: str | None = Field(default=None, min_length=1, max_length=200)
    priority: ActionPlanPriority | None = None
    status: ActionPlanStatus | None = None
    target_end_date: date | None = None
    actual_end_date: date | None = None
    completion_percentage: int | None = Field(default=None, ge=0, le=100)
    outcome_notes: str | None = None
