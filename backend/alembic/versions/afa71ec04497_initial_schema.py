from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'afa71ec04497'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('foremen',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('employee_number', sa.String(length=30), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=False),
    sa.Column('last_name', sa.String(length=100), nullable=False),
    sa.Column('hire_date', sa.Date(), nullable=False),
    sa.Column('termination_date', sa.Date(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('sap_personnel_number', sa.String(length=30), nullable=True),
    sa.Column('photo_url', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_foremen_employee_number'), 'foremen', ['employee_number'], unique=True)
    op.create_table('integration_runs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('source_system', sa.Enum('SYNTHETIC', 'SAP', name='run_source_system'), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.Enum('RUNNING', 'SUCCESS', 'PARTIAL_SUCCESS', 'FAILED', name='integration_status'), nullable=False),
    sa.Column('processed_count', sa.Integer(), nullable=False),
    sa.Column('success_count', sa.Integer(), nullable=False),
    sa.Column('error_count', sa.Integer(), nullable=False),
    sa.Column('skipped_count', sa.Integer(), nullable=False),
    sa.Column('notes', sa.String(length=2000), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('kpis',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('code', sa.String(length=30), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('description', sa.String(length=1000), nullable=True),
    sa.Column('unit', sa.String(length=30), nullable=False),
    sa.Column('calculation_type', sa.Enum('HIGHER_IS_BETTER', 'LOWER_IS_BETTER', 'RANGE_TARGET', 'DIRECT_SCORE', 'PROPORTIONAL_PENALTY', 'CUSTOM_FORMULA', name='calculation_type'), nullable=False),
    sa.Column('success_direction_higher', sa.Boolean(), nullable=False),
    sa.Column('default_target_value', sa.Numeric(precision=12, scale=4), nullable=False),
    sa.Column('min_valid_value', sa.Numeric(precision=12, scale=4), nullable=False),
    sa.Column('max_valid_value', sa.Numeric(precision=12, scale=4), nullable=False),
    sa.Column('min_score', sa.Numeric(precision=6, scale=2), nullable=False),
    sa.Column('max_score', sa.Numeric(precision=6, scale=2), nullable=False),
    sa.Column('weight', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('valid_from', sa.Date(), nullable=False),
    sa.Column('valid_to', sa.Date(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('source_data_field', sa.String(length=100), nullable=True),
    sa.Column('aggregation_method', sa.Enum('SUM', 'AVERAGE', 'WEIGHTED_AVERAGE', 'MIN', 'MAX', 'LAST_VALUE', 'RATIO_RECOMPUTE', name='aggregation_method'), nullable=False),
    sa.Column('decimal_places', sa.Integer(), nullable=False),
    sa.Column('is_critical', sa.Boolean(), nullable=False),
    sa.Column('display_order', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_kpis_code'), 'kpis', ['code'], unique=True)
    op.create_table('performance_level_rules',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('min_score', sa.Numeric(precision=6, scale=2), nullable=False),
    sa.Column('max_score', sa.Numeric(precision=6, scale=2), nullable=False),
    sa.Column('description', sa.String(length=500), nullable=False),
    sa.Column('color', sa.String(length=20), nullable=False),
    sa.Column('icon', sa.String(length=50), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('plants',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('code', sa.String(length=20), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('city', sa.String(length=100), nullable=False),
    sa.Column('region', sa.String(length=100), nullable=False),
    sa.Column('description', sa.String(length=1000), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('sap_plant_code', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_plants_code'), 'plants', ['code'], unique=True)
    op.create_index(op.f('ix_plants_region'), 'plants', ['region'], unique=False)
    op.create_table('shifts',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('code', sa.String(length=20), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('start_time', sa.Time(), nullable=False),
    sa.Column('end_time', sa.Time(), nullable=False),
    sa.Column('sequence', sa.Integer(), nullable=False),
    sa.Column('crosses_midnight', sa.Boolean(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=200), nullable=False),
    sa.Column('full_name', sa.String(length=200), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('failed_login_attempts', sa.Integer(), nullable=False),
    sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_table('audit_logs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('action', sa.String(length=100), nullable=False),
    sa.Column('entity', sa.String(length=100), nullable=True),
    sa.Column('old_value', sa.String(length=2000), nullable=True),
    sa.Column('new_value', sa.String(length=2000), nullable=True),
    sa.Column('ip_address', postgresql.INET(), nullable=True),
    sa.Column('session_info', sa.String(length=200), nullable=True),
    sa.Column('success', sa.Boolean(), nullable=False),
    sa.Column('error_message', sa.String(length=1000), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    op.create_table('departments',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('plant_id', sa.UUID(), nullable=False),
    sa.Column('code', sa.String(length=20), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('description', sa.String(length=1000), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_departments_plant_id'), 'departments', ['plant_id'], unique=False)
    op.create_table('kpi_calculation_rules',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('kpi_id', sa.UUID(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('calculation_type', sa.Enum('HIGHER_IS_BETTER', 'LOWER_IS_BETTER', 'RANGE_TARGET', 'DIRECT_SCORE', 'PROPORTIONAL_PENALTY', 'CUSTOM_FORMULA', name='calc_rule_type'), nullable=False),
    sa.Column('parameters', sa.JSON(), nullable=False),
    sa.Column('valid_from', sa.Date(), nullable=False),
    sa.Column('valid_to', sa.Date(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['kpi_id'], ['kpis.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_kpi_calculation_rules_kpi_id'), 'kpi_calculation_rules', ['kpi_id'], unique=False)
    op.create_table('kpi_targets',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('kpi_id', sa.UUID(), nullable=False),
    sa.Column('scope_type', sa.Enum('COMPANY', 'PLANT', 'DEPARTMENT', 'LINE', 'SHIFT', 'FOREMAN', name='target_scope_type'), nullable=False),
    sa.Column('scope_id', sa.UUID(), nullable=True),
    sa.Column('target_value', sa.Numeric(precision=12, scale=4), nullable=False),
    sa.Column('valid_from', sa.Date(), nullable=False),
    sa.Column('valid_to', sa.Date(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['kpi_id'], ['kpis.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_kpi_targets_kpi_id'), 'kpi_targets', ['kpi_id'], unique=False)
    op.create_index(op.f('ix_kpi_targets_scope_id'), 'kpi_targets', ['scope_id'], unique=False)
    op.create_table('production_lines',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('plant_id', sa.UUID(), nullable=False),
    sa.Column('department_id', sa.UUID(), nullable=False),
    sa.Column('code', sa.String(length=20), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('capacity', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('sap_work_center_code', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
    sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_production_lines_department_id'), 'production_lines', ['department_id'], unique=False)
    op.create_index(op.f('ix_production_lines_plant_id'), 'production_lines', ['plant_id'], unique=False)
    op.create_table('foreman_assignments',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('foreman_id', sa.UUID(), nullable=False),
    sa.Column('plant_id', sa.UUID(), nullable=False),
    sa.Column('department_id', sa.UUID(), nullable=False),
    sa.Column('production_line_id', sa.UUID(), nullable=False),
    sa.Column('shift_id', sa.UUID(), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
    sa.ForeignKeyConstraint(['foreman_id'], ['foremen.id'], ),
    sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], ),
    sa.ForeignKeyConstraint(['production_line_id'], ['production_lines.id'], ),
    sa.ForeignKeyConstraint(['shift_id'], ['shifts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_foreman_assignments_end_date'), 'foreman_assignments', ['end_date'], unique=False)
    op.create_index(op.f('ix_foreman_assignments_foreman_id'), 'foreman_assignments', ['foreman_id'], unique=False)
    op.create_index(op.f('ix_foreman_assignments_plant_id'), 'foreman_assignments', ['plant_id'], unique=False)
    op.create_index(op.f('ix_foreman_assignments_start_date'), 'foreman_assignments', ['start_date'], unique=False)
    op.create_table('performance_records',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('source_system', sa.Enum('SYNTHETIC', 'SAP', name='source_system'), nullable=False),
    sa.Column('source_record_id', sa.String(length=100), nullable=False),
    sa.Column('integration_run_id', sa.UUID(), nullable=False),
    sa.Column('performance_date', sa.Date(), nullable=False),
    sa.Column('plant_id', sa.UUID(), nullable=False),
    sa.Column('department_id', sa.UUID(), nullable=False),
    sa.Column('production_line_id', sa.UUID(), nullable=False),
    sa.Column('shift_id', sa.UUID(), nullable=False),
    sa.Column('foreman_id', sa.UUID(), nullable=False),
    sa.Column('kpi_id', sa.UUID(), nullable=False),
    sa.Column('target_value', sa.Numeric(precision=14, scale=4), nullable=True),
    sa.Column('actual_value', sa.Numeric(precision=14, scale=4), nullable=True),
    sa.Column('numerator_value', sa.Numeric(precision=14, scale=4), nullable=True),
    sa.Column('denominator_value', sa.Numeric(precision=14, scale=4), nullable=True),
    sa.Column('unit', sa.String(length=30), nullable=False),
    sa.Column('data_quality_status', sa.Enum('COMPLETE', 'MISSING', 'INVALID', 'SUSPICIOUS', 'DUPLICATE', 'NEEDS_SOURCE_CORRECTION', 'PENDING_RESYNC', 'REPROCESSED', name='data_quality_status'), nullable=False),
    sa.Column('source_updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('imported_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
    sa.ForeignKeyConstraint(['foreman_id'], ['foremen.id'], ),
    sa.ForeignKeyConstraint(['integration_run_id'], ['integration_runs.id'], ),
    sa.ForeignKeyConstraint(['kpi_id'], ['kpis.id'], ),
    sa.ForeignKeyConstraint(['plant_id'], ['plants.id'], ),
    sa.ForeignKeyConstraint(['production_line_id'], ['production_lines.id'], ),
    sa.ForeignKeyConstraint(['shift_id'], ['shifts.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('foreman_id', 'kpi_id', 'production_line_id', 'shift_id', 'performance_date', name='uq_perf_record_natural_key'),
    sa.UniqueConstraint('source_system', 'source_record_id', name='uq_perf_record_source')
    )
    op.create_index(op.f('ix_performance_records_department_id'), 'performance_records', ['department_id'], unique=False)
    op.create_index(op.f('ix_performance_records_foreman_id'), 'performance_records', ['foreman_id'], unique=False)
    op.create_index(op.f('ix_performance_records_integration_run_id'), 'performance_records', ['integration_run_id'], unique=False)
    op.create_index(op.f('ix_performance_records_kpi_id'), 'performance_records', ['kpi_id'], unique=False)
    op.create_index(op.f('ix_performance_records_performance_date'), 'performance_records', ['performance_date'], unique=False)
    op.create_index(op.f('ix_performance_records_plant_id'), 'performance_records', ['plant_id'], unique=False)
    op.create_index(op.f('ix_performance_records_production_line_id'), 'performance_records', ['production_line_id'], unique=False)
    op.create_index(op.f('ix_performance_records_shift_id'), 'performance_records', ['shift_id'], unique=False)
    op.create_index(op.f('ix_performance_records_source_record_id'), 'performance_records', ['source_record_id'], unique=False)
    op.create_table('data_quality_issues',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('performance_record_id', sa.UUID(), nullable=True),
    sa.Column('issue_type', sa.Enum('COMPLETE', 'MISSING', 'INVALID', 'SUSPICIOUS', 'DUPLICATE', 'NEEDS_SOURCE_CORRECTION', 'PENDING_RESYNC', 'REPROCESSED', name='issue_type'), nullable=False),
    sa.Column('description', sa.String(length=1000), nullable=False),
    sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['performance_record_id'], ['performance_records.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_quality_issues_performance_record_id'), 'data_quality_issues', ['performance_record_id'], unique=False)
    op.create_table('performance_scores',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('performance_record_id', sa.UUID(), nullable=False),
    sa.Column('calculation_rule_id', sa.UUID(), nullable=False),
    sa.Column('raw_score', sa.Numeric(precision=8, scale=3), nullable=False),
    sa.Column('capped_score', sa.Numeric(precision=8, scale=3), nullable=False),
    sa.Column('kpi_weight', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('weighted_contribution', sa.Numeric(precision=8, scale=3), nullable=False),
    sa.Column('calculation_version', sa.Integer(), nullable=False),
    sa.Column('calculated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['calculation_rule_id'], ['kpi_calculation_rules.id'], ),
    sa.ForeignKeyConstraint(['performance_record_id'], ['performance_records.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_performance_scores_performance_record_id'), 'performance_scores', ['performance_record_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_performance_scores_performance_record_id'), table_name='performance_scores')
    op.drop_table('performance_scores')
    op.drop_index(op.f('ix_data_quality_issues_performance_record_id'), table_name='data_quality_issues')
    op.drop_table('data_quality_issues')
    op.drop_index(op.f('ix_performance_records_source_record_id'), table_name='performance_records')
    op.drop_index(op.f('ix_performance_records_shift_id'), table_name='performance_records')
    op.drop_index(op.f('ix_performance_records_production_line_id'), table_name='performance_records')
    op.drop_index(op.f('ix_performance_records_plant_id'), table_name='performance_records')
    op.drop_index(op.f('ix_performance_records_performance_date'), table_name='performance_records')
    op.drop_index(op.f('ix_performance_records_kpi_id'), table_name='performance_records')
    op.drop_index(op.f('ix_performance_records_integration_run_id'), table_name='performance_records')
    op.drop_index(op.f('ix_performance_records_foreman_id'), table_name='performance_records')
    op.drop_index(op.f('ix_performance_records_department_id'), table_name='performance_records')
    op.drop_table('performance_records')
    op.drop_index(op.f('ix_foreman_assignments_start_date'), table_name='foreman_assignments')
    op.drop_index(op.f('ix_foreman_assignments_plant_id'), table_name='foreman_assignments')
    op.drop_index(op.f('ix_foreman_assignments_foreman_id'), table_name='foreman_assignments')
    op.drop_index(op.f('ix_foreman_assignments_end_date'), table_name='foreman_assignments')
    op.drop_table('foreman_assignments')
    op.drop_index(op.f('ix_production_lines_plant_id'), table_name='production_lines')
    op.drop_index(op.f('ix_production_lines_department_id'), table_name='production_lines')
    op.drop_table('production_lines')
    op.drop_index(op.f('ix_kpi_targets_scope_id'), table_name='kpi_targets')
    op.drop_index(op.f('ix_kpi_targets_kpi_id'), table_name='kpi_targets')
    op.drop_table('kpi_targets')
    op.drop_index(op.f('ix_kpi_calculation_rules_kpi_id'), table_name='kpi_calculation_rules')
    op.drop_table('kpi_calculation_rules')
    op.drop_index(op.f('ix_departments_plant_id'), table_name='departments')
    op.drop_table('departments')
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_table('shifts')
    op.drop_index(op.f('ix_plants_region'), table_name='plants')
    op.drop_index(op.f('ix_plants_code'), table_name='plants')
    op.drop_table('plants')
    op.drop_table('performance_level_rules')
    op.drop_index(op.f('ix_kpis_code'), table_name='kpis')
    op.drop_table('kpis')
    op.drop_table('integration_runs')
    op.drop_index(op.f('ix_foremen_employee_number'), table_name='foremen')
    op.drop_table('foremen')
