import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import ActionPlanPriority, ActionPlanStatus


class ActionPlan(TimestampMixin, Base):

    __tablename__ = "action_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(String(4000))

    plant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plants.id"), nullable=True, index=True)
    chief_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("chiefs.id"), nullable=True)
    shift_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("shifts.id"), nullable=True)
    foreman_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("foremen.id"), nullable=True, index=True)
    kpi_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("kpis.id"), nullable=True, index=True)

    owner: Mapped[str] = mapped_column(String(200), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    priority: Mapped[ActionPlanPriority] = mapped_column(
        Enum(ActionPlanPriority, name="action_plan_priority"), nullable=False, default=ActionPlanPriority.NORMAL
    )
    status: Mapped[ActionPlanStatus] = mapped_column(
        Enum(ActionPlanStatus, name="action_plan_status"), nullable=False, default=ActionPlanStatus.OPEN
    )

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    target_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    actual_end_date: Mapped[date | None] = mapped_column(Date)

    completion_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    outcome_notes: Mapped[str | None] = mapped_column(String(4000))
