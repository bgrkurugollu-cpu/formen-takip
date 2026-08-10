"""foreman_assignments date-range integrity.

Closes four gaps in `ForemanAssignment` that were never enforced at the DB level:

1. `start_date <= end_date` had no CHECK — a corrupted or manually-edited row could have an
   end before its start with nothing to catch it.
2. `is_active = false` with `end_date IS NULL` is always inconsistent (an inactive assignment
   must record when it ended) — also a plain CHECK.
3. The existing partial unique index (`uq_foreman_assignments_plant_shift_active`, migration
   `b7c9e1a3d5f2`) only guards *active* rows — nothing stopped two rows (e.g. both inactive, or
   one active/one historical) from claiming overlapping date ranges for the same plant+shift.
   Fixed with a range-overlap EXCLUDE constraint (requires `btree_gist` for the uuid equality
   terms alongside the `daterange` overlap term). This matters concretely: `assignment_resolver.
   resolve_assignment` (added for the ingestion assignment-validity check) takes the *first*
   matching candidate for a foreman+plant+date — an undetected historical overlap would make
   that pick arbitrary.
4. Nothing enforced "a foreman reports to exactly one chief" (see CLAUDE.md) — two
   `foreman_assignments` rows for the same foreman could reference different chiefs. Enforced
   with a trigger, since a cross-row-per-foreign-key invariant like this has no direct
   CHECK/UNIQUE/EXCLUDE representation.

Existing data already satisfies all four constraints (verified against the live DB before
writing this migration), so no cleanup step is needed.
"""
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
