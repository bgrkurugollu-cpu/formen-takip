
from sqlalchemy import select

from app.models.foreman import Chief
from app.models.organization import Factory, Plant

PERIOD = {"date_from": "2025-08-01", "date_to": "2026-07-28"}


class TestChiefList:
    def test_requires_auth(self, client):
        assert client.get("/api/v1/chiefs").status_code == 401

    def test_returns_chiefs_with_team_scores(self, client, auth_headers):
        resp = client.get("/api/v1/chiefs", params={**PERIOD, "page_size": 50}, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] > 0
        item = body["items"][0]
        assert item["plant"] is not None and item["factory"] is not None
        assert item["foreman_count"] >= 1
        assert item["level"]["name"]

    def test_factory_filter_narrows_the_list(self, client, auth_headers, db_session):
        factories = list(db_session.scalars(select(Factory).order_by(Factory.code)))
        totals = []
        for factory in factories:
            resp = client.get(
                "/api/v1/chiefs",
                params={**PERIOD, "factory_ids": str(factory.id), "page_size": 200},
                headers=auth_headers,
            )
            body = resp.json()
            totals.append(body["total"])
            assert all(i["factory"]["code"] == factory.code for i in body["items"])

        unfiltered = client.get("/api/v1/chiefs", params={**PERIOD, "page_size": 1}, headers=auth_headers).json()
        assert sum(totals) == unfiltered["total"]

    def test_score_sort_is_monotonic(self, client, auth_headers):
        resp = client.get(
            "/api/v1/chiefs",
            params={**PERIOD, "sort_by": "score", "sort_dir": "desc", "page_size": 50},
            headers=auth_headers,
        )
        scores = [i["total_score"] for i in resp.json()["items"]]
        assert scores == sorted(scores, reverse=True)

    def test_search_matches_employee_number(self, client, auth_headers):
        resp = client.get("/api/v1/chiefs", params={**PERIOD, "search": "SEF-05", "page_size": 50}, headers=auth_headers)
        items = resp.json()["items"]
        assert items and all(i["employee_number"].startswith("SEF-05") for i in items)


class TestChiefDetail:
    def test_unknown_id_returns_404(self, client, auth_headers):
        import uuid

        assert client.get(f"/api/v1/chiefs/{uuid.uuid4()}", headers=auth_headers).status_code == 404

    def test_score_equals_mean_of_team_scores(self, client, auth_headers, db_session):
        listing = client.get(
            "/api/v1/chiefs",
            params={**PERIOD, "sort_by": "foreman_count", "sort_dir": "desc", "page_size": 5},
            headers=auth_headers,
        ).json()

        for row in listing["items"]:
            team = client.get(f"/api/v1/chiefs/{row['id']}/foremen", params=PERIOD, headers=auth_headers).json()
            scores = [f["total_score"] for f in team["items"]]
            assert len(scores) == row["foreman_count"]
            assert round(sum(scores) / len(scores), 1) == round(row["total_score"], 1)

    def test_detail_exposes_rankings(self, client, auth_headers, db_session):
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        body = client.get(f"/api/v1/chiefs/{chief.id}", params=PERIOD, headers=auth_headers).json()
        assert 1 <= body["company_rank"] <= body["company_total"]
        assert 1 <= body["plant_rank"] <= body["plant_total"]
        assert body["plant_total"] <= body["company_total"]

    def test_team_members_all_belong_to_the_chief(self, client, auth_headers, db_session):
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        team = client.get(f"/api/v1/chiefs/{chief.id}/foremen", params=PERIOD, headers=auth_headers).json()
        assert team["items"]
        foremen = client.get(
            "/api/v1/foremen",
            params={**PERIOD, "chief_id": str(chief.id), "page_size": 200},
            headers=auth_headers,
        ).json()
        assert {f["id"] for f in team["items"]} <= {f["id"] for f in foremen["items"]}

    def test_kpi_breakdown_returns_all_active_kpis(self, client, auth_headers, db_session):
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        body = client.get(f"/api/v1/chiefs/{chief.id}/kpis", params=PERIOD, headers=auth_headers).json()
        assert len(body["items"]) == 5
        assert sum(i["weight"] for i in body["items"]) == 100

    def test_trend_returns_ordered_points(self, client, auth_headers, db_session):
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        body = client.get(
            f"/api/v1/chiefs/{chief.id}/trend", params={**PERIOD, "granularity": "month"}, headers=auth_headers
        ).json()
        dates = [p["date"] for p in body["points"]]
        assert dates == sorted(dates)


class TestChiefPlantConsistency:
    def test_every_chief_belongs_to_exactly_one_plant(self, client, auth_headers, db_session):
        plants_by_id = {str(p.id): p for p in db_session.scalars(select(Plant))}
        body = client.get("/api/v1/chiefs", params={**PERIOD, "page_size": 200}, headers=auth_headers).json()
        for item in body["items"]:
            plant = plants_by_id[item["plant"]["id"]]
            assert item["factory"]["id"] == str(plant.factory_id)
