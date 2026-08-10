
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone

from sqlalchemy import event, select

from app.core.security import hash_password
from app.db.session import engine
from app.models.enums import ReportFormat, ReportStatus, ReportType
from app.models.foreman import Foreman
from app.models.organization import Plant
from app.models.report import ReportExport
from app.models.user import User

from .conftest import TEST_EMAIL


@contextmanager
def count_queries():
    counter = {"n": 0}

    def _on_execute(conn, cursor, statement, parameters, context, executemany):
        counter["n"] += 1

    event.listen(engine, "before_cursor_execute", _on_execute)
    try:
        yield counter
    finally:
        event.remove(engine, "before_cursor_execute", _on_execute)


class TestReportListQueryCount:
    def test_query_count_does_not_scale_with_distinct_requesters(self, client, auth_headers, db_session):
        # `/reports/generate` her zaman TEK bir current_user kullanır — tek başına yeterli bir
        # test değil, çünkü aynı id'ye tekrar tekrar `db.get()` identity-map'ten bedava döner
        # (eski koddaki N+1'i gizler). Farklı istekçileri gerçekten ayırt etmek için satırlar
        # burada FARKLI kullanıcılarla doğrudan ekleniyor.
        now = datetime.now(timezone.utc)
        new_ids = []
        for i in range(6):
            user = User(
                id=uuid.uuid4(), email=f"n1-report-test-{uuid.uuid4().hex[:8]}@formen-demo.com",
                password_hash=hash_password("x"), full_name=f"N+1 Test Kullanıcısı {i}", is_active=True,
            )
            db_session.add(user)
            db_session.flush()
            export = ReportExport(
                id=uuid.uuid4(), report_type=ReportType.COMPANY_SUMMARY, format=ReportFormat.CSV,
                filters_json={}, requested_by_user_id=user.id,
                file_name=f"n1-test-{i}.csv", file_content=b"x", row_count=0,
                status=ReportStatus.COMPLETED, completed_at=now,
            )
            db_session.add(export)
            new_ids.append((user.id, export.id))
        db_session.commit()

        try:
            with count_queries() as counter:
                resp = client.get("/api/v1/reports", params={"page_size": 200}, headers=auth_headers)
            assert resp.status_code == 200
            returned_ids = {i["id"] for i in resp.json()["items"]}
            assert all(str(eid) in returned_ids for _, eid in new_ids)
            # Eski kodda rapor başına ayrı bir db.get(User, ...) vardı; 6 FARKLI istekçi eski
            # koddan en az +6 sorgu üretirdi. Artık istekçiler tek bir IN (...) sorgusuyla toplu
            # çekiliyor, sorgu sayısı istekçi çeşitliliğinden bağımsız kalmalı.
            assert counter["n"] <= 6, f"Beklenenden fazla sorgu: {counter['n']}"
        finally:
            db_session.execute(ReportExport.__table__.delete().where(ReportExport.id.in_([eid for _, eid in new_ids])))
            db_session.execute(User.__table__.delete().where(User.id.in_([uid for uid, _ in new_ids])))
            db_session.commit()


class TestContributionSummaryQueryCount:
    def test_query_count_does_not_scale_with_work_count(self, client, auth_headers, db_session):
        foremen = list(db_session.scalars(select(Foreman).where(Foreman.is_active.is_(True)).limit(5)))
        plants = list(db_session.scalars(select(Plant).order_by(Plant.sequence_number).limit(5)))
        assert len(foremen) >= 5 and len(plants) >= 5

        # Bkz. TestReportListQueryCount'taki aynı not: benzersiz jeton, önceki koşumlardan
        # kalan kayıtların tam eşitlik doğrulamalarını bozmasını engeller.
        token = uuid.uuid4().hex[:8]
        for i in range(5):
            resp = client.post(
                "/api/v1/contribution-works",
                json={
                    "title": f"N+1 özet testi {token} #{i}", "status": "published", "work_type": "kaizen",
                    "summary": "s", "problem_description": "p", "solution_description": "s",
                    "foreman_ids": [str(foremen[i].id)], "plant_id": str(plants[i].id),
                    "work_date": date.today().isoformat(), "impact_level": "medium",
                },
                headers=auth_headers,
            )
            assert resp.status_code == 201, resp.text

        with count_queries() as counter:
            resp = client.get(
                "/api/v1/contribution-works/summary", params={"search": f"N+1 özet testi {token}"}, headers=auth_headers
            )
        assert resp.status_code == 200
        assert resp.json()["total_works"] == 5
        # Eski kodda çalışma başına ayrı bir ContributionWorkForeman sorgusu vardı (ve bu endpoint
        # sayfalanmıyor) — artık tek bir IN (...) sorgusuyla toplu çekiliyor.
        assert counter["n"] <= 6, f"Beklenenden fazla sorgu: {counter['n']}"
