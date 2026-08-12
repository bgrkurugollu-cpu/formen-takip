import json
import uuid
from datetime import date
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd4f6a8b1c3e5'
down_revision: Union[str, None] = 'a1b3c5d7e9f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TODAY = date.today().isoformat()

_V3_PARAMS = {
    'formula_type': 'ASYMMETRIC_PLAN_ACHIEVEMENT',
    'target_score': 100,
    'positive_linear_limit': 5.0,
    'positive_points_per_percentage_point': 1.0,
    'positive_log_coefficient': 5.0,
    'negative_linear_limit': 5.0,
    'negative_points_per_percentage_point': 1.0,
    'negative_log_coefficient': 10.0,
    'minimum_score': 0,
    'maximum_score': None,
}


def upgrade() -> None:
    bind = op.get_bind()

    existing_kpi_count = bind.execute(sa.text("SELECT count(*) FROM kpis WHERE code = 'PLANA_UYUM'")).scalar()
    if not existing_kpi_count:
        return

    next_version = bind.execute(sa.text(
        """
        SELECT COALESCE(MAX(kcr.version), 0) + 1
        FROM kpi_calculation_rules kcr
        JOIN kpis k ON k.id = kcr.kpi_id
        WHERE k.code = 'PLANA_UYUM'
        """
    )).scalar()

    bind.execute(sa.text(
        """
        UPDATE kpi_calculation_rules
        SET is_active = false, valid_to = :today, updated_at = now()
        WHERE is_active = true AND kpi_id = (SELECT id FROM kpis WHERE code = 'PLANA_UYUM')
        """
    ), {"today": _TODAY})

    bind.execute(sa.text(
        """
        INSERT INTO kpi_calculation_rules (
            id, kpi_id, version, calculation_type, parameters, valid_from, valid_to, is_active,
            created_at, updated_at
        )
        SELECT gen_random_uuid(), id, :version, 'CUSTOM_FORMULA'::calc_rule_type, CAST(:params AS json), :valid_from, NULL, true, now(), now()
        FROM kpis WHERE code = 'PLANA_UYUM'
        """
    ), {"version": next_version, "params": json.dumps(_V3_PARAMS), "valid_from": _TODAY})

    bind.execute(sa.text(
        """
        UPDATE kpis
        SET description = 'Gerçekleşen üretimin, güncel (revize) üretim planına göre yönlü sapması '
            || '(planın üzerinde üretim ödüllendirilir, planın altında üretim daha güçlü cezalandırılır).',
            updated_at = now()
        WHERE code = 'PLANA_UYUM'
        """
    ))


def downgrade() -> None:
    bind = op.get_bind()

    existing_kpi_count = bind.execute(sa.text("SELECT count(*) FROM kpis WHERE code = 'PLANA_UYUM'")).scalar()
    if not existing_kpi_count:
        return

    bind.execute(sa.text(
        """
        DELETE FROM kpi_calculation_rules
        WHERE kpi_id = (SELECT id FROM kpis WHERE code = 'PLANA_UYUM')
          AND parameters->>'formula_type' = 'ASYMMETRIC_PLAN_ACHIEVEMENT'
        """
    ))
    bind.execute(sa.text(
        """
        UPDATE kpi_calculation_rules
        SET is_active = true, valid_to = NULL, updated_at = now()
        WHERE kpi_id = (SELECT id FROM kpis WHERE code = 'PLANA_UYUM')
          AND version = (
              SELECT MAX(kcr.version) FROM kpi_calculation_rules kcr
              JOIN kpis k ON k.id = kcr.kpi_id
              WHERE k.code = 'PLANA_UYUM' AND kcr.parameters->>'formula_type' = 'PIECEWISE_LINEAR_LOGARITHMIC'
          )
        """
    ))
    bind.execute(sa.text(
        """
        UPDATE kpis
        SET description = 'Gerçekleşen üretimin, güncel (revize) üretim planına göre mutlak sapması '
            || '(plan altı ve plan üstü eşit ağırlıkta sapma sayılır).',
            updated_at = now()
        WHERE code = 'PLANA_UYUM'
        """
    ))
