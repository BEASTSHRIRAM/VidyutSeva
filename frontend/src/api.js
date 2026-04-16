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

// Voice / Chat
export const testVoice = (message) =>
  fetchJSON('/voice/test', { method: 'POST', body: JSON.stringify({ message }) });

export const sendChat = (message, area = '', lat = null, lon = null) =>
  fetchJSON('/voice/chat', {
    method: 'POST',
    body: JSON.stringify({ message, area, lat, lon }),
  });

// Returns full URL for EventSource (SSE)
export const getChatStreamUrl = (message, area = '', lat = 12.9716, lon = 77.5946) => {
  const url = new URL(`${API_BASE}/voice/chat/stream`);
  url.searchParams.set('message', message);
  if (area) url.searchParams.set('area', area);
  url.searchParams.set('lat', lat);
  url.searchParams.set('lon', lon);
  return url.toString();
};

// ── Auth ────────────────────────────────────────────────────────────────────

export const sendOTP = (phone_number) =>
  fetchJSON('/auth/send-otp', { method: 'POST', body: JSON.stringify({ phone_number }) });

export const verifyOTP = (phone_number, otp, name) =>
  fetchJSON('/auth/verify-otp', {
    method: 'POST',
    body: JSON.stringify({ phone_number, otp, name }),
  });

export const getMe = (token) =>
  fetchJSON('/auth/me', { headers: { Authorization: `Bearer ${token}` } });

// ── Complaints ──────────────────────────────────────────────────────────────

export const getComplaints = ({ area, status, sort = 'upvotes', limit = 50 } = {}) => {
  const params = new URLSearchParams();
  if (area)   params.set('area', area);
  if (status) params.set('status', status);
  params.set('sort', sort);
  params.set('limit', limit);
  return fetchJSON(`/complaints?${params.toString()}`);
};

export const createComplaint = (data, token) =>
  fetchJSON('/complaints', {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: JSON.stringify(data),
  });

export const upvoteComplaint = (complaintId, token) =>
  fetchJSON(`/complaints/${complaintId}/upvote`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });

export const getComplaint = (id) => fetchJSON(`/complaints/${id}`);

// ── Admin ───────────────────────────────────────────────────────────────────

export const getAdminEscalations = (token, limit = 50) =>
  fetchJSON(`/complaints/admin/escalations?limit=${limit}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
