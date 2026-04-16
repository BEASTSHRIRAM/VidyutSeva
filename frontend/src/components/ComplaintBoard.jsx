/**
 * ComplaintBoard - Community reports with upvote system.
 * Warm parchment design system, zero emojis.
 */
import { useState } from 'react';
import { submitCrowdReport, upvoteComplaint } from '../api';

export default function ComplaintBoard({ complaints = [], onRefresh, user, token }) {
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ text: '', area: '', phone_number: '' });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await submitCrowdReport({ ...formData, phone_number: user?.phone || formData.phone_number });
      setShowForm(false);
      setFormData({ text: '', area: '', phone_number: '' });
      if (onRefresh) onRefresh();
    } catch (err) { alert(err.message); }
    finally { setLoading(false); }
  };

  const handleUpvote = async (id) => {
    if (!user) { alert('Please login to upvote'); return; }
    try { await upvoteComplaint(id, token); if (onRefresh) onRefresh(); }
    catch (err) { alert(err.message); }
  };

  return (
    <div className="panel" style={{ background: '#faf9f5', border: '1px solid #e8e6dc', borderRadius: 16 }}>
      <div className="panel-header" style={{ borderBottom: '1px solid #f0eee6', paddingBottom: 16 }}>
        <div className="panel-title" style={{ fontFamily: "'Georgia', serif", color: '#141413', fontWeight: 500 }}>
          <span className="panel-icon" style={{ background: 'rgba(201,100,66,0.08)', color: '#c96442' }}>CR</span>
          Community Reports {user?.role === 'admin' && '(Admin View)'}
        </div>
        <button className="btn btn-primary btn-sm" onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Cancel' : 'Report Issue'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} style={{ marginBottom: 24, padding: 20, background: '#fff',
          borderRadius: 12, border: '1px solid #f0eee6',
          boxShadow: 'rgba(0,0,0,0.05) 0px 4px 24px' }}>
          <div className="form-group">
            <label className="form-label">Area / Locality</label>
            <input className="form-input" required value={formData.area}
              onChange={(e) => setFormData({ ...formData, area: e.target.value })}
              placeholder="e.g. Koramangala" />
          </div>
          <div className="form-group">
            <label className="form-label">Issue Description</label>
            <textarea className="form-textarea" required value={formData.text}
              onChange={(e) => setFormData({ ...formData, text: e.target.value })}
              placeholder="Describe the problem" />
          </div>
          {!user && (
            <div className="form-group">
              <label className="form-label">Phone Number (Optional)</label>
              <input className="form-input" type="tel" value={formData.phone_number}
                onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                placeholder="For tracking" />
            </div>
          )}
          <button type="submit" className="btn btn-primary" disabled={loading}
            style={{ width: '100%', justifyContent: 'center' }}>
            {loading ? 'Submitting...' : 'Submit Report'}
          </button>
        </form>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {complaints.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon" style={{ color: '#b0aea5' }}>&mdash;</div>
            <p>No community reports found</p>
          </div>
        ) : complaints.map((c) => (
          <div key={c.id} style={{ display: 'flex', gap: 16, padding: 16, background: '#fff',
            borderRadius: 12, border: '1px solid #f0eee6' }}>

            {/* Upvote */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, minWidth: 44 }}>
              <button onClick={() => handleUpvote(c.id)}
                style={{ background: 'none', border: 'none',
                  cursor: user ? 'pointer' : 'default',
                  fontSize: 18, color: user ? '#c96442' : '#b0aea5', lineHeight: 1,
                  padding: '4px 8px', borderRadius: 6,
                  transition: 'background 0.15s',
                }}
                onMouseEnter={(e) => user && (e.target.style.background = 'rgba(201,100,66,0.08)')}
                onMouseLeave={(e) => (e.target.style.background = 'none')}>
                &#9650;
              </button>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#141413' }}>{c.upvote_count || 0}</div>
            </div>

            {/* Content */}
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                  <span className="badge source-crowd">{c.area}</span>
                  {c.fault_type && <span className="badge source-scraper">{c.fault_type}</span>}
                  {c.escalated && <span className="badge active"><span className="badge-dot" /> ESCALATED</span>}
                  {c.status === 'resolved' && <span className="badge resolved">RESOLVED</span>}
                </div>
                <div style={{ fontSize: 12, color: '#87867f' }}>{new Date(c.created_at).toLocaleDateString()}</div>
              </div>
              <div style={{ fontSize: 14, color: '#4d4c48', lineHeight: 1.6, marginBottom: 8 }}>{c.text}</div>
              {user?.role === 'admin' && (
                <div style={{ padding: '8px 12px', background: '#f5f4ed', borderRadius: 8,
                  fontSize: 12, display: 'flex', gap: 16, color: '#5e5d59' }}>
                  <span><strong>ID:</strong> {c.complaint_id}</span>
                  <span><strong>Status:</strong> {c.status}</span>
                  {c.phone_number && <span><strong>Phone:</strong> {c.phone_number}</span>}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
