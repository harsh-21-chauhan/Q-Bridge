export const groups = ['local_a', 'local_b', 'remote'];
export const names = { local_a: 'Local · QPU A', local_b: 'Local · QPU B', remote: 'Remote link' };
export const colors = { local_a: '#5ee4ca', local_b: '#b6a2ff', remote: '#f3b86c' };
export const percent = (value, digits = 2) =>
  value == null ? 'Not estimated' : `${(value * 100).toFixed(digits)}%`;
export const number = (value) => (value == null ? '—' : value.toFixed(6));
export const scientific = (value) => (value == null ? 'Not calculated' : value.toExponential(3));
export const scenarios = {
  prior: 'Prior-aligned',
  shifted: 'Local + link shift',
  local_shift: 'Local-only shift',
  link_shift: 'Link-only shift',
};
export const policyNames = {
  adaptive_original_guard60: 'Adaptive · 60% guard',
  adaptive_original: 'Adaptive · unguarded',
  adaptive_original_guard75: 'Adaptive · 75% guard',
  adaptive_robust_guard75: 'Mixture priors · 75% guard',
  original_evsi: 'Original EVSI',
  fixed_split: 'Fixed split',
  random_calibration: 'Random calibration',
  no_calibration: 'No calibration',
};
