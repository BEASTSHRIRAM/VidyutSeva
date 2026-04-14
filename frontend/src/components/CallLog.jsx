import { useState, useEffect } from 'react';
import { getRecentCalls } from '../api';

function formatTime(iso) {
  if (!iso) return '\u2014';
  const d = new Date(iso);
  return d.toLocaleString('en-IN', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

const DIAGNOSIS_LABELS = {
  area_outage: 'Area Outage',
  building_issue: 'Building Issue',
  crowd_reported: 'Crowd Signal',
  unknown: 'Unknown',
  error: 'Error',
};

export default function CallLog() {
  const [calls, setCalls] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadCalls();
  }, []);

  async function loadCalls() {
    try {
      const data = await getRecentCalls(15);
      setCalls(data);
    } catch (err) {
      console.error('Failed to load calls:', err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-icon">C</span>
          Recent Calls
        </div>
        <button className="btn btn-ghost btn-sm" onClick={loadCalls}>
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="empty-state">
          <p>Loading call log...</p>
        </div>
      ) : calls.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">\u2014</div>
          <p>No calls recorded yet</p>
        </div>
      ) : (
        <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
          {calls.map((call, i) => (
            <div
              key={call.id || i}
              style={{
                padding: '14px 0',
                borderBottom: '1px solid var(--border-cream)',
              }}
            >
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '6px',
              }}>
                <span style={{
                  fontWeight: 600,
                  fontSize: '14px',
                  color: 'var(--near-black)',
                }}>
                  {call.caller_area || 'Unknown Area'}
                </span>
                <span style={{
                  fontSize: '12px',
                  color: 'var(--stone-gray)',
                }}>
                  {formatTime(call.call_timestamp)}
                </span>
              </div>

              <p style={{
                fontSize: '13px',
                color: 'var(--olive-gray)',
                marginBottom: '6px',
                lineHeight: '1.5',
              }}>
                {call.user_message
                  ? (call.user_message.length > 120
                      ? call.user_message.slice(0, 120) + '...'
                      : call.user_message)
                  : 'No message recorded'}
              </p>

              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <span className={`badge ${call.outage_found ? 'active' : 'resolved'}`}>
                  {call.outage_found ? 'Outage Found' : 'No Outage'}
                </span>
                <span className="badge source-manual" style={{ fontSize: '10px' }}>
                  {DIAGNOSIS_LABELS[call.diagnosis_type] || call.diagnosis_type}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
