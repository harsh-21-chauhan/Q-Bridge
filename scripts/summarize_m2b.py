"""Human-readable benchmark comparison; reads existing per-case JSON outputs."""
from pathlib import Path
import csv
import json

folder = Path('results/m2b')
rows = []
for f in sorted(folder.glob('*.json')):
    report = json.loads(f.read_text())
    # Skip single-demo records (these do not contain policy comparisons).
    if 'settings' not in report or 'policies' not in report:
        continue
    settings = report['settings']
    for name, values in report['policies'].items():
        delta = report['paired_comparisons'].get(name, {})
        rows.append({
            'case': f.stem,
            'policy': name,
            'runs': settings['runs'],
            'shots': settings['shots'],
            'mean_regret': values['mean_regret'],
            'regret_ci_low': values['regret_95ci'][0],
            'regret_ci_high': values['regret_95ci'][1],
            'switch_rate': values['switch_rate'],
            'harm_rate': values['harm_rate'],
            'gain_vs_original_evsi': delta.get('mean_regret_reduction_vs_original_evsi', ''),
            'paired_ci_low': delta.get('paired_95ci', ['', ''])[0],
            'paired_ci_high': delta.get('paired_95ci', ['', ''])[1],
        })
if not rows:
    raise SystemExit('No M2B JSON outputs found yet')
output = folder / 'summary.csv'
with output.open('w', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
print('\nCONCISE RESULTS (mean regret; lower is better)')
for case in sorted({row['case'] for row in rows}):
    print('\n' + case)
    for row in rows:
        if row['case'] == case:
            print(f"  {row['policy']:<26} regret={row['mean_regret']:.6f} harm={row['harm_rate']:.1%}")
print(f'\nSummary saved: {output}')
