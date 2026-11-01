"""CLI exposes a separate pass/fail or inspectable output for each build stage."""
import argparse
import json
from pathlib import Path
from .circuits import make_circuit, pauli_label, stabilizer_generators
from .loss import PlacementModel, GROUPS
from .bayes import BayesianPlanner, DEFAULT_PRIORS
from .experiment import run_experiment
from .benchmark import benchmark
from .reference_sim import density_reference_loss


def main() -> None:
    parser = argparse.ArgumentParser(description="Q-Bridge scientific prototype (simulation only)")
    sub = parser.add_subparsers(dest="command", required=True)
    for cmd in ("inspect", "check-loss", "rank", "demo", "benchmark", "validate-aer"):
        p = sub.add_parser(cmd)
        p.add_argument("--family", choices=("ghz", "layered", "star"), default="layered")
        p.add_argument("--qubits", type=int, default=6)
        if cmd in {"rank", "demo", "benchmark"}:
            p.add_argument("--shots", type=int, default=100)
        if cmd in {"demo", "benchmark"}:
            p.add_argument("--seed", type=int, default=42)
        if cmd == "demo":
            p.add_argument("--truth-a", type=float, default=0.045)
            p.add_argument("--truth-b", type=float, default=0.012)
            p.add_argument("--truth-link", type=float, default=0.085)
            p.add_argument("--calibration-backend", choices=("binomial", "aer"), default="binomial")
        if cmd in {"demo", "benchmark"}:
            p.add_argument("--output", type=str, default=None,
                           help="save reproducible JSON record; for example results/run01.json")
        if cmd == "benchmark":
            p.add_argument("--runs", type=int, default=30)
            p.add_argument("--truth-mode", choices=("prior", "shifted"), default="prior")
    args = parser.parse_args()
    model = PlacementModel(make_circuit(args.qubits, args.family))
    if args.command == "inspect":
        c = model.circuit
        result = {"family": c.family, "qubits": c.n_qubits,
                  "cx_gates": c.cx_count, "placement_count": len(model.mappings),
                  "gates": [{"name": g.name, "control": g.control, "target": g.target} for g in c.gates],
                  "stabilizers": [pauli_label(x, z, c.n_qubits) for x, z in stabilizer_generators(c)]}
    elif args.command == "check-loss":
        true_parameters = (0.035, 0.015, 0.11)
        ref = density_reference_loss(model, true_parameters, index=0)
        predicted = float(model.losses(true_parameters)[0])
        result = {"numpy_density_matrix_loss": ref, "analytic_loss": predicted,
                  "absolute_difference": abs(ref-predicted),
                  "pass": abs(ref-predicted) < 1e-10}
    elif args.command == "rank":
        planner = BayesianPlanner(model)
        selected, scores = planner.select(DEFAULT_PRIORS, args.shots)
        result = {"shot_budget": args.shots, "chosen_calibration": GROUPS[selected],
                  "expected_value_of_sample_information": scores,
                  "prior_best_placement": model.mappings[planner.recommend(DEFAULT_PRIORS)[0]]}
    elif args.command == "demo":
        result = run_experiment(model, (args.truth_a, args.truth_b, args.truth_link),
                                shots=args.shots, seed=args.seed,
                                calibration_backend=args.calibration_backend).to_dict()
    elif args.command == "benchmark":
        result = benchmark(model, runs=args.runs, shots=args.shots, seed=args.seed,
                           truth_mode=args.truth_mode)
    else:
        from .aer_validation import compare_aer_to_analytical, validate_calibration
        result = {"loss_validation": compare_aer_to_analytical(model),
                  "calibration_validation": validate_calibration()}
    rendered = json.dumps(result, indent=2)
    if args.command in {"demo", "benchmark"} and args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
