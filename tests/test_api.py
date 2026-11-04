"""Exercise the HTTP interface with real science and isolated temporary storage."""
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="Install .[api,api-test] to run backend tests")
pytest.importorskip("httpx", reason="Install .[api-test] to run backend tests")
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app
from qbridge.production import SimulationConfig, run_experiment

RESEARCH = Path(__file__).resolve().parents[1] / "research"


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(Settings(tmp_path / "experiments", RESEARCH))) as client:
        yield client


def test_create_retrieve_and_reuse_match_scientific_result(client):
    request = {"family": "layered", "qubits": 12, "shots": 100, "seed": 42}
    expected = run_experiment(SimulationConfig(**request))
    created = client.post("/api/experiments", json=request)
    assert created.status_code == 201
    assert created.json() == expected
    location = created.headers["location"]
    assert client.get(location).json() == expected
    repeated = client.post("/api/experiments", json=request)
    assert repeated.status_code == 200
    assert repeated.json() == expected
    assert len(list(client.app.state.experiment_service.store.directory.glob("*.json"))) == 1


def test_history_survives_new_app_instance(tmp_path):
    settings = Settings(tmp_path / "history", RESEARCH)
    with TestClient(create_app(settings)) as first:
        record = first.post("/api/experiments", json={"shots": 21}).json()
    with TestClient(create_app(settings)) as restarted:
        response = restarted.get(f"/api/experiments/{record['experiment_id']}")
        assert response.status_code == 200
        assert response.json() == record


def test_evidence_endpoint_omits_all_simulator_evaluation(client):
    record = client.post("/api/experiments", json={}).json()
    response = client.get(f"/api/experiments/{record['experiment_id']}/evidence")
    assert response.status_code == 200
    assert response.json() == {
        "experiment_id": record["experiment_id"], "mode": "simulation", "result": record["result"]
    }
    for name in ("true_error_rates", "truth_mode", "evaluation", "oracle", "regret"):
        assert name not in response.text


def test_unguarded_and_odd_budget_request(client):
    response = client.post("/api/experiments", json={"shots": 101, "guard_enabled": False})
    assert response.status_code == 201
    result = response.json()["result"]
    assert result["calibration"]["total_shots"] == 101
    assert sum(result["calibration"]["shots_by_group"].values()) == 101
    assert result["placements"]["final"] == result["placements"]["candidate"]
    assert result["decision"]["posterior_probability_better"] is None


@pytest.mark.parametrize("body", [
    {"qubits": 8}, {"qubits": 6.0}, {"qubits": True}, {"shots": "100"},
    {"shots": 10}, {"shots": 1001}, {"seed": -1}, {"seed": 2**32},
    {"guard_enabled": "false"}, {"guard_threshold": True}, {"guard_threshold": 1.1},
    {"guard_draws": 63}, {"guard_draws": 16385}, {"family": "custom"},
    {"truth_mode": "real_hardware"}, {"method": "original_evsi"},
    {"secret": "never-echo-this"}, {"true_error_rates": [0, 0, 0]},
])
def test_invalid_requests_never_reach_science_or_storage(client, monkeypatch, body):
    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid input must not reach the experiment service")
    monkeypatch.setattr(client.app.state.experiment_service, "create", forbidden)
    response = client.post("/api/experiments", json=body)
    assert response.status_code == 422
    assert "never-echo-this" not in response.text
    assert not client.app.state.experiment_service.store.directory.exists()


@pytest.mark.parametrize("body", ['{"shots": NaN}', '{"guard_threshold": Infinity}', '{bad-json'])
def test_invalid_json_has_safe_validation_response(client, body):
    response = client.post("/api/experiments", content=body, headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert response.json()["detail"]


def test_invalid_and_missing_identifiers(client):
    assert client.get("/api/experiments/not-a-valid-id").status_code == 422
    assert client.get("/api/experiments/qb_" + "0" * 32).status_code == 404
    assert client.get("/api/experiments/qb_" + "0" * 32 + "/evidence").status_code == 404


def test_paginated_history_contains_only_summaries(client):
    assert client.get("/api/experiments").json() == {"experiments": [], "next_offset": None, "total": 0}
    for seed in (1, 2, 3):
        assert client.post("/api/experiments", json={"seed": seed}).status_code == 201
    first = client.get("/api/experiments?limit=2").json()
    second = client.get(f"/api/experiments?limit=2&offset={first['next_offset']}").json()
    assert first["total"] == second["total"] == 3
    assert len(first["experiments"]) == 2 and len(second["experiments"]) == 1
    assert second["next_offset"] is None
    ids = [r["experiment_id"] for r in first["experiments"] + second["experiments"]]
    assert ids == sorted(set(ids))
    assert "evaluation" not in str(first)
    assert client.get("/api/experiments?limit=101").status_code == 422
    assert client.get("/api/experiments?offset=-1").status_code == 422


def test_corrupt_saved_record_reports_failure_without_overwrite(client):
    record = client.post("/api/experiments", json={}).json()
    path = client.app.state.experiment_service.store.directory / f"{record['experiment_id']}.json"
    path.write_text("broken-json")
    response = client.get(f"/api/experiments/{record['experiment_id']}")
    assert response.status_code == 500
    assert str(path) not in response.text
    assert client.post("/api/experiments", json={}).status_code == 500
    assert path.read_text() == "broken-json"


def test_busy_calculation_is_bounded_and_health_still_works(client):
    lock = client.app.state.experiment_service.calculation_lock
    with lock:
        assert client.post("/api/experiments", json={}).status_code == 503
        assert client.get("/api/health").status_code == 200
    assert client.post("/api/experiments", json={}).status_code == 201


def test_storage_failure_is_clear_and_releases_calculation_lock(client, monkeypatch):
    from backend.app.services.experiment_store import StoreError
    service = client.app.state.experiment_service
    def fail(*args):
        raise StoreError("The experiment could not be saved.")
    monkeypatch.setattr(service.store, "save", fail)
    assert client.post("/api/experiments", json={}).status_code == 503
    assert not service.calculation_lock.locked()


def test_benchmarks_and_interactive_docs_are_available(client):
    response = client.get("/api/benchmarks/summary")
    assert response.status_code == 200
    report = response.json()
    assert report["configuration_count"] == 40
    assert report["policy_outcome_count"] == 32000
    assert len(report["policies"]) == 8
    assert len(report["scenarios"]) == 40
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert schema["components"]["schemas"]["ExperimentRequest"]["additionalProperties"] is False
    assert client.get("/api/health").json()["meta_integration"] == "not_implemented"
    assert client.post("/api/assistant/chat", json={}).status_code == 404


def test_missing_evidence_is_a_controlled_error(tmp_path):
    with TestClient(create_app(Settings(tmp_path / "records", tmp_path / "no-evidence"))) as client:
        assert client.get("/api/benchmarks/summary").status_code == 503
        assert client.get("/api/health").status_code == 200
