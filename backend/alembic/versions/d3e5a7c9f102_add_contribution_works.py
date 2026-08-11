from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'd3e5a7c9f102'
down_revision: Union[str, None] = 'b6d4f8a2c1e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONTRIBUTION_WORK_TYPE = (
    'SMED', 'KAIZEN', 'PROBLEM_SOLVING', 'COST_REDUCTION', 'TIME_SAVING',
    'QUALITY_IMPROVEMENT', 'SAFETY_IMPROVEMENT', 'ENERGY_RESOURCE_SAVING',
    'PRODUCTION_EFFICIENCY', 'DIGITALIZATION', 'OTHER',
)
CONTRIBUTION_STATUS = ('DRAFT', 'PUBLISHED')
FINANCIAL_GAIN_STATUS = ('YES', 'NO', 'NOT_CALCULATED')
CONTRIBUTION_CURRENCY = ('TRY', 'USD', 'EUR')
CONTRIBUTION_GAIN_PERIOD = ('ONE_TIME', 'MONTHLY', 'YEARLY')
CONTRIBUTION_VERIFYING_DEPARTMENT = (
    'FINANCE', 'PRODUCTION', 'MAINTENANCE', 'QUALITY', 'SAFETY', 'ENERGY', 'HR', 'OTHER',
)
CONTRIBUTION_TIME_UNIT = ('SECOND', 'MINUTE', 'HOUR')
CONTRIBUTION_REPEAT_PERIOD = ('DAILY', 'WEEKLY', 'MONTHLY')
CONTRIBUTION_IMPACT_LEVEL = ('LOW', 'MEDIUM', 'HIGH')
CONTRIBUTION_OTHER_GAIN_TYPE = (
    'CAPACITY_INCREASE', 'DOWNTIME_REDUCTION', 'GSF_REDUCTION', 'SCRAP_REDUCTION',
    'SLOW_RUNNING_REDUCTION', 'SAFETY_RISK_REDUCTION', 'ENERGY_REDUCTION',
    'LABOR_SAVING', 'QUALITY_DEFECT_REDUCTION', 'OTHER',
)
CONTRIBUTION_HIGHLIGHTED_GAIN_MODE = ('AUTO', 'MANUAL')

_ENUMS = [
    ('contribution_work_type', CONTRIBUTION_WORK_TYPE),
    ('contribution_status', CONTRIBUTION_STATUS),
    ('financial_gain_status', FINANCIAL_GAIN_STATUS),
    ('contribution_currency', CONTRIBUTION_CURRENCY),
    ('contribution_gain_period', CONTRIBUTION_GAIN_PERIOD),
    ('contribution_verifying_department', CONTRIBUTION_VERIFYING_DEPARTMENT),
    ('contribution_time_unit', CONTRIBUTION_TIME_UNIT),
    ('contribution_repeat_period', CONTRIBUTION_REPEAT_PERIOD),
    ('contribution_impact_level', CONTRIBUTION_IMPACT_LEVEL),
    ('contribution_other_gain_type', CONTRIBUTION_OTHER_GAIN_TYPE),
    ('contribution_highlighted_gain_mode', CONTRIBUTION_HIGHLIGHTED_GAIN_MODE),
]


