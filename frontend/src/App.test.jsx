import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import App from './App';
import { api } from './lib/api';
import { defaults } from './components/ExperimentForm';

// These tests focus on request/state transitions. ScientificViews.test.jsx
// checks the result components separately, without copying a full saved run.
vi.mock('./components/CircuitViewer', () => ({ default: () => null }));
vi.mock('./components/Placement', () => ({ default: () => null }));
vi.mock('./components/Calibration', () => ({
  CalibrationTimeline: () => null,
  NoiseComparison: () => null,
}));

function exampleRecord(shots = 100) {
  return {
    experiment_id: `test-${shots}`,
    configuration: { ...defaults, shots },
    result: {
      loss: { final_under_posterior: 0.04, accepted_expected_improvement: 0 },
      circuit: { placement_count: 20 },
      calibration: { total_shots: shots },
      decision: { switched: false, status: 'unchanged' },
      guard_seed: 42,
    },
    evaluation: {
      true_error_rates: { local_a: 0.02, local_b: 0.03, remote: 0.05 },
      oracle_placement: { assignment: [0, 0, 0, 1, 1, 1] },
    },
    metadata: { algorithm_version: 'test', schema_version: 1, seed_scheme: 'test', runtime: {} },
  };
}

vi.mock('./lib/api', () => ({
  api: { health: vi.fn(), history: vi.fn(), run: vi.fn(), get: vi.fn(), benchmarks: vi.fn() },
  downloadJSON: vi.fn(),
}));
afterEach(cleanup);
beforeEach(() => {
  vi.resetAllMocks();
  api.health.mockResolvedValue({ status: 'ok' });
  api.history.mockResolvedValue({ experiments: [], total: 0, next_offset: null });
});

it('loads connection/history without creating experiments or model requests', async () => {
  render(<App />);
  await screen.findByText('Backend connected');
  expect(api.run).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: /Research assistant/ }));
  expect(screen.getByText('Meta integration is not enabled')).toBeTruthy();
  expect(api.run).not.toHaveBeenCalled();
  expect(api.benchmarks).not.toHaveBeenCalled();
});

it('reports a failed run and allows a deliberate retry', async () => {
  api.run.mockRejectedValue(new Error('Calculation busy. Try again later.'));
  render(<App />);
  await screen.findByText('Backend connected');
  fireEvent.click(screen.getByRole('button', { name: 'Run calibration' }));
  await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('Calculation busy'));
  expect(api.run).toHaveBeenCalledOnce();
  expect(screen.getByRole('button', { name: 'Run calibration' }).disabled).toBe(false);
  expect(screen.queryByText('Recorded result')).toBeNull();
});

it('keeps successful result labels intact when edited settings fail', async () => {
  api.run
    .mockResolvedValueOnce(exampleRecord())
    .mockRejectedValueOnce(new Error('Calculation failed'));
  render(<App />);
  await screen.findByText('Backend connected');
  fireEvent.click(screen.getByRole('button', { name: 'Run calibration' }));
  await screen.findByRole('heading', { name: 'LAYERED · 6 qubits · 100 shots' });
  fireEvent.change(screen.getByRole('spinbutton', { name: /Calibration budget/ }), {
    target: { value: '200' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Run calibration' }));
  await screen.findByRole('alert');
  expect(screen.getByRole('heading', { name: 'LAYERED · 6 qubits · 100 shots' })).toBeTruthy();
  expect(screen.queryByRole('heading', { name: 'LAYERED · 6 qubits · 200 shots' })).toBeNull();
});

it('uses recorded settings for a budget comparison, even if form inputs changed', async () => {
  api.run.mockResolvedValueOnce(exampleRecord()).mockResolvedValueOnce(exampleRecord(200));
  render(<App />);
  await screen.findByText('Backend connected');
  fireEvent.click(screen.getByRole('button', { name: 'Run calibration' }));
  await screen.findByRole('heading', { name: 'LAYERED · 6 qubits · 100 shots' });
  fireEvent.change(screen.getByRole('spinbutton', { name: /Reproducibility seed/ }), {
    target: { value: '99' },
  });
  fireEvent.click(screen.getByRole('button', { name: '200 shots' }));
  await screen.findByRole('heading', { name: 'LAYERED · 6 qubits · 200 shots' });
  expect(api.run).toHaveBeenLastCalledWith({ ...defaults, shots: 200 });
  expect(screen.getByText(/Each run has a different posterior/)).toBeTruthy();
});
