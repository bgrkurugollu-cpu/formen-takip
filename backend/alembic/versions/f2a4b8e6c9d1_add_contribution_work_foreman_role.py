from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'f2a4b8e6c9d1'
down_revision: Union[str, None] = 'e1b2c4d6f8a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONTRIBUTION_ROLE = ('LEAD', 'CONTRIBUTOR')


def upgrade() -> None:
    role_enum = postgresql.ENUM(*CONTRIBUTION_ROLE, name='contribution_role', create_type=False)
    role_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'contribution_work_foremen',
        sa.Column('role', role_enum, nullable=False, server_default='CONTRIBUTOR'),
    )
    op.alter_column('contribution_work_foremen', 'role', server_default=None)

    op.execute(
        """
        UPDATE contribution_work_foremen cwf
        SET role = 'LEAD'
        WHERE (SELECT count(*) FROM contribution_work_foremen x WHERE x.work_id = cwf.work_id) = 1
        """
    )


def downgrade() -> None:
    op.drop_column('contribution_work_foremen', 'role')
    postgresql.ENUM(name='contribution_role').drop(op.get_bind(), checkfirst=True)
