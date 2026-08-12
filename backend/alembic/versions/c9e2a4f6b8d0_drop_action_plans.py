from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c9e2a4f6b8d0'
down_revision: Union[str, None] = 'b3d5f7a9c1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(op.f('ix_action_plans_plant_id'), table_name='action_plans')
    op.drop_index(op.f('ix_action_plans_kpi_id'), table_name='action_plans')
    op.drop_index(op.f('ix_action_plans_foreman_id'), table_name='action_plans')
    op.drop_table('action_plans')
    op.execute('DROP TYPE action_plan_priority')
    op.execute('DROP TYPE action_plan_status')


def downgrade() -> None:
    raise NotImplementedError(
        "Bu migration geri alınamaz: Aksiyon Planları özelliği tamamen kaldırıldı, "
        "action_plans tablosundaki tüm kayıtlar kalıcı olarak silindi."
    )
