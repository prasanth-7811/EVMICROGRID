from __future__ import annotations

from fastapi.testclient import TestClient

from ev_service.app import app


client = TestClient(app)


def test_health_is_local_and_deterministic() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["deterministic"] is True
    assert body["local_only"] is True


def test_dashboard_shape_contains_operational_sections() -> None:
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    body = response.json()
    for key in ("summary", "fleet", "energy", "forecasts", "tariffs", "recommendations", "agents", "monitoring"):
        assert key in body
    assert body["deterministic"] is True
    assert body["summary"]["total_vehicles"] == len(body["fleet"])
    assert len(body["forecasts"]) == 24
    assert response.headers["content-type"].startswith("application/json")


def test_optimization_respects_vehicle_constraints() -> None:
    response = client.post("/api/optimize", json={"horizon_hours": 24, "fleet_size": 5, "include_v2g": True})
    assert response.status_code == 200
    body = response.json()
    checks = body["constraint_checks"]
    assert checks["reserve_soc_respected"] is True
    assert checks["charge_power_limits_respected"] is True
    assert checks["discharge_power_limits_respected"] is True
    assert checks["no_simultaneous_charge_discharge"] is True
    assert len(body["schedule"]) == 24
    for schedule in body["schedules"]:
        assert schedule["final_soc"] >= schedule["target_soc"] or not schedule["departure_target_met"]
        for slot in schedule["slots"]:
            assert not (slot["charge_kw"] > 0 and slot["discharge_kw"] > 0)


def test_feedback_is_captured_and_aggregated() -> None:
    response = client.post(
        "/api/feedback",
        json={"recommendation_id": "rec-solar-first", "rating": 5, "helpful": True, "category": "accuracy"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert body["feedback"]["feedback_id"].startswith("feedback-")
    assert body["aggregate"]["count"] >= 1
    assert body["aggregate"]["average_rating"] >= 1


def test_monitoring_exposes_quality_drift_and_request_metrics() -> None:
    response = client.get("/api/monitoring")
    assert response.status_code == 200
    body = response.json()
    for key in ("requests", "quality", "drift", "feedback", "checks"):
        assert key in body
    assert body["checks"]["deterministic_local_mode"] is True
    assert "drift_score" in body["drift"]


def test_dashboard_is_served_at_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "EV Energy Microgrid" in response.text
