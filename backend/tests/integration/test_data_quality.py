from app.db.session import SessionLocal
from app.services.ingestion import backfill_data_quality_issues


class TestBackfillIdempotency:
    def test_running_backfill_twice_second_time_creates_nothing_new(self):
        db = SessionLocal()
        try:
            backfill_data_quality_issues(db)
            second_run_count = backfill_data_quality_issues(db)
            assert second_run_count == 0
        finally:
            db.close()
