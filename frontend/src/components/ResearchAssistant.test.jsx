import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import ResearchAssistant from './ResearchAssistant';
import { request } from '../lib/api';
vi.mock('../lib/api', () => ({ request: vi.fn() }));
const status = { mode: 'mock', disabled: false, reserved_usd: 0, budget_usd: 5, provider_calls: 0 };
afterEach(cleanup);
beforeEach(() => {
  vi.resetAllMocks();
  request.mockResolvedValue(status);
});
it('does not run a model or experiment on mount', async () => {
  render(<ResearchAssistant record={null} />);
  await screen.findByText('Select an experiment first');
  await waitFor(() => expect(request).toHaveBeenCalledExactlyOnceWith('/assistant/status'));
});
it('submits selected experiment and budget only after the button click', async () => {
  render(<ResearchAssistant record={{ experiment_id: 'selected' }} />);
  await waitFor(() =>
    expect(
      screen.getByRole('button', { name: 'Run mock walkthrough' }).closest('fieldset').disabled,
    ).toBe(false),
  );
  request.mockResolvedValueOnce({
    mode: 'mock',
    answer: 'Mock explanation',
    trace: [],
    usage: status,
  });
  fireEvent.change(screen.getByLabelText('Optional what-if calculation'), {
    target: { value: '200' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Run mock walkthrough' }));
  await screen.findByText('Mock explanation');
  expect(request).toHaveBeenLastCalledWith(
    '/assistant/ask',
    expect.objectContaining({ experiment_id: 'selected', compare_shots: 200 }),
  );
});
it('emergency stop disables further submissions', async () => {
  render(<ResearchAssistant record={{ experiment_id: 'selected' }} />);
  await waitFor(() =>
    expect(
      screen.getByRole('button', { name: 'Run mock walkthrough' }).closest('fieldset').disabled,
    ).toBe(false),
  );
  request.mockResolvedValueOnce({ ...status, disabled: true });
  fireEvent.click(screen.getByRole('button', { name: 'Emergency stop' }));
  await screen.findByRole('button', { name: 'Emergency stop · disabled' });
  expect(
    screen.getByRole('button', { name: 'Run mock walkthrough' }).closest('fieldset').disabled,
  ).toBe(true);
});
