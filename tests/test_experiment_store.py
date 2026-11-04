"""Persistence must preserve science, refuse corrupt records and never traverse paths."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json

import pytest

pytest.importorskip("pydantic", minversion="2.10", reason="Install .[api] for storage tests")
from backend.app.services.experiment_store import (
    ExperimentStore, InvalidExperimentId, InvalidStoredRecord, RecordConflict, StoreError,
)
from qbridge.production import run_experiment


@pytest.fixture(scope="module")
def record():
    return run_experiment()


def test_concurrent_identical_writes_create_one_complete_file(tmp_path, record):
    store = ExperimentStore(tmp_path)
    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(lambda _: store.save(record), range(8)))
    assert sum(created for _, created in outcomes) == 1
    assert store.get(record["experiment_id"]).model_dump() == record
    assert [p.suffix for p in tmp_path.iterdir()] == [".json"]


@pytest.mark.parametrize("identifier", ["../outside", "/tmp/outside", "qb_../x", "qb_" + "a" * 32 + "\n"])
def test_ids_cannot_be_paths(tmp_path, identifier):
    with pytest.raises(InvalidExperimentId):
        ExperimentStore(tmp_path).get(identifier)


@pytest.mark.parametrize("mutation", ["missing", "id", "config", "budget", "nan"])
def test_malformed_records_are_rejected(tmp_path, record, mutation):
    damaged = deepcopy(record)
    if mutation == "missing":
        del damaged["result"]["calibration"]
    elif mutation == "id":
        damaged["experiment_id"] = "qb_" + "0" * 32
    elif mutation == "config":
        damaged["configuration"]["shots"] = 200
    elif mutation == "budget":
        damaged["result"]["calibration"]["trace"][0]["shots"] += 1
    else:
        damaged["result"]["loss"]["final_under_posterior"] = float("nan")
    with pytest.raises(InvalidStoredRecord):
        ExperimentStore(tmp_path).save(damaged)
    assert list(tmp_path.iterdir()) == []


def test_existing_record_cannot_be_silently_replaced(tmp_path, record):
    store = ExperimentStore(tmp_path)
    store.save(record)
    changed = deepcopy(record)
    changed["result"]["decision"]["reason"] = "different result for the same ID"
    with pytest.raises(RecordConflict):
        store.save(changed)
    assert store.get(record["experiment_id"]).model_dump() == record
    assert not list(tmp_path.glob("*.tmp"))


def test_symlink_record_is_not_followed(tmp_path, record):
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps(record))
    folder = tmp_path / "records"
    folder.mkdir()
    (folder / f"{record['experiment_id']}.json").symlink_to(outside)
    with pytest.raises(InvalidStoredRecord):
        ExperimentStore(folder).get(record["experiment_id"])


def test_atomic_publish_failure_leaves_no_partial_record(tmp_path, record, monkeypatch):
    import backend.app.services.experiment_store as module
    def fail(*args):
        raise OSError("disk unavailable")
    monkeypatch.setattr(module.os, "link", fail)
    with pytest.raises(StoreError, match="could not be saved"):
        ExperimentStore(tmp_path).save(record)
    assert list(tmp_path.iterdir()) == []
