import { useState } from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import ExperimentForm, { defaults } from './ExperimentForm';
import Placement from './Placement';
import CircuitViewer from './CircuitViewer';
import { CalibrationTimeline } from './Calibration';

afterEach(cleanup);

it('submits typed numeric settings and rejects out-of-range budgets', () => {
  const submit = vi.fn();
  function Form() {
    const [config, setConfig] = useState(defaults);
    return <ExperimentForm config={config} setConfig={setConfig} onRun={submit} />;
  }
  render(<Form />);
  const budget = screen.getByRole('spinbutton', { name: /Calibration budget/ });
  fireEvent.change(budget, { target: { value: '200' } });
  fireEvent.click(screen.getByRole('button', { name: 'Run calibration' }));
  expect(submit).toHaveBeenCalledWith({ ...defaults, shots: 200 });
  fireEvent.change(budget, { target: { value: '19' } });
  expect(budget.checkValidity()).toBe(false);
  fireEvent.click(screen.getByRole('button', { name: 'Run calibration' }));
  expect(submit).toHaveBeenCalledOnce();
});

// Small synthetic view data tests presentation rules, not Bayesian mathematics.
const placement = {
  assignment: [0, 0, 0, 1, 1, 1],
  qpu_a: [0, 1, 2],
  qpu_b: [3, 4, 5],
  cx_counts: { local_a: 2, local_b: 2, remote: 1 },
};
const placements = { initial: placement, candidate: placement, final: placement };

it('does not turn an uncomputed switch probability into zero confidence', () => {
  render(
    <Placement
      result={{
        placements,
        loss: {},
        decision: {
          guard_enabled: true,
          guard_threshold: 0.6,
          posterior_probability_better: null,
          posterior_draws_used: 0,
          switched: false,
          status: 'unchanged',
          reason: 'Candidate equals initial placement',
          probability_interpretation: 'Not calculated',
        },
      }}
    />,
  );
  expect(screen.getByText('Not estimated')).toBeTruthy();
  expect(screen.getByText('Initial placement retained')).toBeTruthy();
  expect(screen.queryByText('0.00%')).toBeNull();
});

it('recolors circuit groups when inspecting another placement', () => {
  const candidate = { ...placement, assignment: [0, 1, 0, 1, 0, 1] };
  const result = {
    placements: { ...placements, candidate },
    circuit: {
      family: 'ghz',
      qubits: 6,
      cx_count: 1,
      gates: [{ name: 'cx', control: 0, target: 1 }],
      stabilizers: ['IIIIXX'],
    },
  };
  const { container } = render(<CircuitViewer result={result} />);
  expect(container.querySelector('svg title').textContent).toContain('Local · QPU A');
  fireEvent.change(screen.getByLabelText('Circuit placement view'), {
    target: { value: 'candidate' },
  });
  expect(container.querySelector('svg title').textContent).toContain('Remote link');
});

it('shows EVSI only for the selected adaptive stage', () => {
  const beliefs = Object.fromEntries(
    ['local_a', 'local_b', 'remote'].map((g) => [g, { mean: 0.02, alpha: 2, beta: 98 }]),
  );
  const common = {
    shots: 10,
    failures: 0,
    posteriors_before: beliefs,
    posteriors_after: beliefs,
    cumulative_shots_by_group: { local_a: 10, local_b: 0, remote: 0 },
  };
  render(
    <CalibrationTimeline
      result={{
        calibration: {
          total_shots: 20,
          trace: [
            {
              ...common,
              step: 1,
              stage: 'pilot',
              group: 'local_a',
              cumulative_shots: 10,
              evsi_at_choice: null,
            },
            {
              ...common,
              step: 2,
              stage: 'adaptive',
              group: 'remote',
              cumulative_shots: 20,
              evsi_at_choice: { local_a: 0.001, local_b: 0.002, remote: 0.003 },
            },
          ],
        },
      }}
    />,
  );
  expect(screen.getByText(/EVSI is not calculated/)).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: /Adaptive EVSI/ }));
  expect(screen.queryByText(/EVSI is not calculated/)).toBeNull();
  expect(screen.getByText('3.000e-3')).toBeTruthy();
  expect(screen.getByText('Remote link · chosen')).toBeTruthy();
  expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(4);
});
