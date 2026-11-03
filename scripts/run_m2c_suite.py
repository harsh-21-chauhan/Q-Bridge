#!/usr/bin/env python3
"""Run the frozen M2C held-out evaluation matrix and create a shareable ZIP.

From Q-Bridge root:
    python scripts/run_m2c_suite.py --mode quick --runs 20
    python scripts/run_m2c_suite.py --mode full --runs 100

No new dependencies or changes to M1/M2B are required.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from qbridge.circuits import make_circuit
from qbridge.loss import PlacementModel
from qbridge.m2c_validation import evaluate

ROOT = Path('results/m2c')


def matrix(mode: str):
    """Predefined scenarios: never select cases after examining their results."""
    if mode == 'quick':
        # Smoke test: all three families at both scales, in two conditions.
        return [(f, 6, 'prior', 100) for f in ('ghz', 'layered', 'star')] + [
            (f, 12, 'shifted', 100) for f in ('ghz', 'layered', 'star')]
    # Main held-out matrix: 3 families * 2 sizes * 2 shifts * 3 budgets,
    # plus isolated link/local shifts at 12 qubits.
    combos = [(f, n, mode_, s)
              for f in ('ghz', 'layered', 'star')
              for n in (6, 12)
              for mode_ in ('prior', 'shifted')
              for s in (50, 100, 200)]
    combos += [('layered', 12, mode_, s)
               for mode_ in ('local_shift', 'link_shift')
               for s in (100, 200)]
    return combos


def save_case(prefix: Path, report: dict, rows: list[dict]):
    prefix.with_suffix('.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    with prefix.with_suffix('.csv').open('w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['quick', 'full'], default='quick')
    parser.add_argument('--runs', type=int, default=100)
    parser.add_argument('--seed', type=int, default=20261104)
    parser.add_argument('--guard-draws', type=int, default=512)
    args = parser.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)

    scenarios = matrix(args.mode)
    all_summaries: list[dict] = []
    included: list[Path] = []
    for number, (family, qubits, truth, shots) in enumerate(scenarios, 1):
        prefix = ROOT / f'{family}{qubits}_{truth}_shots{shots}_runs{args.runs}_seed{args.seed}'
        json_path, csv_path = prefix.with_suffix('.json'), prefix.with_suffix('.csv')
        print(f'[{number}/{len(scenarios)}] {family} {qubits}q / {truth} / {shots} shots', flush=True)
        if json_path.exists() and csv_path.exists():
            # Resume an interrupted run without wasting time. Filenames encode
            # all settings except draws, so also check it in the JSON metadata.
            previous = json.loads(json_path.read_text(encoding='utf-8'))
            if previous['settings']['guard_draws'] == args.guard_draws:
                report = previous
                print('  Existing matching result reused.', flush=True)
            else:
                report, rows = evaluate(PlacementModel(make_circuit(qubits, family)),
                    runs=args.runs, shots=shots, seed=args.seed,
                    truth_mode=truth, guard_draws=args.guard_draws)
                save_case(prefix, report, rows)
        else:
            report, rows = evaluate(PlacementModel(make_circuit(qubits, family)),
                runs=args.runs, shots=shots, seed=args.seed,
                truth_mode=truth, guard_draws=args.guard_draws)
            save_case(prefix, report, rows)

        included.extend([json_path, csv_path])
        stats = report['policies']
        candidate = stats['adaptive_original_guard60']['mean_regret']
        original = stats['original_evsi']['mean_regret']
        adaptive = stats['adaptive_original']['mean_regret']
        print(f'  regret: EVSI={original:.6f}  adaptive={adaptive:.6f}  guard60={candidate:.6f}', flush=True)
        for policy, values in stats.items():
            diff = report['paired_comparisons'].get(policy)
            all_summaries.append({
                'family': family, 'qubits': qubits, 'truth_mode': truth,
                'shots': shots, 'runs': args.runs, 'seed': args.seed,
                'policy': policy, 'mean_regret': values['mean_regret'],
                'mean_task_loss': values['mean_task_loss'],
                'switch_rate': values['switch_rate'],
                'help_rate': values['help_rate'], 'harm_rate': values['harm_rate'],
                'candidate_minus_policy_improvement': (
                    diff['mean_regret_reduction_vs_candidate'] if diff else 0.0),
                'paired_ci_low': (diff['paired_95ci'][0] if diff else 0.0),
                'paired_ci_high': (diff['paired_95ci'][1] if diff else 0.0),
            })

    summary = ROOT / f'summary_{args.mode}_runs{args.runs}_seed{args.seed}.csv'
    with summary.open('w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=list(all_summaries[0]))
        writer.writeheader()
        writer.writerows(all_summaries)
    included.append(summary)

    out = Path(f'results/QBridge-M2C-{args.mode}-runs{args.runs}.zip')
    with ZipFile(out, 'w', ZIP_DEFLATED) as z:
        for file in included:
            z.write(file, file.relative_to(Path('results')))
    print('\nCompleted:', len(scenarios), 'scenarios')
    print('Summary:', summary)
    print('UPLOAD THIS FILE:', out)
    print('Interpretation: positive paired improvement means guard60 has lower regret.')
    print('These are simulated results, not measurements from real quantum hardware.')


if __name__ == '__main__':
    main()
