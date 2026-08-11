"""add foreman/chief contact info (phone_number, email)

Revision ID: b1f4d6a8c0e3
Revises: a8e2c4f6b1d3
Create Date: 2026-08-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b1f4d6a8c0e3'
down_revision: Union[str, None] = 'a8e2c4f6b1d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('chiefs', sa.Column('phone_number', sa.String(length=20), nullable=True))
    op.add_column('chiefs', sa.Column('email', sa.String(length=254), nullable=True))
    op.create_unique_constraint('uq_chiefs_email', 'chiefs', ['email'])

    op.add_column('foremen', sa.Column('phone_number', sa.String(length=20), nullable=True))
    op.add_column('foremen', sa.Column('email', sa.String(length=254), nullable=True))
    op.create_unique_constraint('uq_foremen_email', 'foremen', ['email'])


def downgrade() -> None:
    op.drop_constraint('uq_foremen_email', 'foremen', type_='unique')
    op.drop_column('foremen', 'email')
    op.drop_column('foremen', 'phone_number')

    op.drop_constraint('uq_chiefs_email', 'chiefs', type_='unique')
    op.drop_column('chiefs', 'email')
    op.drop_column('chiefs', 'phone_number')
