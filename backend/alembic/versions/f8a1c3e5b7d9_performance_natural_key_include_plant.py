"""performance_records natural key includes plant_id.

`c3e5f7a9b1d4` added plant_id to the foreman_work_calendar / production_records natural
keys once a foreman could hold 2-4 concurrent plant assignments, but left
uq_perf_record_natural_key on performance_records unfixed. Each production_record (one per
foreman/plant/day) derives its own per-KPI performance rows with the same
foreman/kpi/chief/shift/date but a different plant — without plant_id in the key, only the
first plant's row per day survived ingestion's ON CONFLICT DO NOTHING and the rest were
silently skipped as DUPLICATE data-quality issues.

No conflict backfill is needed: the old (looser) constraint already guaranteed every existing
row is unique on its column subset, so adding plant_id cannot introduce a collision among rows
already in the table — it only affects rows ingestion will accept going forward.
"""
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
