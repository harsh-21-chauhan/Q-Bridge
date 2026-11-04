// One small HTTP helper: no automatic retries or hidden background experiments.
export async function request(path, body) {
  let response;
  try {
    response = await fetch(
      `/api${path}`,
      body === undefined
        ? {}
        : {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          },
    );
  } catch {
    throw new Error(
      'Cannot reach the backend. Start FastAPI on port 8000 and check the Vite proxy.',
    );
  }
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error(
      'The backend is unavailable or returned an unreadable response. Check its terminal.',
    );
  }
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((e) => `${e.loc.join('.')}: ${e.msg}`).join('; ')
      : data.detail;
    throw new Error(detail || `Request failed (${response.status}).`);
  }
  return data;
}
export const api = {
  health: () => request('/health'),
  run: (config) => request('/experiments', config),
  get: (id) => request(`/experiments/${encodeURIComponent(id)}`),
  history: (offset = 0) => request(`/experiments?limit=10&offset=${offset}`),
  benchmarks: () => request('/benchmarks/summary'),
};
export function downloadJSON(record) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(record, null, 2)], { type: 'application/json' }),
  );
  const link = document.createElement('a');
  link.href = url;
  link.download = `${record.experiment_id}.json`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
