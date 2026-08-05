from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '9f3a2c7b1e44'
down_revision: Union[str, None] = '6ad63dbc115b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('kpis', 'min_score',
               existing_type=sa.Numeric(6, 2),
               type_=sa.Numeric(12, 2),
               existing_nullable=False)
    op.alter_column('kpis', 'max_score',
               existing_type=sa.Numeric(6, 2),
               type_=sa.Numeric(12, 2),
               existing_nullable=False)
    op.alter_column('performance_scores', 'raw_score',
               existing_type=sa.Numeric(8, 3),
               type_=sa.Numeric(14, 3),
               existing_nullable=False)
    op.alter_column('performance_scores', 'capped_score',
               existing_type=sa.Numeric(8, 3),
               type_=sa.Numeric(14, 3),
               existing_nullable=False)
    op.alter_column('performance_scores', 'weighted_contribution',
               existing_type=sa.Numeric(8, 3),
               type_=sa.Numeric(14, 3),
               existing_nullable=False)


def downgrade() -> None:
    op.alter_column('performance_scores', 'weighted_contribution',
               existing_type=sa.Numeric(14, 3),
               type_=sa.Numeric(8, 3),
               existing_nullable=False)
    op.alter_column('performance_scores', 'capped_score',
               existing_type=sa.Numeric(14, 3),
               type_=sa.Numeric(8, 3),
               existing_nullable=False)
    op.alter_column('performance_scores', 'raw_score',
               existing_type=sa.Numeric(14, 3),
               type_=sa.Numeric(8, 3),
               existing_nullable=False)
    op.alter_column('kpis', 'max_score',
               existing_type=sa.Numeric(12, 2),
               type_=sa.Numeric(6, 2),
               existing_nullable=False)
    op.alter_column('kpis', 'min_score',
               existing_type=sa.Numeric(12, 2),
               type_=sa.Numeric(6, 2),
               existing_nullable=False)
