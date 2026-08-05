import uuid

import pytest
from sqlalchemy import select

from app.models.contribution import ContributionWork, ContributionWorkForeman
from app.models.foreman import Foreman
from app.models.organization import Plant
from app.models.user import User

from .conftest import TEST_EMAIL


@pytest.fixture(autouse=True)
def _cleanup_contribution_works(db_session):
    yield
    test_user_id = db_session.scalar(select(User.id).where(User.email == TEST_EMAIL))
    db_session.query(ContributionWork).filter(
        ContributionWork.created_by_user_id == test_user_id
    ).delete(synchronize_session=False)
    db_session.commit()


def _sample_plant_and_foreman(db_session):
    plant = db_session.scalars(select(Plant).order_by(Plant.sequence_number)).first()
    foreman = db_session.scalars(select(Foreman).where(Foreman.is_active.is_(True))).first()
    return plant, foreman


def _full_payload(plant, foreman, status="published"):
    return {
        "title": "Kalıp Değişim Süresinin Kısaltılması",
        "status": status,
        "work_type": "smed",
        "summary": "Kalıp değişim adımları standartlaştırıldı.",
        "problem_description": "Kalıp değişimi uzun sürüyordu.",
        "solution_description": "Adımlar paralel hale getirildi.",
        "result_description": "Süre kısaldı.",
        "foreman_ids": [str(foreman.id)],
        "plant_id": str(plant.id),
        "work_date": "2026-01-15",
        "impact_level": "high",
        "previous_duration": 45,
        "new_duration": 28,
        "duration_unit": "minute",
        "repeat_period": "monthly",
        "repeat_count": 30,
        "financial_gain_status": "yes",
        "estimated_amount": 250000,
        "currency": "TRY",
        "gain_period": "yearly",
    }


