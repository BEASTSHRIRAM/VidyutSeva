import { useState, useEffect, useCallback } from 'react';
import './index.css';
import DashboardStats from './components/DashboardStats';
import OutageTable from './components/OutageTable';
import OutageForm from './components/OutageForm';
import CallLog from './components/CallLog';
import LiveHeatmap from './components/LiveHeatmap';
import CrowdReports from './components/CrowdReports';
import AlertSubscriptions from './components/AlertSubscriptions';
import ChatPage from './components/ChatPage';
import ComplaintBoard from './components/ComplaintBoard';
import AdminDashboard from './components/AdminDashboard';
import AuthModal from './components/AuthModal';
import VapiWidget from './components/VapiWidget';
import { testVoice, triggerScraper, getComplaints } from './api';

const STEPS = [
  {
    num: '1',
    title: 'Citizen Reports Issue',
    desc: 'A Bangalore resident calls our AI hotline or submits a report through the web portal, describing their electricity problem in natural language.',
  },
  {
    num: '2',
    title: 'AI Agents Investigate',
    desc: 'Three specialized ReAct agents work in sequence: extracting your location, querying BESCOM data and historical records, then diagnosing the root cause.',
  },
  {
    num: '3',
    title: 'Accurate Diagnosis Delivered',
    desc: 'Within seconds, you receive an honest assessment: is this an area-wide outage or a building-specific issue, with actionable next steps tailored to your situation.',
  },
];

const FEATURES = [
  {
    icon: 'FC',
    title: 'Firecrawl-Powered Scraping',
    desc: 'Structured data extraction from BESCOM\u2019s outage pages using AI-driven web scraping, updated every 3 hours automatically.',
  },
  {
    icon: 'RA',
    title: 'ReAct Agent Reasoning',
    desc: 'Multi-agent pipeline built on AgentScope with tool-calling ReActAgents that reason through each case step by step.',
  },
  {
    icon: 'VS',
    title: 'Semantic Memory',
    desc: 'Qdrant vector store maintains outage history, call memory, and BESCOM knowledge for context-aware responses.',
  },
  {
    icon: 'CR',
    title: 'Crowdsourced Detection',
    desc: 'When 3 or more citizens report outages in the same area within 30 minutes, the system auto-flags it as a confirmed outage.',
  },
  {
    icon: 'PA',
    title: 'Proactive Alerts',
    desc: 'Subscribe to your locality and receive instant notifications when new outages are detected in your area.',
  },
  {
    icon: 'LM',
    title: 'Live Outage Map',
    desc: 'Real-time Bangalore heatmap showing outage zones, severity levels, and crowd-reported problem areas at a glance.',
  },
];

