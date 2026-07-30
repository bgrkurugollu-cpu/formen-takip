from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '55082513f1be'
down_revision: Union[str, None] = 'afa71ec04497'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('audit_logs', 'ip_address',
               existing_type=postgresql.INET(),
               type_=sa.String(length=64),
               existing_nullable=True)


def downgrade() -> None:
    op.alter_column('audit_logs', 'ip_address',
               existing_type=sa.String(length=64),
               type_=postgresql.INET(),
               existing_nullable=True)