def upgrade() -> None:
    enum_types = {}
    for name, values in _ENUMS:
        enum_type = postgresql.ENUM(*values, name=name, create_type=False)
        enum_type.create(op.get_bind(), checkfirst=True)
        enum_types[name] = enum_type

    op.create_table(
        'contribution_works',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('work_type', enum_types['contribution_work_type'], nullable=True),
        sa.Column('work_type_other_note', sa.String(length=300), nullable=True),
        sa.Column('summary', sa.String(length=500), nullable=True),
        sa.Column('detailed_description', sa.Text(), nullable=True),
        sa.Column('problem_description', sa.Text(), nullable=True),
        sa.Column('solution_description', sa.Text(), nullable=True),
        sa.Column('result_description', sa.Text(), nullable=True),
        sa.Column('plant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plants.id'), nullable=True),
        sa.Column('work_date', sa.Date(), nullable=True),
        sa.Column('work_date_end', sa.Date(), nullable=True),
        sa.Column('impact_level', enum_types['contribution_impact_level'], nullable=True),
        sa.Column('status', enum_types['contribution_status'], nullable=False),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_standardized', sa.Boolean(), nullable=False),
        sa.Column('is_applicable_other_plants', sa.Boolean(), nullable=False),
        sa.Column('is_permanent_solution', sa.Boolean(), nullable=False),
        sa.Column('work_instruction_updated', sa.Boolean(), nullable=False),
        sa.Column('financial_gain_status', enum_types['financial_gain_status'], nullable=False),
        sa.Column('estimated_amount', sa.Numeric(14, 2), nullable=True),
        sa.Column('verified_amount', sa.Numeric(14, 2), nullable=True),
        sa.Column('currency', enum_types['contribution_currency'], nullable=True),
        sa.Column('gain_period', enum_types['contribution_gain_period'], nullable=True),
        sa.Column('calculation_method', sa.Text(), nullable=True),
        sa.Column('is_gain_verified', sa.Boolean(), nullable=False),
        sa.Column('verified_by_department', enum_types['contribution_verifying_department'], nullable=True),
        sa.Column('verified_by_department_other_note', sa.String(length=300), nullable=True),
        sa.Column('verification_date', sa.Date(), nullable=True),
        sa.Column('verification_note', sa.Text(), nullable=True),
        sa.Column('previous_duration', sa.Numeric(10, 2), nullable=True),
        sa.Column('new_duration', sa.Numeric(10, 2), nullable=True),
        sa.Column('duration_unit', enum_types['contribution_time_unit'], nullable=True),
        sa.Column('per_occurrence_saving', sa.Numeric(10, 2), nullable=True),
        sa.Column('repeat_period', enum_types['contribution_repeat_period'], nullable=True),
        sa.Column('repeat_count', sa.Numeric(10, 2), nullable=True),
        sa.Column('monthly_total_saving_minutes', sa.Numeric(12, 2), nullable=True),
        sa.Column('highlighted_gain_mode', enum_types['contribution_highlighted_gain_mode'], nullable=False),
        sa.Column('highlighted_gain_ref', sa.String(length=80), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_contribution_works_plant_id', 'contribution_works', ['plant_id'])
    op.create_index('ix_contribution_works_status', 'contribution_works', ['status'])
    op.create_index('ix_contribution_works_work_date', 'contribution_works', ['work_date'])
    op.create_index('ix_contribution_works_created_by_user_id', 'contribution_works', ['created_by_user_id'])

    op.create_table(
        'contribution_work_foremen',
        sa.Column(
            'work_id', postgresql.UUID(as_uuid=True),
            sa.ForeignKey('contribution_works.id', ondelete='CASCADE'), primary_key=True,
        ),
        sa.Column('foreman_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('foremen.id'), primary_key=True),
    )
    op.create_index('ix_contribution_work_foremen_work_id', 'contribution_work_foremen', ['work_id'])
    op.create_index('ix_contribution_work_foremen_foreman_id', 'contribution_work_foremen', ['foreman_id'])

    op.create_table(
        'contribution_gains',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'work_id', postgresql.UUID(as_uuid=True),
            sa.ForeignKey('contribution_works.id', ondelete='CASCADE'), nullable=False,
        ),
        sa.Column('gain_type', enum_types['contribution_other_gain_type'], nullable=False),
        sa.Column('gain_type_other_note', sa.String(length=300), nullable=True),
        sa.Column('previous_value', sa.Numeric(14, 4), nullable=True),
        sa.Column('next_value', sa.Numeric(14, 4), nullable=True),
        sa.Column('change_amount', sa.Numeric(14, 4), nullable=True),
        sa.Column('change_percent', sa.Numeric(8, 3), nullable=True),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('measurement_period', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_contribution_gains_work_id', 'contribution_gains', ['work_id'])


def downgrade() -> None:
    op.drop_table('contribution_gains')
    op.drop_table('contribution_work_foremen')
    op.drop_table('contribution_works')

    for name, _values in reversed(_ENUMS):
        postgresql.ENUM(name=name).drop(op.get_bind(), checkfirst=True)