function LandingPage({ onNavigate }) {
  return (
    <>
      {/* Hero */}
      <section className="hero">
        <p className="hero-overline">AI-Powered Electricity Support</p>
        <h1 className="hero-title">
          Honest answers about your power cut, instantly
        </h1>
        <p className="hero-subtitle">
          VidyutSeva replaces unreliable IVR systems with an AI agent that
          checks real BESCOM data — and auto-dispatches linemen for hardware faults.
        </p>
        <div className="hero-actions">
          <button className="btn btn-primary" onClick={() => onNavigate('chat')}>
            Chat with AI Agent
          </button>
          <VapiWidget />
          <button className="btn btn-secondary" onClick={() => onNavigate('complaints')}>
            Community Reports
          </button>
        </div>

        <div className="hero-stats">
          <div className="hero-stat">
            <div className="hero-stat-value">20+</div>
            <div className="hero-stat-label">Bangalore Areas Covered</div>
          </div>
          <div className="hero-stat">
            <div className="hero-stat-value">4</div>
            <div className="hero-stat-label">ReAct Agents Running</div>
          </div>
          <div className="hero-stat">
            <div className="hero-stat-value">&lt;10s</div>
            <div className="hero-stat-label">Average Response Time</div>
          </div>
          <div className="hero-stat">
            <div className="hero-stat-value">15</div>
            <div className="hero-stat-label">Linemen on Roster</div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="section" id="how-it-works">
        <p className="section-overline">How It Works</p>
        <h2 className="section-title">Three agents, one honest answer</h2>
        <p className="section-subtitle">
          Our multi-agent pipeline uses ReAct reasoning to investigate your
          power issue from multiple data sources before responding.
        </p>
        <div className="steps-grid">
          {STEPS.map((step) => (
            <div key={step.num} className="step-card anim-stagger">
              <div className="step-number">{step.num}</div>
              <h3 className="step-title">{step.title}</h3>
              <p className="step-desc">{step.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features (Dark Section) */}
      <section className="section-dark" id="features">
        <div className="section-inner">
          <p className="section-overline" style={{ color: 'var(--coral)' }}>
            Features
          </p>
          <h2 className="section-title">
            Built for accuracy, not platitudes
          </h2>
          <p className="section-subtitle">
            Every component is designed to give Bangalore citizens truthful,
            data-backed electricity information.
          </p>
          <div className="features-grid">
            {FEATURES.map((f) => (
              <div key={f.title} className="feature-card anim-stagger">
                <div className="feature-icon">{f.icon}</div>
                <h3 className="feature-title">{f.title}</h3>
                <p className="feature-desc">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="cta-section">
        <p className="section-overline">Get Started</p>
        <h2 className="section-title">
          Stop guessing. Start knowing.
        </h2>
        <p className="section-subtitle">
          Chat with our 4-agent pipeline, report issues, upvote critical faults,
          and track BESCOM's auto-dispatched linemen in real time.
        </p>
        <div className="hero-actions">
          <button className="btn btn-primary" onClick={() => onNavigate('chat')}>
            Chat with AI Agent
          </button>
          <button className="btn btn-dark" onClick={() => onNavigate('complaints')}>
            View Community Reports
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="footer">
        <p className="footer-text">
          VidyutSeva &mdash; AI Electricity Support for Bangalore Citizens.
          Built with AgentScope, Firecrawl, Qdrant, and Vapi.
        </p>
      </footer>
    </>
  );
}

function DashboardPage() {
  const [tab, setTab] = useState('overview');
  const [editOutage, setEditOutage] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [scraperStatus, setScraperStatus] = useState(null);

  async function handleScrape() {
    setScraperStatus('running');
    try {
      const result = await triggerScraper();
      setScraperStatus(`Found: ${result.outages_found}, Stored: ${result.outages_stored}`);
      setRefreshKey((k) => k + 1);
    } catch (err) {
      setScraperStatus('Failed: ' + err.message);
    }
    setTimeout(() => setScraperStatus(null), 5000);
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1>Dashboard</h1>
          <p>Monitor outages, manage reports, and control the AI pipeline.</p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary btn-sm" onClick={handleScrape}>
            Run BESCOM Scraper
          </button>
        </div>
      </div>

      <DashboardStats />

      <div className="tabs">
        {[
          { key: 'overview', label: 'Overview' },
          { key: 'outages', label: 'Outages' },
          { key: 'map', label: 'Map' },
          { key: 'reports', label: 'Reports' },
          { key: 'alerts', label: 'Alerts' },
        ].map((t) => (
          <button
            key={t.key}
            className={`tab ${tab === t.key ? 'active' : ''}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <>
          <div className="content-grid full" style={{ marginBottom: 20 }}>
            <LiveHeatmap />
          </div>
          <div className="content-grid">
            <CallLog />
            <CrowdReports />
          </div>
        </>
      )}

      {tab === 'outages' && (
        <div className="content-grid">
          <div style={{ gridColumn: editOutage ? '1' : '1 / -1' }}>
            <OutageTable
              onEdit={(o) => setEditOutage(o)}
              refreshKey={refreshKey}
            />
          </div>
          {editOutage && (
            <OutageForm
              editData={editOutage}
              onClose={() => setEditOutage(null)}
              onSaved={() => {
                setEditOutage(null);
                setRefreshKey((k) => k + 1);
              }}
            />
          )}
        </div>
      )}

      {tab === 'map' && (
        <div className="content-grid full">
          <LiveHeatmap />
        </div>
      )}

      {tab === 'reports' && (
        <div className="content-grid">
          <CrowdReports />
          <OutageForm
            onSaved={() => setRefreshKey((k) => k + 1)}
          />
        </div>
      )}

      {tab === 'alerts' && (
        <div className="content-grid full">
          <AlertSubscriptions />
        </div>
      )}

      {scraperStatus && (
        <div className={`toast ${scraperStatus.startsWith('Failed') ? 'error' : 'success'}`}>
          {scraperStatus === 'running' ? 'Scraper running...' : scraperStatus}
        </div>
      )}
    </div>
  );
}

function TestPage() {
  const [message, setMessage] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleTest(e) {
    e.preventDefault();
    if (!message.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const data = await testVoice(message);
      setResult(data);
    } catch (err) {
      setResult({ response: 'Error: ' + err.message, area: '', diagnosis_type: 'error' });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Voice Agent Test</h1>
        <p>Simulate a citizen call to test the multi-agent pipeline.</p>
      </div>

      <div className="content-grid">
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title">
              <span className="panel-icon">T</span>
              Send Test Message
            </div>
          </div>
          <form onSubmit={handleTest}>
            <div className="form-group">
              <label className="form-label">Citizen Message</label>
              <textarea
                className="form-textarea"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Example: I live in Koramangala, my electricity has been cut for 2 hours now..."
                style={{ minHeight: '120px' }}
              />
            </div>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{ width: '100%', justifyContent: 'center' }}
            >
              {loading ? 'Processing through agent pipeline...' : 'Send to AI Agent'}
            </button>
          </form>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div className="panel-title">
              <span className="panel-icon">R</span>
              Agent Response
            </div>
          </div>

          {result ? (
            <div>
              <div style={{ marginBottom: '16px', display: 'flex', gap: '8px' }}>
                <span className={`badge ${result.outage_found ? 'active' : 'resolved'}`}>
                  <span className="badge-dot" />
                  {result.outage_found ? 'Outage Found' : 'No Outage'}
                </span>
                {result.area && (
                  <span className="badge source-manual">
                    Area: {result.area}
                  </span>
                )}
                {result.diagnosis_type && (
                  <span className="badge source-scraper">
                    {result.diagnosis_type}
                  </span>
                )}
              </div>
              <div style={{
                padding: '20px',
                background: 'var(--parchment)',
                borderRadius: 'var(--r-lg)',
                border: '1px solid var(--border-cream)',
                fontSize: '15px',
                lineHeight: '1.7',
                color: 'var(--near-black)',
                fontFamily: 'var(--font-serif)',
              }}>
                {result.response}
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">\u2014</div>
              <p>Send a message to see the agent response</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ComplaintsPage({ user, token }) {
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [area, setArea] = useState('');

  const fetchComplaints = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getComplaints({ area: area || undefined, sort: 'upvotes', limit: 50 });
      setComplaints(data || []);
    } catch (err) {
      console.error('Failed to load complaints:', err);
    } finally {
      setLoading(false);
    }
  }, [area]);

  useEffect(() => { fetchComplaints(); }, [fetchComplaints]);

  return (
    <div className="dashboard">
      <div className="dashboard-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1>Community Reports</h1>
          <p>Citizen-reported issues sorted by community upvotes. Hardware faults are auto-escalated to linemen.</p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <input
            className="form-input"
            placeholder="Filter by area…"
            value={area}
            onChange={(e) => setArea(e.target.value)}
            style={{ width: 180, marginBottom: 0 }}
          />
          <button className="btn btn-secondary btn-sm" onClick={fetchComplaints}>Filter</button>
        </div>
      </div>
      {loading
        ? <div style={{ textAlign: 'center', padding: 48, color: 'var(--charcoal)' }}>Loading reports…</div>
        : <ComplaintBoard complaints={complaints} onRefresh={fetchComplaints} user={user} token={token} />
      }
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState('landing');
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('vs_user')); } catch { return null; }
  });
  const [token, setToken] = useState(() => localStorage.getItem('vs_token') || null);
  const [showAuth, setShowAuth] = useState(false);

  const handleLoginSuccess = (u) => {
    setUser(u);
    setToken(localStorage.getItem('vs_token'));
  };

  const handleLogout = () => {
    localStorage.removeItem('vs_token');
    localStorage.removeItem('vs_user');
    setUser(null);
    setToken(null);
  };

  // Chat page renders full-screen with its own layout (no shared nav)
  if (page === 'chat') {
    return (
      <div style={{ position: 'relative' }}>
        <button
          onClick={() => setPage('landing')}
          style={{
            position: 'fixed', top: 16, left: 16, zIndex: 100,
            background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.12)',
            color: 'rgba(255,255,255,0.6)', borderRadius: 10, padding: '6px 14px',
            fontSize: 13, cursor: 'pointer', backdropFilter: 'blur(12px)',
          }}
        >← Back</button>
        <ChatPage />
      </div>
    );
  }

  // Admin dashboard also full-screen
  if (page === 'admin') {
    if (!user || user.role !== 'admin') {
      return (
        <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexDirection: 'column', gap: 16, fontFamily: 'Inter, sans-serif', background: '#f5f4ed' }}>
          <div style={{ fontSize: 40 }}>🔒</div>
          <h2 style={{ fontFamily: "'Playfair Display', serif", color: '#141413' }}>Admin Access Only</h2>
          <p style={{ color: '#87867f' }}>Please login with an admin account.</p>
          <button className="btn btn-primary" onClick={() => setShowAuth(true)}>Login</button>
          <button className="btn btn-secondary" onClick={() => setPage('landing')}>← Back</button>
          {showAuth && <AuthModal onClose={() => setShowAuth(false)} onLoginSuccess={handleLoginSuccess} />}
        </div>
      );
    }
    return (
      <div style={{ position: 'relative' }}>
        <button
          onClick={() => setPage('landing')}
          style={{ position: 'fixed', top: 16, left: 16, zIndex: 100,
            background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(0,0,0,0.12)',
            color: '#6b6b68', borderRadius: 10, padding: '6px 14px', fontSize: 13, cursor: 'pointer' }}
        >← Back</button>
        <AdminDashboard user={user} token={token} />
      </div>
    );
  }

  return (
    <>
      {/* Navigation */}
      <nav className="nav">
        <div className="nav-inner">
          <div className="nav-brand">
            <span className="nav-brand-name" style={{ cursor: 'pointer' }} onClick={() => setPage('landing')}>
              VidyutSeva
            </span>
            <span className="nav-brand-tag">Bangalore</span>
          </div>
          <div className="nav-links">
            <button className={`nav-link ${page === 'landing' ? 'active' : ''}`} onClick={() => setPage('landing')}>Home</button>
            <button className={`nav-link ${page === 'chat' ? 'active' : ''}`} onClick={() => setPage('chat')}>AI Chat</button>
            <button className={`nav-link ${page === 'complaints' ? 'active' : ''}`} onClick={() => setPage('complaints')}>Reports</button>
            <button className={`nav-link ${page === 'dashboard' ? 'active' : ''}`} onClick={() => setPage('dashboard')}>Dashboard</button>
            {user?.role === 'admin' && (
              <button className={`nav-link ${page === 'admin' ? 'active' : ''}`} onClick={() => setPage('admin')}
                style={{ color: '#c96442', fontWeight: 600 }}>Admin ⚡</button>
            )}
            {user ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 13, color: 'var(--charcoal)' }}>{user.name || user.phone}</span>
                <button className="btn btn-secondary btn-sm" onClick={handleLogout}>Logout</button>
              </div>
            ) : (
              <button className="nav-cta" onClick={() => setShowAuth(true)}>Login</button>
            )}
          </div>
        </div>
      </nav>

      {/* Auth Modal */}
      {showAuth && <AuthModal onClose={() => setShowAuth(false)} onLoginSuccess={handleLoginSuccess} />}

      {/* Pages */}
      {page === 'landing'    && <LandingPage onNavigate={setPage} />}
      {page === 'dashboard'  && <DashboardPage />}
      {page === 'test'       && <TestPage />}
      {page === 'complaints' && <ComplaintsPage user={user} token={token} />}
    </>
  );
}
