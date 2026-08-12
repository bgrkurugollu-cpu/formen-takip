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
