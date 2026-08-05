from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'e1b2c4d6f8a0'
down_revision: Union[str, None] = 'd3e5a7c9f102'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# NOT: SQLAlchemy'nin Enum tipi, Python enum üyelerini varsayılan olarak `.value` değil
# `.name` ile veritabanına yazar — bu yüzden burada app/models/enums.py'daki üye adları
# (büyük harf) kullanılıyor, `.value` küçük harfleri değil.
ANOMALY_TYPE = (
    'SHIFT_UNDERPERFORMANCE', 'RISING_TREND', 'FOREMAN_DEVIATION', 'PRODUCT_GROUP_DEVIATION',
    'DOWNTIME_CONCENTRATION', 'PLAN_ADHERENCE_STREAK', 'PLANT_HISTORICAL_DEVIATION',
    'CROSS_PLANT_GAP', 'MULTI_KPI_SIMULTANEOUS', 'SINGLE_DAY_SPIKE', 'CHRONIC_ANOMALY',
    'CRITICAL_PRODUCTION_LOSS', 'DATA_QUALITY_SUSPECT',
)
ANOMALY_SEVERITY = ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')
ANOMALY_STATUS = ('NEW', 'IN_REVIEW', 'ACTION_PENDING', 'RESOLVED', 'CLOSED')
ANOMALY_ANALYSIS_STATUS = ('NOT_ANALYZED', 'ANALYZING', 'COMPLETED', 'FAILED')
ANOMALY_ANALYSIS_RUN_STATUS = ('NOT_ANALYZED', 'ANALYZING', 'COMPLETED', 'FAILED')

_ENUMS = [
    ('anomaly_type', ANOMALY_TYPE),
    ('anomaly_severity', ANOMALY_SEVERITY),
    ('anomaly_status', ANOMALY_STATUS),
    ('anomaly_analysis_status', ANOMALY_ANALYSIS_STATUS),
    ('anomaly_analysis_run_status', ANOMALY_ANALYSIS_RUN_STATUS),
]


def upgrade() -> None:
    enum_types = {}
    for name, values in _ENUMS:
        enum_type = postgresql.ENUM(*values, name=name, create_type=False)
        enum_type.create(op.get_bind(), checkfirst=True)
        enum_types[name] = enum_type

    op.create_table(
        'anomalies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(length=30), nullable=False, unique=True),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('anomaly_type', enum_types['anomaly_type'], nullable=False),
        sa.Column('severity', enum_types['anomaly_severity'], nullable=False),
        sa.Column('status', enum_types['anomaly_status'], nullable=False),
        sa.Column('analysis_status', enum_types['anomaly_analysis_status'], nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('plant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plants.id'), nullable=False),
        sa.Column('shift_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shifts.id'), nullable=True),
        sa.Column('kpi_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('kpis.id'), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('observed_value', sa.Numeric(12, 4), nullable=False),
        sa.Column('expected_value', sa.Numeric(12, 4), nullable=False),
        sa.Column('unit', sa.String(length=20), nullable=False),
        sa.Column('deviation_percent', sa.Numeric(8, 3), nullable=False),
        sa.Column('ml_confidence', sa.Numeric(5, 4), nullable=False),
        sa.Column('affected_days', sa.Integer(), nullable=True),
        sa.Column('total_days', sa.Integer(), nullable=True),
        sa.Column('comparison', sa.JSON(), nullable=False),
        sa.Column('related_signals', sa.JSON(), nullable=False),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.Column('foreman_ids', sa.JSON(), nullable=False),
        sa.Column('data_quality_status', sa.String(length=20), nullable=False),
        sa.Column('data_quality_warnings', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_anomalies_code', 'anomalies', ['code'])
    op.create_index('ix_anomalies_detected_at', 'anomalies', ['detected_at'])
    op.create_index('ix_anomalies_plant_id', 'anomalies', ['plant_id'])
    op.create_index('ix_anomalies_shift_id', 'anomalies', ['shift_id'])
    op.create_index('ix_anomalies_kpi_id', 'anomalies', ['kpi_id'])

    op.create_table(
        'anomaly_analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(length=30), nullable=False, unique=True),
        sa.Column(
            'anomaly_id', postgresql.UUID(as_uuid=True),
            sa.ForeignKey('anomalies.id', ondelete='CASCADE'), nullable=False,
        ),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('is_demo', sa.Boolean(), nullable=False),
        sa.Column('status', enum_types['anomaly_analysis_run_status'], nullable=False),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('input_snapshot', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_anomaly_analyses_code', 'anomaly_analyses', ['code'])
    op.create_index('ix_anomaly_analyses_anomaly_id', 'anomaly_analyses', ['anomaly_id'])


def downgrade() -> None:
    op.drop_table('anomaly_analyses')
    op.drop_table('anomalies')

    for name, _values in reversed(_ENUMS):
        postgresql.ENUM(name=name).drop(op.get_bind(), checkfirst=True)
