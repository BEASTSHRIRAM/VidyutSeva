const API_BASE = 'http://localhost:8000';

export async function fetchJSON(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'API request failed');
  }
  return res.json();
}

// Dashboard
export const getDashboardSummary = () => fetchJSON('/dashboard/summary');
export const getAreaStatus = () => fetchJSON('/dashboard/areas');
export const getRecentCalls = (limit = 20) => fetchJSON(`/dashboard/calls?limit=${limit}`);

// Outages
export const getOutages = (status) =>
  fetchJSON(`/outages${status ? `?status=${status}` : ''}`);
export const getActiveOutages = (area) =>
  fetchJSON(`/outages/active${area ? `?area=${area}` : ''}`);
export const getLiveOutages = () => fetchJSON('/api/live-outages');
export const createOutage = (data) =>
  fetchJSON('/outages', { method: 'POST', body: JSON.stringify(data) });
export const updateOutage = (id, data) =>
  fetchJSON(`/outages/${id}`, { method: 'PUT', body: JSON.stringify(data) });
export const deleteOutage = (id) =>
  fetchJSON(`/outages/${id}`, { method: 'DELETE' });
export const searchOutages = (q) => fetchJSON(`/outages/search?q=${encodeURIComponent(q)}`);

// Crowd Reports
export const getCrowdReports = (area) =>
  fetchJSON(`/reports${area ? `?area=${area}` : ''}`);
export const submitCrowdReport = (data) =>
  fetchJSON('/reports', { method: 'POST', body: JSON.stringify(data) });

// Alerts
export const getSubscriptions = (area) =>
  fetchJSON(`/alerts/subscriptions${area ? `?area=${area}` : ''}`);
export const createSubscription = (data) =>
  fetchJSON('/alerts/subscribe', { method: 'POST', body: JSON.stringify(data) });

// Scraper
export const triggerScraper = () => fetchJSON('/scraper/run', { method: 'POST' });

// Voice Test
export const testVoice = (message) =>
  fetchJSON('/voice/test', { method: 'POST', body: JSON.stringify({ message }) });
