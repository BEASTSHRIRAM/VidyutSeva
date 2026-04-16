/**
 * BESCOM Admin Dashboard - Escalation tracker.
 * Parchment design system, zero emojis.
 */
import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { getAdminEscalations, getComplaints } from '../api';

const STATUS_STYLE = {
  escalated:    { bg: 'rgba(201,100,66,0.08)', text: '#c96442', border: 'rgba(201,100,66,0.15)' },
  acknowledged: { bg: 'rgba(251,191,36,0.08)', text: '#d4a017', border: 'rgba(251,191,36,0.15)' },
  dispatched:   { bg: 'rgba(129,140,248,0.08)',text: '#818cf8', border: 'rgba(129,140,248,0.15)' },
  resolved:     { bg: 'rgba(52,211,153,0.08)', text: '#34d399', border: 'rgba(52,211,153,0.15)' },
};

function StatCard({ label, value, accent }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      style={{ background: '#faf9f5', border: '1px solid #f0eee6', borderRadius: 12,
        padding: '20px 22px', boxShadow: 'rgba(0,0,0,0.03) 0px 2px 12px' }}>
      <div style={{ fontSize: 28, fontWeight: 700, color: '#141413', lineHeight: 1, fontFamily: "'Georgia', serif" }}>
        {value}
      </div>
      <div style={{ fontSize: 13, color: '#87867f', marginTop: 6 }}>{label}</div>
      <div style={{ width: '100%', height: 3, borderRadius: 2, background: '#f0eee6', marginTop: 12 }}>
        <div style={{ width: value > 0 ? '100%' : '0%', height: '100%', borderRadius: 2,
          background: accent || '#c96442', transition: 'width 0.3s' }} />
      </div>
    </motion.div>
  );
}

function EscalationRow({ esc, i }) {
  const st = STATUS_STYLE[esc.status] || STATUS_STYLE.escalated;
  return (
    <motion.div initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }}
      transition={{ delay: i * 0.04 }}
      style={{ background: '#faf9f5', border: '1px solid #f0eee6', borderRadius: 12,
        padding: '16px 20px', display: 'flex', gap: 16, alignItems: 'flex-start' }}>
      {/* Fault badge */}
      <div style={{ width: 42, height: 42, borderRadius: 10, background: '#f5f4ed',
        border: '1px solid #e8e6dc', display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0, fontSize: 11, fontWeight: 700, color: '#5e5d59', textTransform: 'uppercase' }}>
        {(esc.fault_type || '?').slice(0, 4)}
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 8, alignItems: 'center' }}>
          <span style={{ fontWeight: 600, fontSize: 13, color: '#141413', fontFamily: "'Georgia', serif" }}>
            {esc.complaint_ref || esc.complaint_id || 'Unknown'}
          </span>
          <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 6,
            background: st.bg, color: st.text, border: `1px solid ${st.border}`,
            fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.3px' }}>
            {esc.status || 'escalated'}
          </span>
          <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 6,
            background: '#f5f4ed', color: '#5e5d59', border: '1px solid #e8e6dc' }}>
            {esc.fault_type || 'unknown'} fault
          </span>
          {esc.complaint_area && (
            <span style={{ fontSize: 11, color: '#87867f' }}>{esc.complaint_area}</span>
          )}
        </div>

        {esc.report_text && (
          <div style={{ fontSize: 13, color: '#5e5d59', marginBottom: 10, lineHeight: 1.5,
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            &ldquo;{esc.report_text?.substring(0, 120)}{esc.report_text?.length > 120 ? '...' : ''}&rdquo;
          </div>
        )}

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, fontSize: 12, color: '#87867f' }}>
          <span>Lineman: <strong style={{ color: '#3d3d3a' }}>{esc.lineman_name || 'Unassigned'}</strong>
            {esc.lineman_phone && ` \u00b7 ${esc.lineman_phone}`}</span>
          {esc.distance_km && <span>{esc.distance_km} km</span>}
          {esc.confidence && <span>{Math.round(esc.confidence * 100)}% conf.</span>}
          <span>Call: {esc.call_status || 'pending'}</span>
          <span>{new Date(esc.escalated_at).toLocaleString()}</span>
        </div>
      </div>

      {esc.upvote_count > 0 && (
        <div style={{ textAlign: 'center', flexShrink: 0 }}>
          <div style={{ fontSize: 18, fontWeight: 700, color: '#c96442' }}>{esc.upvote_count}</div>
          <div style={{ fontSize: 10, color: '#87867f' }}>votes</div>
        </div>
      )}
    </motion.div>
  );
}

