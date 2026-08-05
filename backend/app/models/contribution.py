import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    ContributionRole,
    ContributionStatus,
    ContributionWorkType,
    Currency,
    FinancialGainStatus,
    GainPeriod,
    HighlightedGainMode,
    ImpactLevel,
    OtherGainType,
    RepeatPeriod,
    TimeUnit,
    VerifyingDepartment,
)


class ContributionWork(TimestampMixin, Base):

    __tablename__ = "contribution_works"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    work_type: Mapped[ContributionWorkType | None] = mapped_column(
        Enum(ContributionWorkType, name="contribution_work_type")
    )
    work_type_other_note: Mapped[str | None] = mapped_column(String(300))
    summary: Mapped[str | None] = mapped_column(String(500))
    detailed_description: Mapped[str | None] = mapped_column(Text)
    problem_description: Mapped[str | None] = mapped_column(Text)
    solution_description: Mapped[str | None] = mapped_column(Text)
    result_description: Mapped[str | None] = mapped_column(Text)

    plant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plants.id"), nullable=True, index=True)
    work_date: Mapped[date | None] = mapped_column(Date)
    work_date_end: Mapped[date | None] = mapped_column(Date)

    impact_level: Mapped[ImpactLevel | None] = mapped_column(Enum(ImpactLevel, name="contribution_impact_level"))
    status: Mapped[ContributionStatus] = mapped_column(
        Enum(ContributionStatus, name="contribution_status"), nullable=False, default=ContributionStatus.DRAFT
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    is_standardized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_applicable_other_plants: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_permanent_solution: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    work_instruction_updated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    financial_gain_status: Mapped[FinancialGainStatus] = mapped_column(
        Enum(FinancialGainStatus, name="financial_gain_status"),
        nullable=False,
        default=FinancialGainStatus.NOT_CALCULATED,
    )
    estimated_amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    verified_amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[Currency | None] = mapped_column(Enum(Currency, name="contribution_currency"))
    gain_period: Mapped[GainPeriod | None] = mapped_column(Enum(GainPeriod, name="contribution_gain_period"))
    calculation_method: Mapped[str | None] = mapped_column(Text)
    is_gain_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verified_by_department: Mapped[VerifyingDepartment | None] = mapped_column(
        Enum(VerifyingDepartment, name="contribution_verifying_department")
    )
    verified_by_department_other_note: Mapped[str | None] = mapped_column(String(300))
    verification_date: Mapped[date | None] = mapped_column(Date)
    verification_note: Mapped[str | None] = mapped_column(Text)

    previous_duration: Mapped[float | None] = mapped_column(Numeric(10, 2))
    new_duration: Mapped[float | None] = mapped_column(Numeric(10, 2))
    duration_unit: Mapped[TimeUnit | None] = mapped_column(Enum(TimeUnit, name="contribution_time_unit"))
    per_occurrence_saving: Mapped[float | None] = mapped_column(Numeric(10, 2))
    repeat_period: Mapped[RepeatPeriod | None] = mapped_column(Enum(RepeatPeriod, name="contribution_repeat_period"))
    repeat_count: Mapped[float | None] = mapped_column(Numeric(10, 2))
    monthly_total_saving_minutes: Mapped[float | None] = mapped_column(Numeric(12, 2))

    highlighted_gain_mode: Mapped[HighlightedGainMode] = mapped_column(
        Enum(HighlightedGainMode, name="contribution_highlighted_gain_mode"),
        nullable=False,
        default=HighlightedGainMode.AUTO,
    )
    highlighted_gain_ref: Mapped[str | None] = mapped_column(String(80))


class ContributionWorkForeman(Base):

    __tablename__ = "contribution_work_foremen"

    work_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contribution_works.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    foreman_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("foremen.id"), primary_key=True, index=True)
    role: Mapped[ContributionRole] = mapped_column(
        Enum(ContributionRole, name="contribution_role"), nullable=False, default=ContributionRole.CONTRIBUTOR
    )


class ContributionGain(TimestampMixin, Base):

    __tablename__ = "contribution_gains"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contribution_works.id", ondelete="CASCADE"), nullable=False, index=True
    )

    gain_type: Mapped[OtherGainType] = mapped_column(Enum(OtherGainType, name="contribution_other_gain_type"), nullable=False)
    gain_type_other_note: Mapped[str | None] = mapped_column(String(300))
    previous_value: Mapped[float | None] = mapped_column(Numeric(14, 4))
    next_value: Mapped[float | None] = mapped_column(Numeric(14, 4))
    change_amount: Mapped[float | None] = mapped_column(Numeric(14, 4))
    change_percent: Mapped[float | None] = mapped_column(Numeric(8, 3))
    unit: Mapped[str | None] = mapped_column(String(50))
    measurement_period: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
