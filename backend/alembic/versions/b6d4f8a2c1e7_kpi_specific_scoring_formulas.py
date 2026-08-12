import json
import uuid
from datetime import date
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b6d4f8a2c1e7'
down_revision: Union[str, None] = 'c7a1f9d0b2e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TODAY = date.today().isoformat()

_V2_RULE_PARAMS = {
    'AGIR_GITME': {
        'formula_type': 'SIGNED_ABSOLUTE_PIECEWISE',
        'good_coefficient': 9,
        'bad_coefficient': 12,
    },
    'GSF': {
        'formula_type': 'HYBRID_BASE_PIECEWISE_LOG',
        'minimum_normalization_base': 0.05,
        'good_coefficient': 10,
        'bad_coefficient': 16,
    },
    'ISKARTA': {
        'formula_type': 'TARGET_RATIO_PIECEWISE',
        'good_coefficient': 12,
        'bad_coefficient': 12,
    },
    'PLANA_UYUM': {
        'formula_type': 'PIECEWISE_LINEAR_LOGARITHMIC',
        'normal_deviation_limit': 5.00,
        'excess_deviation_coefficient': 10.00,
    },
}

_INKITA_RULE_PARAMS = {
    'formula_type': 'HYBRID_BASE_PIECEWISE_LOG',
    'included_components': ['TECHNICAL', 'MANUFACTURING'],
    'excluded_components': ['OTHER'],
    'minimum_normalization_base': 0.50,
    'good_coefficient': 6,
    'bad_coefficient': 10,
}


def upgrade() -> None:
    bind = op.get_bind()

    existing_kpi_count = bind.execute(sa.text("SELECT count(*) FROM kpis")).scalar()
    if not existing_kpi_count:
        return

    bind.execute(sa.text(
        """
        UPDATE kpi_calculation_rules
        SET is_active = false, valid_to = :today, updated_at = now()
        WHERE is_active = true
          AND kpi_id IN (SELECT id FROM kpis WHERE code IN ('PLANLI_INKITA', 'PLANSIZ_INKITA'))
        """
    ), {"today": _TODAY})
    bind.execute(sa.text(
        """
        UPDATE kpis
        SET is_active = false, valid_to = :today, updated_at = now()
        WHERE code IN ('PLANLI_INKITA', 'PLANSIZ_INKITA')
        """
    ), {"today": _TODAY})

    inkita_kpi_id = str(uuid.uuid4())
    bind.execute(sa.text(
        """
        INSERT INTO kpis (
            id, code, name, description, unit, calculation_type, success_direction_higher,
            default_target_value, min_valid_value, max_valid_value, min_score, max_score, weight,
            valid_from, is_active, source_data_field, aggregation_method, decimal_places, is_critical,
            display_order, created_at, updated_at
        ) VALUES (
            :id, 'INKITA', 'İnkita Oranı',
            'Teknik ve imalat kaynaklı duruş sürelerinin planlanan üretim süresine oranı (Diğer duruşlar puana dahil edilmez).',
            '%', 'CUSTOM_FORMULA'::calculation_type, false,
            10.0, 0, 100, 0, 999999.99, 20,
            :valid_from, true, NULL, 'RATIO_RECOMPUTE'::aggregation_method, 2, true,
            4, now(), now()
        )
        """
    ), {"id": inkita_kpi_id, "valid_from": _TODAY})

    inkita_rule_id = str(uuid.uuid4())
    bind.execute(sa.text(
        """
        INSERT INTO kpi_calculation_rules (
            id, kpi_id, version, calculation_type, parameters, valid_from, valid_to, is_active,
            created_at, updated_at
        ) VALUES (
            :id, :kpi_id, 1, 'CUSTOM_FORMULA'::calc_rule_type, CAST(:params AS json), :valid_from, NULL, true,
            now(), now()
        )
        """
    ), {"id": inkita_rule_id, "kpi_id": inkita_kpi_id, "params": json.dumps(_INKITA_RULE_PARAMS), "valid_from": _TODAY})

    bind.execute(sa.text(
        """
        INSERT INTO kpi_targets (id, kpi_id, scope_type, scope_id, target_value, valid_from, valid_to, is_active, created_at, updated_at)
        VALUES (:id, :kpi_id, 'COMPANY'::target_scope_type, NULL, 10.0, :valid_from, NULL, true, now(), now())
        """
    ), {"id": str(uuid.uuid4()), "kpi_id": inkita_kpi_id, "valid_from": _TODAY})

    bind.execute(sa.text(
        """
        INSERT INTO kpi_targets (id, kpi_id, scope_type, scope_id, target_value, valid_from, valid_to, is_active, created_at, updated_at)
        SELECT gen_random_uuid(), :kpi_id, 'PLANT'::target_scope_type, combined.scope_id, combined.total, :valid_from, NULL, true, now(), now()
        FROM (
            SELECT t.scope_id AS scope_id, SUM(t.target_value) AS total
            FROM kpi_targets t
            JOIN kpis k ON k.id = t.kpi_id
            WHERE k.code IN ('PLANLI_INKITA', 'PLANSIZ_INKITA')
              AND t.scope_type = 'PLANT'::target_scope_type
              AND t.is_active = true
            GROUP BY t.scope_id
        ) combined
        """
    ), {"kpi_id": inkita_kpi_id, "valid_from": _TODAY})

    for code, params in _V2_RULE_PARAMS.items():
        bind.execute(sa.text(
            """
            UPDATE kpi_calculation_rules
            SET is_active = false, valid_to = :today, updated_at = now()
            WHERE is_active = true AND kpi_id = (SELECT id FROM kpis WHERE code = :code)
            """
        ), {"today": _TODAY, "code": code})
        bind.execute(sa.text(
            """
            UPDATE kpis
            SET calculation_type = 'CUSTOM_FORMULA'::calculation_type, updated_at = now()
            WHERE code = :code
            """
        ), {"code": code})
        bind.execute(sa.text(
            """
            INSERT INTO kpi_calculation_rules (
                id, kpi_id, version, calculation_type, parameters, valid_from, valid_to, is_active,
                created_at, updated_at
            )
            SELECT gen_random_uuid(), id, 2, 'CUSTOM_FORMULA'::calc_rule_type, CAST(:params AS json), :valid_from, NULL, true, now(), now()
            FROM kpis WHERE code = :code
            """
        ), {"params": json.dumps(params), "valid_from": _TODAY, "code": code})

    bind.execute(sa.text("UPDATE kpis SET min_valid_value = -100, updated_at = now() WHERE code = 'AGIR_GITME'"))

    bind.execute(sa.text("UPDATE kpis SET display_order = 5, updated_at = now() WHERE code = 'PLANA_UYUM'"))


