"""Read the frozen benchmark once; this endpoint never runs experiments."""
import csv
import hashlib
import io
import json
from pathlib import Path
from statistics import fmean

from pydantic import ValidationError

from qbridge.m2c_validation import POLICIES

from ..schemas import BenchmarkScenario, BenchmarkSummary, PolicyMetrics, ScenarioPolicy
from .experiment_store import StoreError

METRICS = ("mean_regret", "mean_task_loss", "switch_rate", "help_rate", "harm_rate")


class ReportService:
    def __init__(self, research_dir: Path):
        self.research_dir = research_dir
        self._summary: BenchmarkSummary | None = None

    def summary(self) -> BenchmarkSummary:
        if self._summary is not None:
            return self._summary
        try:
            self._summary = self._read_summary()
            return self._summary
        except (OSError, ValueError, KeyError, TypeError, StopIteration, ValidationError) as exc:
            raise StoreError("Verified benchmark evidence is unavailable. Check QBRIDGE_RESEARCH_DIR.") from exc

    def _read_summary(self) -> BenchmarkSummary:
        path = self.research_dir / "summaries/m2c-final-summary.csv"
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        manifest = json.loads((self.research_dir / "provenance.json").read_text())
        original = next(item for item in manifest["artifacts"] if item["storage"].get("file")
                        == "research/summaries/m2c-final-summary.csv")
        if digest != original["sha256"]:
            raise ValueError("Benchmark checksum mismatch")

        rows = list(csv.DictReader(io.StringIO(content.decode("utf-8"))))
        grouped: dict[tuple, list[ScenarioPolicy]] = {}
        for row in rows:
            key = (row["family"], int(row["qubits"]), row["truth_mode"],
                   int(row["shots"]), int(row["runs"]), int(row["seed"]))
            policy = row["policy"]
            # The historical column name is misleading: positive means that
            # this comparator has MORE regret than guard60. Explain the sign.
            metrics = ScenarioPolicy(
                policy=policy, **{name: float(row[name]) for name in METRICS},
                regret_reduction_vs_guard60=float(row["candidate_minus_policy_improvement"]),
                paired_ci_95=(None if policy == "adaptive_original_guard60" else
                              [float(row["paired_ci_low"]), float(row["paired_ci_high"])]),
            )
            grouped.setdefault(key, []).append(metrics)
        if len(rows) != 320 or len(grouped) != 40:
            raise ValueError("Expected the complete 40-configuration M2C summary")

        scenarios = []
        for key, policies in grouped.items():
            if len(policies) != len(POLICIES) or {p.policy for p in policies} != set(POLICIES):
                raise ValueError("Missing or repeated benchmark policy")
            family, qubits, truth_mode, shots, runs, seed = key
            if runs != 100:
                raise ValueError("Quick trials must not enter the full summary")
            scenarios.append(BenchmarkScenario(
                family=family, qubits=qubits, truth_mode=truth_mode, shots=shots,
                runs=runs, seed=seed, policies=policies,
            ))

        aggregate = []
        for policy in POLICIES:
            matching = [p for scenario in scenarios for p in scenario.policies if p.policy == policy]
            aggregate.append(PolicyMetrics(
                policy=policy,
                **{name: fmean(getattr(p, name) for p in matching) for name in METRICS},
            ))
        return BenchmarkSummary(
            mode="simulation", source="research/summaries/m2c-final-summary.csv",
            source_sha256=digest, configuration_count=len(scenarios),
            trial_configuration_count=sum(s.runs for s in scenarios),
            policy_outcome_count=sum(s.runs * len(s.policies) for s in scenarios),
            aggregation="Average across all 40 configurations, with equal weight for each",
            metric_notes=[
                "Regret and task loss are probabilities. The chart scales regret by 1,000 for readability.",
                "Harm, help and switch rates use all trials, not only switched trials.",
                "The no-calibration policy uses zero shots. Other policies use the selected scenario budget.",
                "Quick runs overlap full runs and are excluded. Simulated environments also repeat across configurations.",
                "A positive regret reduction favors the 60% guard. Each uncertainty interval applies only to its selected scenario.",
                "These results do not establish one policy as best in every setting. No combined confidence interval is reported.",
            ],
            policies=aggregate, scenarios=scenarios,
        )
