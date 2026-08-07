from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a1b3c5d7e9f2'
down_revision: Union[str, None] = 'c3e5f7a9b1d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Bir şef artık tek bir tesise değil, tesislerden oluşan sabit bir bölgeye ("zone")
    # sorumludur; bir formen bu bölgedeki tüm tesislerden sorumlu olsa da her zaman TEK bir
    # şefe bağlıdır (bkz. reference_data.py::seed_reference_data). Eski modelde (1 tesis = 1
    # şef) bir formenin 2-4 tesise yayılan ataması, her tesisin kendi şefine bağlı kaldığından
    # bir formeni aynı anda birden fazla şefe bağlayabiliyordu. Organizasyon kimlikleri kökten
    # değiştiği için (şefler artık tesis değil bölge bazlı numaralanıyor) mevcut veri
    # anlamsızlaşır — Karaman restrukturasyonuyla (6ad63dbc115b) aynı gerekçeyle TRUNCATE edilir.
    op.execute(
        "TRUNCATE TABLE factories, plants, chiefs, foremen, kpi_targets, integration_runs, "
        "shifts, kpis, performance_level_rules, products, company_calendar CASCADE"
    )

    op.drop_constraint('fk_foreman_assignments_chief_plant', 'foreman_assignments', type_='foreignkey')
    op.drop_index('ix_chiefs_plant_id', table_name='chiefs')
    op.drop_constraint('uq_chiefs_id_plant_id', 'chiefs', type_='unique')
    op.drop_column('chiefs', 'plant_id')

    op.add_column('plants', sa.Column('chief_id', sa.UUID(), nullable=False))
    op.create_index(op.f('ix_plants_chief_id'), 'plants', ['chief_id'], unique=False)
    op.create_foreign_key(None, 'plants', 'chiefs', ['chief_id'], ['id'])
    op.create_unique_constraint('uq_plants_id_chief_id', 'plants', ['id', 'chief_id'])

    # Formenin (plant_id, chief_id) çifti her zaman tesisin gerçek şefiyle eşleşir — bu artık
    # foreman_assignments için olduğu gibi foreman_work_calendar ve production_records için de
    # DB seviyesinde garanti edilir (üretici kod zaten tutarlı üretiyordu, bu yalnızca invariant'ı
    # şemaya taşır). Kompozit FK yalnızca plants'ı hedeflediği için (chiefs'i değil), ORM'nin
    # Chief.assignments ilişkisini kurabilmesi için chief_id ayrıca chiefs.id'ye düz bir FK ile
    # bağlanır (eski şemada tek kompozit FK chiefs(id, plant_id)'yi hedeflediğinden buna gerek
    # yoktu).
    op.create_foreign_key(None, 'foreman_assignments', 'chiefs', ['chief_id'], ['id'])
    op.create_foreign_key(
        'fk_foreman_assignments_plant_chief', 'foreman_assignments', 'plants',
        ['plant_id', 'chief_id'], ['id', 'chief_id'],
    )
    op.create_foreign_key(
        'fk_foreman_work_calendar_plant_chief', 'foreman_work_calendar', 'plants',
        ['plant_id', 'chief_id'], ['id', 'chief_id'],
    )
    op.create_foreign_key(
        'fk_production_records_plant_chief', 'production_records', 'plants',
        ['plant_id', 'chief_id'], ['id', 'chief_id'],
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Bu migration geri alınamaz: şef/tesis organizasyon verisini ve ona bağlı tüm "
        "performans/üretim kayıtlarını TRUNCATE ile kalıcı olarak siler."
    )
