import { afterEach, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import AssistantEvidence from './AssistantEvidence';
afterEach(cleanup);
const posterior = Object.fromEntries(
  ['local_a', 'local_b', 'remote'].map((g) => [
    g,
    { mean: 0.02, credible_interval_95: [0.01, 0.03] },
  ]),
);
const mapping = { qpu_a: [0, 1, 2], qpu_b: [3, 4, 5], cx_counts: { remote: 2 } };
const evidence = {
  experiment_id: 'example',
  shots: 100,
  decision: {
    switched: false,
    status: 'unchanged',
    posterior_probability_better: null,
    reason: 'Initial retained',
  },
  loss: { final_under_posterior: 0.04, accepted_expected_improvement: 0 },
  posterior,
  placements: { initial: mapping, candidate: mapping, final: mapping },
  stages: [
    { step: 1, stage: 'pilot', group: 'remote', shots: 20, failures: 1, evsi_at_choice: null },
  ],
};
it('renders scientific values as cards and tables without inventing null confidence', () => {
  render(<AssistantEvidence step={{ tool: 'get_experiment_evidence', evidence }} />);
  expect(screen.getByText('Not estimated')).toBeTruthy();
  expect(screen.getByText('0.040000')).toBeTruthy();
  expect(screen.getAllByText('Not calculated')).toHaveLength(3);
  expect(screen.getByText('Technical tool record · get_experiment_evidence')).toBeTruthy();
});
it('labels both budgets and preserves comparison interpretation', () => {
  render(
    <AssistantEvidence
      step={{
        tool: 'compare_budget',
        evidence: {
          previous: evidence,
          current: { ...evidence, shots: 200 },
          interpretation: 'Different posteriors are not direct benefits.',
        },
      }}
    />,
  );
  expect(screen.getByText('Original experiment · 100 shots')).toBeTruthy();
  expect(screen.getByText('Budget alternative · 200 shots')).toBeTruthy();
  expect(screen.getByText('Different posteriors are not direct benefits.')).toBeTruthy();
});
