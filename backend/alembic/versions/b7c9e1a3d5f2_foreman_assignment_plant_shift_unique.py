from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b7c9e1a3d5f2'
down_revision: Union[str, None] = 'a4c8e0b2d6f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Bir tesisin bir vardiyasından aynı anda yalnızca bir formen sorumlu olabilir — formen
    # birden fazla tesise (concurrent ForemanAssignment satırları) bağlı olsa da bu artık
    # DB seviyesinde garanti edilir (bkz. reference_data.py seed_reference_data).
    op.create_index(
        'uq_foreman_assignments_plant_shift_active',
        'foreman_assignments',
        ['plant_id', 'shift_id'],
        unique=True,
        postgresql_where=sa.text('is_active = true'),
    )


def downgrade() -> None:
    op.drop_index('uq_foreman_assignments_plant_shift_active', table_name='foreman_assignments')
