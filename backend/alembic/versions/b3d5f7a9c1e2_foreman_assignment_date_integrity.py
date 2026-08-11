from typing import Sequence, Union

from alembic import op

revision: str = 'b3d5f7a9c1e2'
down_revision: Union[str, None] = 'a2c4e6f8b0d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_check_constraint(
        'ck_foreman_assignments_date_range',
        'foreman_assignments',
        'end_date IS NULL OR end_date >= start_date',
    )
    op.create_check_constraint(
        'ck_foreman_assignments_inactive_has_end_date',
        'foreman_assignments',
        'is_active = true OR end_date IS NOT NULL',
    )

    op.execute(
        """
        ALTER TABLE foreman_assignments
        ADD CONSTRAINT excl_foreman_assignments_plant_shift_daterange
        EXCLUDE USING gist (
            plant_id WITH =,
            shift_id WITH =,
            daterange(start_date, end_date, '[]') WITH &&
        )
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION enforce_foreman_single_chief() RETURNS trigger AS $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM foreman_assignments
                WHERE foreman_id = NEW.foreman_id
                  AND chief_id <> NEW.chief_id
                  AND id <> NEW.id
            ) THEN
                RAISE EXCEPTION
                    'Formen % zaten farklı bir şefe bağlı (chief_id=%) — bir formen birden fazla şefe atanamaz.',
                    NEW.foreman_id, NEW.chief_id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_foreman_assignments_single_chief
        BEFORE INSERT OR UPDATE OF chief_id, foreman_id ON foreman_assignments
        FOR EACH ROW EXECUTE FUNCTION enforce_foreman_single_chief()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_foreman_assignments_single_chief ON foreman_assignments")
    op.execute("DROP FUNCTION IF EXISTS enforce_foreman_single_chief()")
    op.execute("ALTER TABLE foreman_assignments DROP CONSTRAINT excl_foreman_assignments_plant_shift_daterange")
    op.drop_constraint('ck_foreman_assignments_inactive_has_end_date', 'foreman_assignments', type_='check')
    op.drop_constraint('ck_foreman_assignments_date_range', 'foreman_assignments', type_='check')
