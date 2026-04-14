import { useState, useEffect } from 'react';
import { getSubscriptions, createSubscription } from '../api';

const AREAS = [
  'Koramangala', 'Indiranagar', 'Jayanagar', 'Whitefield', 'Rajajinagar',
  'Hebbal', 'Malleshwaram', 'BTM Layout', 'HSR Layout', 'Electronic City',
  'Marathahalli', 'Yelahanka', 'Banashankari', 'JP Nagar', 'Basavanagudi',
  'Sadashivanagar', 'Vijayanagar', 'RT Nagar', 'Bellandur', 'Sarjapur Road',
];

const METHODS = [
  { value: 'email', label: 'Email' },
  { value: 'sms', label: 'SMS' },
  { value: 'whatsapp', label: 'WhatsApp' },
];

export default function AlertSubscriptions() {
  const [subs, setSubs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [toast, setToast] = useState(null);

  const [form, setForm] = useState({
    area_name: '',
    contact_method: 'email',
    contact_value: '',
  });

  useEffect(() => {
    loadSubs();
  }, []);

  async function loadSubs() {
    try {
      const data = await getSubscriptions();
      setSubs(data);
    } catch (err) {
      console.error('Failed to load subscriptions:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.area_name || !form.contact_value) return;

    try {
      await createSubscription(form);
      setForm({ area_name: '', contact_method: 'email', contact_value: '' });
      setShowForm(false);
      loadSubs();
      setToast('Subscription created successfully.');
      setTimeout(() => setToast(null), 3000);
    } catch (err) {
      alert('Failed: ' + err.message);
    }
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-icon">A</span>
          Alert Subscriptions
        </div>
        <button
          className={`btn ${showForm ? 'btn-ghost' : 'btn-secondary'} btn-sm`}
          onClick={() => setShowForm(!showForm)}
        >
          {showForm ? 'Cancel' : 'Add Subscription'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} style={{ marginBottom: '20px', paddingBottom: '20px', borderBottom: '1px solid var(--border-cream)' }}>
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
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Contact Method</label>
              <select
                className="form-select"
                value={form.contact_method}
                onChange={(e) => setForm({ ...form, contact_method: e.target.value })}
              >
                {METHODS.map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">
                {form.contact_method === 'email' ? 'Email Address' : 'Phone Number'}
              </label>
              <input
                type={form.contact_method === 'email' ? 'email' : 'tel'}
                className="form-input"
                value={form.contact_value}
                onChange={(e) => setForm({ ...form, contact_value: e.target.value })}
                placeholder={form.contact_method === 'email' ? 'you@example.com' : '+91 ...'}
              />
            </div>
          </div>
          <button type="submit" className="btn btn-primary btn-sm">
            Subscribe
          </button>
        </form>
      )}

      {loading ? (
        <div className="empty-state"><p>Loading subscriptions...</p></div>
      ) : subs.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">\u2014</div>
          <p>No subscriptions yet</p>
        </div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Area</th>
              <th>Method</th>
              <th>Contact</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {subs.map((s) => (
              <tr key={s.id}>
                <td className="td-primary">{s.area_name}</td>
                <td style={{ textTransform: 'capitalize' }}>{s.contact_method}</td>
                <td>{s.contact_value}</td>
                <td>
                  <span className={`badge ${s.is_active ? 'resolved' : 'source-manual'}`}>
                    {s.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {toast && <div className="toast success">{toast}</div>}
    </div>
  );
}
