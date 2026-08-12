from typing import Sequence, Union

from alembic import op

revision: str = 'c3e5f7a9b1d4'
down_revision: Union[str, None] = 'b7c9e1a3d5f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('uq_foreman_work_calendar_foreman_date', 'foreman_work_calendar', type_='unique')
    op.create_unique_constraint(
        'uq_foreman_work_calendar_foreman_date_plant',
        'foreman_work_calendar',
        ['foreman_id', 'work_date', 'plant_id'],
    )

    op.drop_constraint('uq_production_record_natural_key', 'production_records', type_='unique')
    op.create_unique_constraint(
        'uq_production_record_natural_key',
        'production_records',
        ['foreman_id', 'production_date', 'shift_id', 'plant_id'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_production_record_natural_key', 'production_records', type_='unique')
    op.create_unique_constraint(
        'uq_production_record_natural_key',
        'production_records',
        ['foreman_id', 'production_date', 'shift_id'],
    )

    op.drop_constraint('uq_foreman_work_calendar_foreman_date_plant', 'foreman_work_calendar', type_='unique')
    op.create_unique_constraint(
        'uq_foreman_work_calendar_foreman_date', 'foreman_work_calendar', ['foreman_id', 'work_date']
    )