class TestContributionWorkList:
    def test_requires_auth(self, client):
        assert client.get("/api/v1/contribution-works").status_code == 401

    def test_list_returns_items(self, client, auth_headers):
        resp = client.get("/api/v1/contribution-works", params={"page_size": 5}, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body and "total" in body


class TestContributionWorkCreate:
    def test_draft_requires_only_title(self, client, auth_headers):
        resp = client.post("/api/v1/contribution-works", json={"title": "Taslak Çalışma"}, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "draft"
        assert body["title"] == "Taslak Çalışma"
        assert body["foremen"] == []

    def test_publish_without_required_fields_returns_422_with_field_errors(self, client, auth_headers):
        resp = client.post(
            "/api/v1/contribution-works",
            json={"title": "Eksik Çalışma", "status": "published"},
            headers=auth_headers,
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert "errors" in detail
        assert "foreman_ids" in detail["errors"]
        assert "plant_id" in detail["errors"]

    def test_publish_with_all_required_fields_succeeds(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        assert plant and foreman
        resp = client.post(
            "/api/v1/contribution-works", json=_full_payload(plant, foreman), headers=auth_headers
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "published"
        assert body["published_at"] is not None
        assert body["foremen"][0]["id"] == str(foreman.id)
        assert body["plant"]["id"] == str(plant.id)

        assert body["per_occurrence_saving"] == 17
        assert body["monthly_total_saving_minutes"] == 510
        assert body["highlighted_gain"]["source"] == "estimated_financial"
        assert body["before_after"]["before"] == "45.0 dakika"
        assert body["before_after"]["after"] == "28.0 dakika"

    def test_created_by_ignores_client_supplied_value(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        payload = {"title": "Sahte kullanıcı testi", "created_by_user_id": str(uuid.uuid4())}
        resp = client.post("/api/v1/contribution-works", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["created_by"]


class TestContributionWorkDetailAndUpdate:
    def test_unknown_id_returns_404(self, client, auth_headers):
        assert client.get(f"/api/v1/contribution-works/{uuid.uuid4()}", headers=auth_headers).status_code == 404

    def test_update_draft_then_publish(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        created = client.post(
            "/api/v1/contribution-works", json={"title": "Aşamalı Yayın Testi"}, headers=auth_headers
        ).json()

        incomplete_publish = client.patch(
            f"/api/v1/contribution-works/{created['id']}", json={"status": "published"}, headers=auth_headers
        )
        assert incomplete_publish.status_code == 422

        full_update = {
            "work_type": "kaizen", "summary": "Özet", "problem_description": "Problem",
            "solution_description": "Çözüm", "foreman_ids": [str(foreman.id)],
            "plant_id": str(plant.id), "work_date": "2026-02-01", "status": "published",
        }
        resp = client.patch(f"/api/v1/contribution-works/{created['id']}", json=full_update, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "published"
        assert body["published_at"] is not None
        assert body["foremen"][0]["id"] == str(foreman.id)


class TestContributionWorkGains:
    def test_gain_change_is_computed_server_side(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        payload = _full_payload(plant, foreman, status="draft")
        payload["gains"] = [
            {"gain_type": "scrap_reduction", "previous_value": 4.2, "next_value": 3.1, "unit": "%"}
        ]
        resp = client.post("/api/v1/contribution-works", json=payload, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        gain = resp.json()["gains"][0]
        assert gain["change_amount"] == -1.1
        assert gain["change_percent"] == pytest.approx(-26.19, rel=0.01)
        assert gain["is_improvement"] is True


class TestContributionWorkPdf:
    def test_pdf_download(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        created = client.post(
            "/api/v1/contribution-works", json=_full_payload(plant, foreman), headers=auth_headers
        ).json()
        resp = client.get(f"/api/v1/contribution-works/{created['id']}/pdf", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:4] == b"%PDF"


class TestContributionWorkSummary:
    def test_summary_shape(self, client, auth_headers):
        resp = client.get("/api/v1/contribution-works/summary", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        for key in (
            "total_works", "added_this_month", "total_estimated_gain", "total_verified_gain",
            "total_monthly_time_saving_minutes", "by_plant", "by_work_type", "top_foremen",
            "applicable_other_plants_count", "standardized_ratio",
        ):
            assert key in body


class TestContributionWorkForemanRole:
    def test_solo_work_defaults_foreman_role_to_lead(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        created = client.post(
            "/api/v1/contribution-works", json=_full_payload(plant, foreman), headers=auth_headers
        ).json()
        assert created["foremen"][0]["role"] == "lead"

    def test_shared_work_defaults_foreman_roles_to_contributor(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        second = db_session.scalars(
            select(Foreman).where(Foreman.is_active.is_(True), Foreman.id != foreman.id)
        ).first()
        assert second is not None

        payload = _full_payload(plant, foreman)
        payload["foreman_ids"] = [str(foreman.id), str(second.id)]
        created = client.post("/api/v1/contribution-works", json=payload, headers=auth_headers).json()
        assert {f["role"] for f in created["foremen"]} == {"contributor"}


class TestForemanContributionSummary:
    def test_unknown_foreman_returns_404(self, client, auth_headers):
        resp = client.get(f"/api/v1/foremen/{uuid.uuid4()}/contribution-summary", headers=auth_headers)
        assert resp.status_code == 404

    def test_empty_state_for_foreman_without_contributions(self, client, auth_headers, db_session):
        covered = select(ContributionWorkForeman.foreman_id)
        foreman = db_session.scalar(select(Foreman).where(Foreman.id.notin_(covered)))
        assert foreman is not None

        resp = client.get(f"/api/v1/foremen/{foreman.id}/contribution-summary", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == {
            "total_contributions": 0, "smed_count": 0, "led_contributions": 0,
            "verified_financial_gain": {}, "estimated_financial_gain": {},
            "total_time_saving_minutes": 0.0, "last_contribution_date": None,
        }

    def test_summary_counts_only_published_and_splits_shared_gain_evenly(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        second = db_session.scalars(
            select(Foreman).where(Foreman.is_active.is_(True), Foreman.id != foreman.id)
        ).first()
        assert second is not None

        # Yayımlanmış, tek formenli çalışma: tahmini kazancın tamamı bu formene ait sayılmalı.
        client.post("/api/v1/contribution-works", json=_full_payload(plant, foreman), headers=auth_headers)

        # Yayımlanmış, iki formenli çalışma: kazanç ve zaman tasarrufu eşit paylaşılmalı.
        shared_payload = _full_payload(plant, foreman)
        shared_payload["title"] = "Ortak SMED Çalışması"
        shared_payload["foreman_ids"] = [str(foreman.id), str(second.id)]
        client.post("/api/v1/contribution-works", json=shared_payload, headers=auth_headers)

        # Taslak çalışma: özet toplamlarına dahil edilmemeli.
        client.post(
            "/api/v1/contribution-works",
            json={"title": "Taslak - sayılmamalı", "foreman_ids": [str(foreman.id)]},
            headers=auth_headers,
        )

        resp = client.get(f"/api/v1/foremen/{foreman.id}/contribution-summary", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_contributions"] == 2
        assert body["smed_count"] == 2
        assert body["led_contributions"] == 1
        assert body["verified_financial_gain"] == {}
        # 250000 (tek başına, tam pay) + 250000/2 (paylaşılan) = 375000
        assert body["estimated_financial_gain"]["TRY"] == pytest.approx(375000, rel=0.001)
        # 510 (tek başına, tam pay) + 510/2 (paylaşılan) = 765
        assert body["total_time_saving_minutes"] == pytest.approx(765, rel=0.001)
        assert body["last_contribution_date"] == "2026-01-15"

