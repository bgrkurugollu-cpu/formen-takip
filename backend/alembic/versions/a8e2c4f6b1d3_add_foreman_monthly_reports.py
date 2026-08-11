"""add foreman_monthly_reports

Revision ID: a8e2c4f6b1d3
Revises: c9e2a4f6b8d0
Create Date: 2026-08-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a8e2c4f6b1d3'
down_revision: Union[str, None] = 'c9e2a4f6b8d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('foreman_monthly_reports',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('foreman_id', sa.UUID(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('month', sa.Integer(), nullable=False),
    sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('overall_score', sa.Numeric(6, 2), nullable=True),
    sa.Column('overall_level_name', sa.String(length=50), nullable=True),
    sa.Column('is_reliable', sa.Boolean(), nullable=False),
    sa.Column('report_data', sa.JSON(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['foreman_id'], ['foremen.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('foreman_id', 'year', 'month', name='uq_foreman_monthly_reports_foreman_year_month'),
    )
    op.create_index(op.f('ix_foreman_monthly_reports_foreman_id'), 'foreman_monthly_reports', ['foreman_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_foreman_monthly_reports_foreman_id'), table_name='foreman_monthly_reports')
    op.drop_table('foreman_monthly_reports')
