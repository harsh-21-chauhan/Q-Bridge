from qbridge.circuits import make_circuit
from qbridge.loss import PlacementModel
from qbridge.benchmark import benchmark, POLICIES


def test_baselines_are_defined_and_regrets_nonnegative():
    result = benchmark(PlacementModel(make_circuit(6, "ghz")), runs=5, shots=10, seed=1)
    assert set(result["policies"]) == set(POLICIES)
    assert all(v["mean_regret"] >= 0 for v in result["policies"].values())
    assert all(v["mean_task_loss"] >= 0 for v in result["policies"].values())
