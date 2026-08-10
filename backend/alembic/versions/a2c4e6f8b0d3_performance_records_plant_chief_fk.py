"""performance_records gets the (plant_id, chief_id) composite FK.

`production_records` and `foreman_work_calendar` already carry a composite FK to
`plants(id, chief_id)` (`fk_production_records_plant_chief` / `fk_foreman_work_calendar_plant_chief`)
that makes a plant/chief mismatch a DB-level impossibility — `performance_records` never got
the same treatment. `ingestion.py` now validates plant/chief/shift against the foreman's actual
assignment before insert (see `app/services/assignment_resolver.py`), so this FK should never
fire in practice; it is a DB-level backstop matching the other two tables, not the primary guard.
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'a2c4e6f8b0d3'
down_revision: Union[str, None] = 'f8a1c3e5b7d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key(
        'fk_performance_records_plant_chief',
        'performance_records', 'plants',
        ['plant_id', 'chief_id'], ['id', 'chief_id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_performance_records_plant_chief', 'performance_records', type_='foreignkey')
