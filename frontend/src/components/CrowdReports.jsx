import { useState, useEffect } from 'react';
import { getCrowdReports, submitCrowdReport } from '../api';

const AREAS = [
  'Koramangala', 'Indiranagar', 'Jayanagar', 'Whitefield', 'Rajajinagar',
  'Hebbal', 'Malleshwaram', 'BTM Layout', 'HSR Layout', 'Electronic City',
  'Marathahalli', 'Yelahanka', 'Banashankari', 'JP Nagar', 'Basavanagudi',
  'Sadashivanagar', 'Vijayanagar', 'RT Nagar', 'Bellandur', 'Sarjapur Road',
];

function timeAgo(iso) {
  if (!iso) return '';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function CrowdReports() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [toast, setToast] = useState(null);

  const [form, setForm] = useState({
    area_name: '',
    description: '',
    reporter_phone: '',
  });

  useEffect(() => {
    loadReports();
  }, []);

  async function loadReports() {
    try {
      const data = await getCrowdReports();
      setReports(data);
    } catch (err) {
      console.error('Failed to load reports:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.area_name || !form.description) return;

    try {
      const result = await submitCrowdReport(form);
      setForm({ area_name: '', description: '', reporter_phone: '' });
      setShowForm(false);
      loadReports();

      if (result.auto_outage_created) {
        setToast('Outage auto-created from citizen reports');
      } else {
        setToast(`Report submitted. ${result.reports_in_area} reports in this area.`);
      }
      setTimeout(() => setToast(null), 4000);
    } catch (err) {
      alert('Submit failed: ' + err.message);
    }
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-icon">R</span>
          Citizen Reports
        </div>
        <button
          className={`btn ${showForm ? 'btn-ghost' : 'btn-secondary'} btn-sm`}
          onClick={() => setShowForm(!showForm)}
        >
          {showForm ? 'Cancel' : 'Submit Report'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} style={{ marginBottom: '20px', paddingBottom: '20px', borderBottom: '1px solid var(--border-cream)' }}>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Area</label>
              <select
                className="form-select"
                value={form.area_name}
                onChange={(e) => setForm({ ...form, area_name: e.target.value })}
              >
                <option value="">Select area</option>
                {AREAS.map((a) => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Phone (optional)</label>
              <input
                type="tel"
                className="form-input"
                value={form.reporter_phone}
                onChange={(e) => setForm({ ...form, reporter_phone: e.target.value })}
                placeholder="+91 ..."
              />
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea
              className="form-textarea"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Describe the power issue you are experiencing..."
            />
          </div>
          <button type="submit" className="btn btn-primary btn-sm">
            Submit Report
          </button>
        </form>
      )}

      {loading ? (
        <div className="empty-state"><p>Loading reports...</p></div>
      ) : reports.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">\u2014</div>
          <p>No citizen reports yet</p>
        </div>
      ) : (
        <div style={{ maxHeight: '360px', overflowY: 'auto' }}>
          {reports.map((r, i) => (
            <div
              key={r.id || i}
              style={{
                padding: '12px 0',
                borderBottom: '1px solid var(--border-cream)',
              }}
            >
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '4px',
              }}>
                <span style={{ fontWeight: 600, fontSize: '14px', color: 'var(--near-black)' }}>
                  {r.area_name}
                </span>
                <span style={{ fontSize: '12px', color: 'var(--stone-gray)' }}>
                  {timeAgo(r.created_at)}
                </span>
              </div>
              <p style={{ fontSize: '13px', color: 'var(--olive-gray)', lineHeight: '1.5' }}>
                {r.description}
              </p>
              <div style={{ marginTop: '4px', display: 'flex', gap: '6px' }}>
                <span className={`badge ${r.verified ? 'resolved' : 'source-manual'}`}>
                  {r.verified ? 'Verified' : 'Unverified'}
                </span>
                <span className="badge source-manual" style={{ fontSize: '10px' }}>
                  {r.report_source}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {toast && <div className="toast success">{toast}</div>}
    </div>
  );
}
