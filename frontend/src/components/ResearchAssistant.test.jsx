import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import ResearchAssistant from './ResearchAssistant';
import { request } from '../lib/api';
vi.mock('../lib/api', () => ({ request: vi.fn() }));
const status = {
  mode: 'live',
  live_authorized: true,
  credential_configured: true,
  disabled: false,
  reserved_usd: 0,
  budget_usd: 5,
  provider_calls: 0,
};
const record = {
  experiment_id: 'selected',
  configuration: { family: 'layered', qubits: 6, shots: 100 },
};
afterEach(cleanup);
beforeEach(() => {
  vi.resetAllMocks();
  request.mockResolvedValue(status);
});
async function ready() {
  render(<ResearchAssistant record={record} />);
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Ask Muse Spark' }).disabled).toBe(false),
  );
}
it('only reads status on mount and keeps utilities collapsed', async () => {
  render(<ResearchAssistant record={null} />);
  await screen.findByText('Select an experiment first');
  expect(request).toHaveBeenCalledExactlyOnceWith('/assistant/status');
  expect(screen.getByText('Connection & usage').closest('details').open).toBe(false);
  expect(
    screen.getByText('Model unavailable? Read a local explanation').closest('details').open,
  ).toBe(false);
});
it('submits the selected budget with one deliberate live request', async () => {
  await ready();
  request.mockResolvedValueOnce({
    mode: 'live',
    answer: 'Recorded evidence explains the decision.',
    trace: [],
    usage: status,
  });
  fireEvent.change(screen.getByLabelText('Budget comparison'), { target: { value: '200' } });
  fireEvent.click(screen.getByRole('button', { name: 'Ask Muse Spark' }));
  await screen.findByText('Muse Spark’s analysis');
  expect(request).toHaveBeenLastCalledWith(
    '/assistant/ask',
    expect.objectContaining({ experiment_id: 'selected', compare_shots: 200 }),
  );
});
it('pause can be resumed without submitting a question', async () => {
  await ready();
  request.mockResolvedValueOnce({ ...status, disabled: true, paused: true });
  fireEvent.click(screen.getByRole('button', { name: 'Pause model requests' }));
  await screen.findByRole('button', { name: 'Resume assistant' });
  expect(screen.getByRole('button', { name: 'Ask Muse Spark' }).disabled).toBe(true);
  request.mockResolvedValueOnce(status);
  fireEvent.click(screen.getByRole('button', { name: 'Resume assistant' }));
  await screen.findByRole('button', { name: 'Pause model requests' });
  expect(request.mock.calls.some(([path]) => path === '/assistant/ask')).toBe(false);
});
it('local explanation works during a pause and is never labeled Muse Spark', async () => {
  request.mockResolvedValueOnce({ ...status, disabled: true });
  render(<ResearchAssistant record={record} />);
  await screen.findByText('Paused');
  request.mockResolvedValueOnce({
    mode: 'local',
    answer: 'Local evidence explanation.',
    trace: [],
  });
  fireEvent.click(screen.getByText('Model unavailable? Read a local explanation'));
  fireEvent.click(screen.getByRole('button', { name: 'Explain placement locally' }));
  await screen.findByText('Local explanation · Python evidence');
  expect(request).toHaveBeenLastCalledWith('/assistant/explain', { experiment_id: 'selected' });
  expect(screen.queryByText('Muse Spark’s analysis')).toBeNull();
});
it('mock mode cannot submit the main Muse Spark form', async () => {
  request.mockResolvedValueOnce({ ...status, mode: 'mock' });
  render(<ResearchAssistant record={record} />);
  await screen.findByText('Live not enabled');
  expect(screen.getByRole('button', { name: 'Ask Muse Spark' }).disabled).toBe(true);
});
it('rejects a mock response if the backend mode changes during a request', async () => {
  await ready();
  request.mockResolvedValueOnce({ mode: 'mock', answer: 'Mock text', trace: [], usage: status });
  fireEvent.click(screen.getByRole('button', { name: 'Ask Muse Spark' }));
  await screen.findByRole('alert');
  expect(screen.queryByText('Muse Spark’s analysis')).toBeNull();
});
it('a failed model request refreshes usage without automatic fallback or retries', async () => {
  await ready();
  request.mockRejectedValueOnce(new Error('Provider unavailable'));
  fireEvent.click(screen.getByRole('button', { name: 'Ask Muse Spark' }));
  await screen.findByRole('alert');
  await waitFor(() => expect(request).toHaveBeenLastCalledWith('/assistant/status'));
  expect(request.mock.calls.filter(([p]) => p === '/assistant/ask')).toHaveLength(1);
  expect(request.mock.calls.some(([p]) => p === '/assistant/explain')).toBe(false);
});

it('rechecks readiness on returning to the tab without submitting a question', async () => {
  request.mockResolvedValueOnce({ ...status, mode: 'mock', credential_configured: false });
  render(<ResearchAssistant record={record} />);
  await screen.findByText('Live not enabled');
  request.mockResolvedValueOnce(status);
  fireEvent.focus(window);
  await screen.findByText('Live enabled');
  expect(screen.getByRole('button', { name: 'Ask Muse Spark' }).disabled).toBe(false);
  expect(request.mock.calls.every(([path]) => path === '/assistant/status')).toBe(true);
});