export default function AdminDashboard({ user, token }) {
  const [escalations, setEscalations] = useState([]);
  const [topComplaints, setTopComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('escalations');
  const [filterStatus, setFilterStatus] = useState('all');
  const [lastRefresh, setLastRefresh] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [esc, comps] = await Promise.all([
        getAdminEscalations(token), getComplaints({ sort: 'upvotes', limit: 20 }),
      ]);
      setEscalations(esc || []);
      setTopComplaints(comps || []);
      setLastRefresh(new Date());
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => { fetchData(); const i = setInterval(fetchData, 30000); return () => clearInterval(i); }, [fetchData]);

  const filtered = filterStatus === 'all' ? escalations : escalations.filter(e => e.status === filterStatus);
  const stats = {
    total: escalations.length,
    pending: escalations.filter(e => e.status === 'escalated').length,
    dispatched: escalations.filter(e => e.status === 'dispatched').length,
    resolved: escalations.filter(e => e.status === 'resolved').length,
  };

  return (
    <div style={{ minHeight: '100vh', background: '#f5f4ed', fontFamily: "'Inter', sans-serif" }}>

      {/* Dark header */}
      <div style={{ background: '#141413', padding: '16px 32px', display: 'flex', alignItems: 'center',
        gap: 16, borderBottom: '1px solid #30302e' }}>
        <div style={{ width: 36, height: 36, borderRadius: 10, background: '#c96442',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 12, fontWeight: 800, color: '#faf9f5' }}>AD</div>
        <div>
          <h1 style={{ fontFamily: "'Georgia', serif", fontSize: 18, fontWeight: 500,
            color: '#faf9f5', margin: 0 }}>BESCOM Admin Dashboard</h1>
          <p style={{ fontSize: 12, color: '#87867f', margin: 0 }}>
            {user?.name || 'Admin'} &middot; {lastRefresh ? `Refreshed ${lastRefresh.toLocaleTimeString()}` : 'Loading...'}
          </p>
        </div>
        <button onClick={fetchData} style={{ marginLeft: 'auto', background: '#30302e',
          border: '1px solid #30302e', color: '#b0aea5', borderRadius: 8,
          padding: '6px 14px', fontSize: 12, cursor: 'pointer' }}>Refresh</button>
      </div>

      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '28px 24px' }}>

        {/* Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 14, marginBottom: 28 }}>
          <StatCard label="Total Escalations" value={stats.total} accent="#c96442" />
          <StatCard label="Pending Dispatch" value={stats.pending} accent="#d4a017" />
          <StatCard label="Dispatched" value={stats.dispatched} accent="#818cf8" />
          <StatCard label="Resolved" value={stats.resolved} accent="#34d399" />
          <StatCard label="Community Reports" value={topComplaints.length} accent="#87867f" />
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 6, marginBottom: 20, flexWrap: 'wrap' }}>
          {[['escalations', 'Escalations'], ['top_complaints', 'Top Complaints']].map(([t, label]) => (
            <button key={t} onClick={() => setTab(t)} style={{
              padding: '8px 20px', borderRadius: 8, fontSize: 13, cursor: 'pointer', fontWeight: 500,
              background: tab === t ? '#141413' : '#faf9f5',
              color: tab === t ? '#faf9f5' : '#5e5d59',
              border: `1px solid ${tab === t ? '#141413' : '#e8e6dc'}`,
              boxShadow: tab === t ? 'none' : '#e8e6dc 0px 0px 0px 0px, #e8e6dc 0px 0px 0px 1px',
              fontFamily: "'Inter', sans-serif",
            }}>{label}</button>
          ))}
          {tab === 'escalations' && (
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
              {['all', 'escalated', 'dispatched', 'resolved'].map(s => (
                <button key={s} onClick={() => setFilterStatus(s)} style={{
                  padding: '6px 12px', borderRadius: 8, fontSize: 12, cursor: 'pointer',
                  background: filterStatus === s ? '#c96442' : '#faf9f5',
                  color: filterStatus === s ? '#faf9f5' : '#87867f',
                  border: `1px solid ${filterStatus === s ? '#c96442' : '#e8e6dc'}`,
                  textTransform: 'capitalize', fontWeight: 500,
                }}>{s}</button>
              ))}
            </div>
          )}
        </div>

        {/* Content */}
        {loading ? (
          <div style={{ textAlign: 'center', padding: 48, color: '#87867f' }}>Loading dashboard...</div>
        ) : tab === 'escalations' ? (
          filtered.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 56 }}>
              <div style={{ fontSize: 20, color: '#b0aea5', marginBottom: 8 }}>&mdash;</div>
              <p style={{ color: '#87867f', fontSize: 14 }}>No escalations matching filter</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {filtered.map((e, i) => <EscalationRow key={e.id || i} esc={e} i={i} />)}
            </div>
          )
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {topComplaints.map((c, i) => (
              <motion.div key={c.id || i} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.03 }}
                style={{ background: '#faf9f5', border: '1px solid #f0eee6', borderRadius: 12,
                  padding: '16px 20px', display: 'flex', gap: 16, alignItems: 'center' }}>
                <div style={{ textAlign: 'center', minWidth: 44 }}>
                  <div style={{ fontSize: 20, fontWeight: 700, color: '#c96442' }}>{c.upvote_count || 0}</div>
                  <div style={{ fontSize: 10, color: '#87867f' }}>votes</div>
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 12, fontWeight: 600, color: '#141413' }}>{c.complaint_id}</span>
                    <span style={{ fontSize: 11, color: '#87867f' }}>{c.area}</span>
                    {c.escalated && (
                      <span style={{ fontSize: 11, padding: '1px 8px', borderRadius: 6,
                        background: 'rgba(201,100,66,0.08)', color: '#c96442',
                        border: '1px solid rgba(201,100,66,0.15)' }}>Escalated</span>
                    )}
                  </div>
                  <div style={{ fontSize: 13, color: '#5e5d59', lineHeight: 1.5 }}>
                    {c.text?.substring(0, 130)}{c.text?.length > 130 ? '...' : ''}
                  </div>
                </div>
                <div style={{ fontSize: 11, color: '#b0aea5', flexShrink: 0 }}>
                  {new Date(c.created_at).toLocaleDateString()}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
