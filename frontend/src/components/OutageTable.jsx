import { useState, useEffect } from 'react';
import { getOutages, deleteOutage } from '../api';

const TYPE_LABELS = {
  planned_maintenance: 'Maintenance',
  emergency: 'Emergency',
  load_shedding: 'Load Shed',
};

const SOURCE_LABELS = {
  manual: 'Manual',
  bescom_scraper: 'BESCOM',
  crowd_detected: 'Crowd',
};

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

export default function OutageTable({ onEdit, refreshKey }) {
  const [outages, setOutages] = useState([]);
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadOutages();
  }, [filter, refreshKey]);

  async function loadOutages() {
    setLoading(true);
    try {
      const data = await getOutages(filter || undefined);
      setOutages(data);
    } catch (err) {
      console.error('Failed to load outages:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id) {
    if (!confirm('Delete this outage record?')) return;
    try {
      await deleteOutage(id);
      loadOutages();
    } catch (err) {
      alert('Delete failed: ' + err.message);
    }
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-icon">O</span>
          Outage Records
        </div>
        <div className="filter-row">
          {['', 'active', 'scheduled', 'resolved'].map((f) => (
            <button
              key={f}
              className={`filter-btn ${filter === f ? 'active' : ''}`}
              onClick={() => setFilter(f)}
            >
              {f || 'All'}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="empty-state">
          <p>Loading records...</p>
        </div>
      ) : outages.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">—</div>
          <p>No outage records found</p>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Area</th>
                <th>Type</th>
                <th>Reason</th>
                <th>Start</th>
                <th>End</th>
                <th>Status</th>
                <th>Source</th>
                <th style={{ width: '100px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {outages.map((o) => (
                <tr key={o.id}>
                  <td className="td-primary">{o.area_name}</td>
                  <td>
                    <span className={`badge ${o.outage_type === 'emergency' ? 'emergency' : 'scheduled'}`}>
                      <span className="badge-dot" />
                      {TYPE_LABELS[o.outage_type] || o.outage_type}
                    </span>
                  </td>
                  <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {o.reason || '\u2014'}
                  </td>
                  <td>{formatTime(o.start_time)}</td>
                  <td>{formatTime(o.end_time)}</td>
                  <td>
                    <span className={`badge ${o.status}`}>
                      <span className="badge-dot" />
                      {o.status}
                    </span>
                  </td>
                  <td>
                    <span className={`badge source-${o.source === 'crowd_detected' ? 'crowd' : o.source === 'bescom_scraper' ? 'scraper' : 'manual'}`}>
                      {SOURCE_LABELS[o.source] || o.source}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: '4px' }}>
                      <button className="btn btn-ghost btn-sm" onClick={() => onEdit?.(o)}>
                        Edit
                      </button>
                      <button className="btn btn-danger btn-sm" onClick={() => handleDelete(o.id)}>
                        Del
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
