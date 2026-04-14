import { useState, useEffect } from 'react';
import { getDashboardSummary } from '../api';

export default function DashboardStats() {
  const [stats, setStats] = useState({
    active_outages: 0,
    calls_today: 0,
    unverified_reports: 0,
    active_subscriptions: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
    const interval = setInterval(loadStats, 30000);
    return () => clearInterval(interval);
  }, []);

  async function loadStats() {
    try {
      const data = await getDashboardSummary();
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    } finally {
      setLoading(false);
    }
  }

  const cards = [
    {
      label: 'Active Outages',
      value: stats.active_outages,
      variant: 'alert',
      indicator: 'alert',
    },
    {
      label: 'Calls Today',
      value: stats.calls_today,
      variant: 'accent',
      indicator: 'accent',
    },
    {
      label: 'Citizen Reports',
      value: stats.unverified_reports,
      variant: '',
      indicator: 'info',
    },
    {
      label: 'Subscriptions',
      value: stats.active_subscriptions,
      variant: 'success',
      indicator: 'success',
    },
  ];

  return (
    <div className="stats-grid">
      {cards.map((card, i) => (
        <div
          key={card.label}
          className={`stat-card ${card.variant} anim-stagger`}
          style={{ animationDelay: `${i * 0.08}s` }}
        >
          <div className="stat-label">
            <span className={`stat-indicator ${card.indicator}`} />
            {card.label}
          </div>
          <div className="stat-value">
            {loading ? '\u2014' : card.value}
          </div>
        </div>
      ))}
    </div>
  );
}
