from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import (
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


class ContributionGainInput(BaseModel):
    gain_type: OtherGainType
    gain_type_other_note: str | None = None
    previous_value: float | None = None
    next_value: float | None = None
    unit: str | None = None
    measurement_period: str | None = None
    description: str | None = None


class ContributionWorkCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    status: ContributionStatus = ContributionStatus.DRAFT

    work_type: ContributionWorkType | None = None
    work_type_other_note: str | None = None
    summary: str | None = Field(default=None, max_length=500)
    detailed_description: str | None = None
    problem_description: str | None = None
    solution_description: str | None = None
    result_description: str | None = None

    foreman_ids: list[UUID] = Field(default_factory=list)
    plant_id: UUID | None = None
    work_date: date | None = None
    work_date_end: date | None = None
    impact_level: ImpactLevel | None = None

    is_standardized: bool = False
    is_applicable_other_plants: bool = False
    is_permanent_solution: bool = False
    work_instruction_updated: bool = False

    financial_gain_status: FinancialGainStatus = FinancialGainStatus.NOT_CALCULATED
    estimated_amount: float | None = None
    verified_amount: float | None = None
    currency: Currency | None = None
    gain_period: GainPeriod | None = None
    calculation_method: str | None = None
    is_gain_verified: bool = False
    verified_by_department: VerifyingDepartment | None = None
    verified_by_department_other_note: str | None = None
    verification_date: date | None = None
    verification_note: str | None = None

    previous_duration: float | None = None
    new_duration: float | None = None
    duration_unit: TimeUnit | None = None
    repeat_period: RepeatPeriod | None = None
    repeat_count: float | None = None
    per_occurrence_saving: float | None = None
    monthly_total_saving_minutes: float | None = None

    gains: list[ContributionGainInput] = Field(default_factory=list)

    highlighted_gain_mode: HighlightedGainMode = HighlightedGainMode.AUTO
    highlighted_gain_ref: str | None = None


class ContributionWorkUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    status: ContributionStatus | None = None

    work_type: ContributionWorkType | None = None
    work_type_other_note: str | None = None
    summary: str | None = Field(default=None, max_length=500)
    detailed_description: str | None = None
    problem_description: str | None = None
    solution_description: str | None = None
    result_description: str | None = None

    foreman_ids: list[UUID] | None = None
    plant_id: UUID | None = None
    work_date: date | None = None
    work_date_end: date | None = None
    impact_level: ImpactLevel | None = None

    is_standardized: bool | None = None
    is_applicable_other_plants: bool | None = None
    is_permanent_solution: bool | None = None
    work_instruction_updated: bool | None = None

    financial_gain_status: FinancialGainStatus | None = None
    estimated_amount: float | None = None
    verified_amount: float | None = None
    currency: Currency | None = None
    gain_period: GainPeriod | None = None
    calculation_method: str | None = None
    is_gain_verified: bool | None = None
    verified_by_department: VerifyingDepartment | None = None
    verified_by_department_other_note: str | None = None
    verification_date: date | None = None
    verification_note: str | None = None

    previous_duration: float | None = None
    new_duration: float | None = None
    duration_unit: TimeUnit | None = None
    repeat_period: RepeatPeriod | None = None
    repeat_count: float | None = None
    per_occurrence_saving: float | None = None
    monthly_total_saving_minutes: float | None = None

    gains: list[ContributionGainInput] | None = None

    highlighted_gain_mode: HighlightedGainMode | None = None
    highlighted_gain_ref: str | None = None
