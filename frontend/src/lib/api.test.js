import { afterEach, describe, expect, it, vi } from 'vitest';
import { request } from './api';

afterEach(() => vi.unstubAllGlobals());

describe('backend requests', () => {
  it('posts numeric settings once, without retries', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({ experiment_id: 'example' }) });
    vi.stubGlobal('fetch', fetch);
    await expect(request('/experiments', { shots: 100 })).resolves.toEqual({
      experiment_id: 'example',
    });
    expect(fetch).toHaveBeenCalledOnce();
    expect(fetch).toHaveBeenCalledWith('/api/experiments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{"shots":100}',
    });
  });

  it('shows field-specific validation errors from FastAPI', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ detail: [{ loc: ['body', 'shots'], msg: 'Must be at least 20' }] }),
      }),
    );
    await expect(request('/experiments', {})).rejects.toThrow('body.shots: Must be at least 20');
  });

  it('handles offline and unreadable proxy responses without retrying', async () => {
    const fetch = vi.fn().mockRejectedValue(new Error('offline'));
    vi.stubGlobal('fetch', fetch);
    await expect(request('/health')).rejects.toThrow('Cannot reach the backend');
    expect(fetch).toHaveBeenCalledOnce();
    fetch.mockResolvedValue({
      json: async () => {
        throw new Error('not JSON');
      },
    });
    await expect(request('/health')).rejects.toThrow('unreadable response');
    expect(fetch).toHaveBeenCalledTimes(2);
  });
});
