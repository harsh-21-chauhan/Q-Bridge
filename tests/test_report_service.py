"""Benchmark API arithmetic is checked against preserved trial-level evidence."""
import csv
import io
from pathlib import Path
from statistics import fmean
from zipfile import ZipFile

import pytest

pytest.importorskip("pydantic", minversion="2.10", reason="Install .[api] for benchmark service tests")
from backend.app.services.experiment_store import StoreError
from backend.app.services.report_service import ReportService

RESEARCH = Path(__file__).resolve().parents[1] / "research"


def test_aggregate_metrics_match_all_full_raw_trials():
    report = ReportService(RESEARCH).summary()
    raw = []
    with ZipFile(RESEARCH / "evidence/QBridge-M2C-full-runs100.zip") as archive:
        for name in archive.namelist():
            if name.endswith(".csv"):
                raw.extend(csv.DictReader(io.StringIO(archive.read(name).decode())))
    assert len(raw) == report.policy_outcome_count == 32000
    assert report.trial_configuration_count == 4000
    for policy in report.policies:
        records = [row for row in raw if row["policy"] == policy.policy]
        assert len(records) == 4000
        for metric, column in [("mean_regret", "regret"), ("mean_task_loss", "task_loss"),
                               ("harm_rate", "harmed"), ("help_rate", "helped"), ("switch_rate", "switched")]:
            assert getattr(policy, metric) == pytest.approx(fmean(float(r[column]) for r in records), abs=1e-12)
    for scenario in report.scenarios:
        candidate = next(p for p in scenario.policies if p.policy == "adaptive_original_guard60")
        assert candidate.paired_ci_95 is None
        for policy in scenario.policies:
            assert policy.regret_reduction_vs_guard60 == pytest.approx(
                policy.mean_regret - candidate.mean_regret, abs=1e-12
            )


def test_no_scientific_simulation_is_needed_and_report_is_cached(monkeypatch):
    from qbridge.loss import PlacementModel
    def forbidden(*args, **kwargs):
        raise AssertionError("A benchmark read must not run a new simulation")
    monkeypatch.setattr(PlacementModel, "losses", forbidden)
    service = ReportService(RESEARCH)
    first = service.summary()
    monkeypatch.setattr(service, "_read_summary", forbidden)
    assert service.summary() is first


def test_modified_summary_is_not_presented_as_verified_evidence(tmp_path):
    (tmp_path / "summaries").mkdir()
    (tmp_path / "provenance.json").write_bytes((RESEARCH / "provenance.json").read_bytes())
    original = (RESEARCH / "summaries/m2c-final-summary.csv").read_bytes()
    (tmp_path / "summaries/m2c-final-summary.csv").write_bytes(original + b"\n")
    with pytest.raises(StoreError, match="Verified benchmark evidence is unavailable"):
        ReportService(tmp_path).summary()