def downgrade() -> None:
    bind = op.get_bind()

    bind.execute(sa.text("UPDATE kpis SET display_order = 6, updated_at = now() WHERE code = 'PLANA_UYUM'"))
    bind.execute(sa.text("UPDATE kpis SET min_valid_value = 0, updated_at = now() WHERE code = 'AGIR_GITME'"))

    for code, calc_type in (
        ('AGIR_GITME', 'lower_is_better'),
        ('GSF', 'lower_is_better'),
        ('ISKARTA', 'lower_is_better'),
        ('PLANA_UYUM', 'higher_is_better'),
    ):
        bind.execute(sa.text(
            """
            DELETE FROM kpi_calculation_rules
            WHERE version = 2 AND kpi_id = (SELECT id FROM kpis WHERE code = :code)
            """
        ), {"code": code})
        bind.execute(sa.text(
            "UPDATE kpis SET calculation_type = CAST(:t AS calculation_type), updated_at = now() WHERE code = :code"
        ), {"t": calc_type, "code": code})
        bind.execute(sa.text(
            """
            UPDATE kpi_calculation_rules
            SET is_active = true, valid_to = NULL, updated_at = now()
            WHERE version = 1 AND kpi_id = (SELECT id FROM kpis WHERE code = :code)
            """
        ), {"code": code})

    bind.execute(sa.text(
        "DELETE FROM kpi_targets WHERE kpi_id = (SELECT id FROM kpis WHERE code = 'INKITA')"
    ))
    bind.execute(sa.text(
        "DELETE FROM kpi_calculation_rules WHERE kpi_id = (SELECT id FROM kpis WHERE code = 'INKITA')"
    ))
    bind.execute(sa.text("DELETE FROM kpis WHERE code = 'INKITA'"))

    bind.execute(sa.text(
        """
        UPDATE kpi_calculation_rules
        SET is_active = true, valid_to = NULL, updated_at = now()
        WHERE kpi_id IN (SELECT id FROM kpis WHERE code IN ('PLANLI_INKITA', 'PLANSIZ_INKITA'))
        """
    ))
    bind.execute(sa.text(
        """
        UPDATE kpis
        SET is_active = true, valid_to = NULL, updated_at = now()
        WHERE code IN ('PLANLI_INKITA', 'PLANSIZ_INKITA')
        """
    ))
