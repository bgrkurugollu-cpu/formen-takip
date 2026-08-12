from typing import Sequence, Union

from alembic import op

revision: str = 'f8a1c3e5b7d9'
down_revision: Union[str, None] = 'd4f6a8b1c3e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('uq_perf_record_natural_key', 'performance_records', type_='unique')
    op.create_unique_constraint(
        'uq_perf_record_natural_key',
        'performance_records',
        ['foreman_id', 'kpi_id', 'chief_id', 'shift_id', 'performance_date', 'plant_id'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_perf_record_natural_key', 'performance_records', type_='unique')
    op.create_unique_constraint(
        'uq_perf_record_natural_key',
        'performance_records',
        ['foreman_id', 'kpi_id', 'chief_id', 'shift_id', 'performance_date'],
    )
