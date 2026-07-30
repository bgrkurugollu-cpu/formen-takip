from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'ef3f90d743f8'
down_revision: Union[str, None] = '55082513f1be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('report_exports',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('report_type', sa.Enum('COMPANY_SUMMARY', 'PLANT_COMPARISON', 'SHIFT_COMPARISON', 'FOREMAN_PERFORMANCE', 'KPI_ANALYSIS', 'CRITICAL_PERFORMANCE', 'MISSING_DATA', name='report_type'), nullable=False),
    sa.Column('format', sa.Enum('CSV', 'XLSX', 'PDF', name='report_format'), nullable=False),
    sa.Column('filters_json', sa.JSON(), nullable=False),
    sa.Column('requested_by_user_id', sa.UUID(), nullable=False),
    sa.Column('file_name', sa.String(length=300), nullable=False),
    sa.Column('file_content', sa.LargeBinary(), nullable=False),
    sa.Column('row_count', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('COMPLETED', 'FAILED', name='report_status'), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['requested_by_user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('action_plans',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('title', sa.String(length=300), nullable=False),
    sa.Column('description', sa.String(length=4000), nullable=True),
    sa.Column('plant_id', sa.UUID(), nullable=True),
    sa.Column('department_id', sa.UUID(), nullable=True),
    sa.Column('production_line_id', sa.UUID(), nullable=True),
    sa.Column('shift_id', sa.UUID(), nullable=True),
    sa.Column('foreman_id', sa.UUID(), nullable=True),
    sa.Column('kpi_id', sa.UUID(), nullable=True),
    sa.Column('owner', sa.String(length=200), nullable=False),
    sa.Column('created_by_user_id', sa.UUID(), nullable=False),
    sa.Column('priority', sa.Enum('LOW', 'NORMAL', 'HIGH', 'CRITICAL', name='action_plan_priority'), nullable=False),
    sa.Column('status', sa.Enum('OPEN', 'IN_PROGRESS', 'ON_HOLD', 'COMPLETED', 'CANCELLED', 'DELAYED', name='action_plan_status'), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('target_end_date', sa.Date(), nullable=False),
    sa.Column('actual_end_date', sa.Date(), nullable=True),
    sa.Column('completion_percentage', sa.Integer(), nullable=False),
    sa.Column('outcome_notes', sa.String(length=4000), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
    sa.ForeignKeyConstraint(['foreman_id'], ['foremen.id'], ),
    sa.ForeignKeyConstraint(['kpi_id'], ['kpis.id'], ),
    sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], ),
    sa.ForeignKeyConstraint(['production_line_id'], ['production_lines.id'], ),
    sa.ForeignKeyConstraint(['shift_id'], ['shifts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_action_plans_foreman_id'), 'action_plans', ['foreman_id'], unique=False)
    op.create_index(op.f('ix_action_plans_kpi_id'), 'action_plans', ['kpi_id'], unique=False)
    op.create_index(op.f('ix_action_plans_plant_id'), 'action_plans', ['plant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_action_plans_plant_id'), table_name='action_plans')
    op.drop_index(op.f('ix_action_plans_kpi_id'), table_name='action_plans')
    op.drop_index(op.f('ix_action_plans_foreman_id'), table_name='action_plans')
    op.drop_table('action_plans')
    op.drop_table('report_exports')
