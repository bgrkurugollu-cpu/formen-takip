from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'c7a1f9d0b2e3'
down_revision: Union[str, None] = '9f3a2c7b1e44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    production_source_system = postgresql.ENUM(
        'SYNTHETIC', 'SAP', name='production_source_system', create_type=False
    )
    production_source_system.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'products',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(length=30), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('unit', sa.String(length=20), nullable=False),
        sa.Column('standard_gram', sa.Numeric(10, 3), nullable=True),
        sa.Column('lower_gram_limit', sa.Numeric(10, 3), nullable=True),
        sa.Column('upper_gram_limit', sa.Numeric(10, 3), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('sap_material_code', sa.String(length=30), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('code'),
    )
    op.create_index('ix_products_code', 'products', ['code'])

    op.create_table(
        'production_lines',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(length=30), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('plant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plants.id'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('code'),
    )
    op.create_index('ix_production_lines_code', 'production_lines', ['code'])
    op.create_index('ix_production_lines_plant_id', 'production_lines', ['plant_id'])

    op.create_table(
        'company_calendar',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('calendar_date', sa.Date(), nullable=False),
        sa.Column('is_holiday', sa.Boolean(), nullable=False),
        sa.Column('note', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('calendar_date'),
    )
    op.create_index('ix_company_calendar_calendar_date', 'company_calendar', ['calendar_date'])

    op.create_table(
        'foreman_work_calendar',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('foreman_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('foremen.id'), nullable=False),
        sa.Column('work_date', sa.Date(), nullable=False),
        sa.Column('plant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plants.id'), nullable=False),
        sa.Column('chief_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('chiefs.id'), nullable=False),
        sa.Column('shift_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shifts.id'), nullable=False),
        sa.Column('line_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('production_lines.id'), nullable=False),
        sa.Column('is_working', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('foreman_id', 'work_date', name='uq_foreman_work_calendar_foreman_date'),
    )
    op.create_index('ix_foreman_work_calendar_foreman_id', 'foreman_work_calendar', ['foreman_id'])
    op.create_index('ix_foreman_work_calendar_work_date', 'foreman_work_calendar', ['work_date'])
    op.create_index('ix_foreman_work_calendar_plant_id', 'foreman_work_calendar', ['plant_id'])
    op.create_index('ix_foreman_work_calendar_chief_id', 'foreman_work_calendar', ['chief_id'])
    op.create_index('ix_foreman_work_calendar_shift_id', 'foreman_work_calendar', ['shift_id'])
    op.create_index('ix_foreman_work_calendar_line_id', 'foreman_work_calendar', ['line_id'])

    op.create_table(
        'production_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_system', production_source_system, nullable=False),
        sa.Column('source_record_id', sa.String(length=100), nullable=False),
        sa.Column('production_order_number', sa.String(length=50), nullable=False),
        sa.Column('batch_number', sa.String(length=50), nullable=False),
        sa.Column('plant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plants.id'), nullable=False),
        sa.Column('line_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('production_lines.id'), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('foreman_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('foremen.id'), nullable=False),
        sa.Column('chief_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('chiefs.id'), nullable=False),
        sa.Column('shift_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shifts.id'), nullable=False),
        sa.Column('production_date', sa.Date(), nullable=False),
        sa.Column('unit', sa.String(length=20), nullable=False),
        sa.Column('planned_qty', sa.Numeric(14, 4), nullable=True),
        sa.Column('actual_qty', sa.Numeric(14, 4), nullable=True),
        sa.Column('planned_start_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('planned_end_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_start_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_end_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('standard_speed', sa.Numeric(14, 4), nullable=True),
        sa.Column('actual_speed', sa.Numeric(14, 4), nullable=True),
        sa.Column('measured_avg_gram', sa.Numeric(10, 3), nullable=True),
        sa.Column('gram_sample_count', sa.Integer(), nullable=True),
        sa.Column('gsf_qty', sa.Numeric(14, 4), nullable=True),
        sa.Column('iskarta_qty', sa.Numeric(14, 4), nullable=True),
        sa.Column('technical_downtime_minutes', sa.Numeric(10, 2), nullable=True),
        sa.Column('manufacturing_downtime_minutes', sa.Numeric(10, 2), nullable=True),
        sa.Column('other_downtime_minutes', sa.Numeric(10, 2), nullable=True),
        sa.Column('plan_revision_no', sa.Integer(), nullable=False),
        sa.Column('plan_revision_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('imported_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('source_system', 'source_record_id', name='uq_production_record_source'),
        sa.UniqueConstraint('foreman_id', 'production_date', 'shift_id', name='uq_production_record_natural_key'),
    )
    op.create_index('ix_production_records_source_record_id', 'production_records', ['source_record_id'])
    op.create_index('ix_production_records_production_order_number', 'production_records', ['production_order_number'])
    op.create_index('ix_production_records_plant_id', 'production_records', ['plant_id'])
    op.create_index('ix_production_records_line_id', 'production_records', ['line_id'])
    op.create_index('ix_production_records_product_id', 'production_records', ['product_id'])
    op.create_index('ix_production_records_foreman_id', 'production_records', ['foreman_id'])
    op.create_index('ix_production_records_chief_id', 'production_records', ['chief_id'])
    op.create_index('ix_production_records_shift_id', 'production_records', ['shift_id'])
    op.create_index('ix_production_records_production_date', 'production_records', ['production_date'])

    op.add_column(
        'performance_records',
        sa.Column('production_record_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_performance_records_production_record_id',
        'performance_records', 'production_records',
        ['production_record_id'], ['id'], ondelete='SET NULL',
    )
    op.create_index(
        'ix_performance_records_production_record_id', 'performance_records', ['production_record_id']
    )


def downgrade() -> None:
    op.drop_index('ix_performance_records_production_record_id', table_name='performance_records')
    op.drop_constraint('fk_performance_records_production_record_id', 'performance_records', type_='foreignkey')
    op.drop_column('performance_records', 'production_record_id')

    op.drop_table('production_records')
    op.drop_table('foreman_work_calendar')
    op.drop_table('company_calendar')
    op.drop_table('production_lines')
    op.drop_table('products')

    postgresql.ENUM(name='production_source_system').drop(op.get_bind(), checkfirst=True)
