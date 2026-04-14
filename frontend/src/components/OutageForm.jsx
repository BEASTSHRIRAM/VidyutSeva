import { useState } from 'react';
import { createOutage, updateOutage } from '../api';

const AREAS = [
  'Koramangala', 'Indiranagar', 'Jayanagar', 'Whitefield', 'Rajajinagar',
  'Hebbal', 'Malleshwaram', 'BTM Layout', 'HSR Layout', 'Electronic City',
  'Marathahalli', 'Yelahanka', 'Banashankari', 'JP Nagar', 'Basavanagudi',
  'Sadashivanagar', 'Vijayanagar', 'RT Nagar', 'Bellandur', 'Sarjapur Road',
];

const TYPES = [
  { value: 'planned_maintenance', label: 'Planned Maintenance' },
  { value: 'emergency', label: 'Emergency' },
  { value: 'load_shedding', label: 'Load Shedding' },
];

const STATUSES = [
  { value: 'active', label: 'Active' },
  { value: 'scheduled', label: 'Scheduled' },
  { value: 'resolved', label: 'Resolved' },
];

function toLocalISO(date) {
  if (!date) return '';
  const d = new Date(date);
  const offset = d.getTimezoneOffset();
  const local = new Date(d.getTime() - offset * 60000);
  return local.toISOString().slice(0, 16);
}

export default function OutageForm({ editData, onClose, onSaved }) {
  const isEdit = !!editData?.id;

  const [form, setForm] = useState({
    area_name: editData?.area_name || '',
    outage_type: editData?.outage_type || 'planned_maintenance',
    reason: editData?.reason || '',
    start_time: toLocalISO(editData?.start_time || new Date()),
    end_time: toLocalISO(editData?.end_time || ''),
    status: editData?.status || 'active',
    severity: editData?.severity || 1,
  });

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.area_name || !form.start_time) {
      setError('Area and start time are required.');
      return;
    }

    setSubmitting(true);
    setError('');

    try {
      const payload = {
        ...form,
        start_time: new Date(form.start_time).toISOString(),
        end_time: form.end_time ? new Date(form.end_time).toISOString() : null,
        severity: Number(form.severity),
      };

      if (isEdit) {
        await updateOutage(editData.id, payload);
      } else {
        await createOutage(payload);
      }
      onSaved?.();
      onClose?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="panel anim-fade">
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-icon">{isEdit ? 'E' : '+'}</span>
          {isEdit ? 'Edit Outage' : 'Report New Outage'}
        </div>
        {onClose && (
          <button className="btn btn-ghost btn-sm" onClick={onClose}>
            Cancel
          </button>
        )}
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Area</label>
            <select
              name="area_name"
              value={form.area_name}
              onChange={handleChange}
              className="form-select"
            >
              <option value="">Select area</option>
              {AREAS.map((a) => (
                <option key={a} value={a}>{a}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Outage Type</label>
            <select
              name="outage_type"
              value={form.outage_type}
              onChange={handleChange}
              className="form-select"
            >
              {TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Reason</label>
          <textarea
            name="reason"
            value={form.reason}
            onChange={handleChange}
            className="form-textarea"
            placeholder="Describe the reason for this outage..."
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Start Time</label>
            <input
              type="datetime-local"
              name="start_time"
              value={form.start_time}
              onChange={handleChange}
              className="form-input"
            />
          </div>
          <div className="form-group">
            <label className="form-label">End Time (Est.)</label>
            <input
              type="datetime-local"
              name="end_time"
              value={form.end_time}
              onChange={handleChange}
              className="form-input"
            />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Status</label>
            <select
              name="status"
              value={form.status}
              onChange={handleChange}
              className="form-select"
            >
              {STATUSES.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Severity (1-3)</label>
            <select
              name="severity"
              value={form.severity}
              onChange={handleChange}
              className="form-select"
            >
              <option value={1}>Low</option>
              <option value={2}>Medium</option>
              <option value={3}>High</option>
            </select>
          </div>
        </div>

        {error && (
          <p style={{ color: 'var(--error)', fontSize: '13px', marginBottom: '12px' }}>
            {error}
          </p>
        )}

        <button
          type="submit"
          className="btn btn-primary"
          disabled={submitting}
          style={{ width: '100%', justifyContent: 'center' }}
        >
          {submitting ? 'Saving...' : isEdit ? 'Update Outage' : 'Create Outage'}
        </button>
      </form>
    </div>
  );
}
