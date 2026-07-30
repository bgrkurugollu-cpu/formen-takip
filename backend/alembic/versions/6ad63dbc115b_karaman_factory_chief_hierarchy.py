from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '6ad63dbc115b'
down_revision: Union[str, None] = 'ef3f90d743f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "TRUNCATE TABLE plants, foremen, kpi_targets, integration_runs, "
        "shifts, kpis, performance_level_rules CASCADE"
    )

    op.drop_constraint('uq_perf_record_natural_key', 'performance_records', type_='unique')
    op.drop_column('performance_records', 'department_id')
    op.drop_column('performance_records', 'production_line_id')
    op.drop_column('foreman_assignments', 'department_id')
    op.drop_column('foreman_assignments', 'production_line_id')
    op.drop_column('action_plans', 'department_id')
    op.drop_column('action_plans', 'production_line_id')

    op.drop_table('production_lines')
    op.drop_table('departments')

    op.create_table(
        'factories',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('location', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_factories_code'), 'factories', ['code'], unique=True)

    op.create_table(
        'chiefs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('employee_number', sa.String(length=30), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('plant_id', sa.UUID(), nullable=False),
        sa.Column('hire_date', sa.Date(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('sap_personnel_number', sa.String(length=30), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id', 'plant_id', name='uq_chiefs_id_plant_id'),
    )
    op.create_index(op.f('ix_chiefs_employee_number'), 'chiefs', ['employee_number'], unique=True)
    op.create_index(op.f('ix_chiefs_plant_id'), 'chiefs', ['plant_id'], unique=False)

    op.drop_index('ix_plants_region', table_name='plants')
    op.drop_column('plants', 'region')
    op.drop_column('plants', 'city')
    op.add_column('plants', sa.Column('factory_id', sa.UUID(), nullable=False))
    op.add_column('plants', sa.Column('sequence_number', sa.Integer(), nullable=False))
    op.create_foreign_key(None, 'plants', 'factories', ['factory_id'], ['id'])
    op.create_index(op.f('ix_plants_factory_id'), 'plants', ['factory_id'], unique=False)
    op.create_unique_constraint('uq_plants_sequence_number', 'plants', ['sequence_number'])

    op.add_column('foreman_assignments', sa.Column('chief_id', sa.UUID(), nullable=False))
    op.create_index(op.f('ix_foreman_assignments_chief_id'), 'foreman_assignments', ['chief_id'], unique=False)
    op.create_foreign_key(
        'fk_foreman_assignments_chief_plant', 'foreman_assignments', 'chiefs',
        ['chief_id', 'plant_id'], ['id', 'plant_id'],
    )

    op.add_column('performance_records', sa.Column('chief_id', sa.UUID(), nullable=False))
    op.create_index(op.f('ix_performance_records_chief_id'), 'performance_records', ['chief_id'], unique=False)
    op.create_foreign_key(None, 'performance_records', 'chiefs', ['chief_id'], ['id'])

    op.add_column('action_plans', sa.Column('chief_id', sa.UUID(), nullable=True))
    op.create_foreign_key(None, 'action_plans', 'chiefs', ['chief_id'], ['id'])

    op.create_unique_constraint(
        'uq_perf_record_natural_key', 'performance_records',
        ['foreman_id', 'kpi_id', 'chief_id', 'shift_id', 'performance_date'],
    )

    op.execute("ALTER TYPE target_scope_type RENAME TO target_scope_type_old")
    op.execute("CREATE TYPE target_scope_type AS ENUM ('COMPANY', 'PLANT', 'CHIEF', 'FOREMAN')")
    op.execute(
        "ALTER TABLE kpi_targets ALTER COLUMN scope_type TYPE target_scope_type "
        "USING scope_type::text::target_scope_type"
    )
    op.execute("DROP TYPE target_scope_type_old")


def downgrade() -> None:
    raise NotImplementedError(
        "Bu migration geri alınamaz: eski organizasyon verisini ve ona bağlı "
        "tüm performans kayıtlarını TRUNCATE ile kalıcı olarak siler."
    )
