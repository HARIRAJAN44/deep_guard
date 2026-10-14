import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Shield, TrendingUp, CheckCircle, AlertTriangle, HelpCircle, BarChart3, Key, Activity, ArrowRight } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { userService, usageService } from '../services/api';
import { ASSESSMENT_LABELS, ASSESSMENT_COLORS, type Assessment } from '../types';
import { AreaChart, Area, PieChart, Pie, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

const VERDICT_ICONS: Record<Assessment, React.ReactNode> = {
  likely_authentic: <CheckCircle size={14} color="var(--success)" />,
  likely_ai_generated: <AlertTriangle size={14} color="var(--danger)" />,
  likely_manipulated: <AlertTriangle size={14} color="#f97316" />,
  suspicious: <HelpCircle size={14} color="var(--warning)" />,
  inconclusive: <HelpCircle size={14} color="var(--text-muted)" />,
};

function StatCard({ icon: Icon, label, value, color }: { icon: any; label: string; value: string | number; color?: string }) {
  return (
    <div className="card" style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
      <div style={{ width: 48, height: 48, borderRadius: 'var(--radius-md)', background: color ? `${color}20` : 'var(--primary-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
        <Icon size={22} color={color || 'var(--primary)'} />
      </div>
      <div>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginBottom: 4 }}>{label}</div>
        <div style={{ fontSize: '1.6rem', fontWeight: 800 }}>{value}</div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState<any>(null);
  const [usage, setUsage] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([userService.getStats(), usageService.getUsage(30)])
      .then(([s, u]) => { setStats(s); setUsage(u); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const pieData = stats?.assessments
    ? Object.entries(stats.assessments)
        .filter(([, v]) => (v as number) > 0)
        .map(([k, v]) => ({ name: ASSESSMENT_LABELS[k as Assessment] || k, value: v, color: ASSESSMENT_COLORS[k as Assessment] || '#888' }))
    : [];

  const total = stats?.total_analyses ?? 0;
  const recent = stats?.recent_analyses ?? [];
  const dailySeries = usage?.daily_series ?? [];

  return (
    <div className="animate-fade-in">
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: '1.8rem', fontWeight: 800, marginBottom: 6 }}>
          Welcome back, {user?.name?.split(' ')[0]} 👋
        </h1>
        <p style={{ color: 'var(--text-secondary)' }}>Here's an overview of your forensic analysis activity.</p>
      </div>

      {/* Quick Action */}
      <div className="card card-elevated" style={{ marginBottom: 28, background: 'linear-gradient(135deg, rgba(99,102,241,0.12) 0%, rgba(168,85,247,0.08) 100%)', borderColor: 'rgba(99,102,241,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <h3 style={{ fontWeight: 700, marginBottom: 4 }}>Analyze an Image</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>Run the three-stage forensic pipeline on any JPEG, PNG, or WEBP file</p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate('/dashboard/analyze')}>
          Start Analysis <ArrowRight size={16} />
        </button>
      </div>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 28 }}>
        <StatCard icon={Shield} label="Total Analyses" value={loading ? '…' : total} />
        <StatCard icon={CheckCircle} label="Likely Authentic" value={loading ? '…' : stats?.assessments?.likely_authentic ?? 0} color="var(--success)" />
        <StatCard icon={AlertTriangle} label="Likely Fake/AI" value={loading ? '…' : (stats?.assessments?.likely_ai_generated ?? 0) + (stats?.assessments?.likely_manipulated ?? 0)} color="var(--danger)" />
        <StatCard icon={Activity} label="API Requests (30d)" value={loading ? '…' : usage?.total_requests ?? 0} color="var(--secondary)" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 20, marginBottom: 28 }}>
        {/* Area chart */}
        {dailySeries.length > 0 && (
          <div className="card">
            <h3 style={{ fontWeight: 700, marginBottom: 20 }}>Analyses Over Time (30 days)</h3>
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={dailySeries}>
                <defs>
                  <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="var(--primary)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--bg-border)', borderRadius: 8, color: 'var(--text-primary)' }} />
                <Area type="monotone" dataKey="count" stroke="var(--primary)" fill="url(#grad)" strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Pie chart */}
        {pieData.length > 0 && (
          <div className="card">
            <h3 style={{ fontWeight: 700, marginBottom: 20 }}>Verdict Distribution</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
              <PieChart width={140} height={140}>
                <Pie data={pieData} cx={65} cy={65} innerRadius={40} outerRadius={65} dataKey="value" paddingAngle={2}>
                  {pieData.map((entry: any, i: number) => <Cell key={i} fill={entry.color} />)}
                </Pie>
              </PieChart>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {pieData.map((d: any, i: number) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.82rem' }}>
                    <div style={{ width: 10, height: 10, borderRadius: 2, background: d.color, flexShrink: 0 }} />
                    <span style={{ color: 'var(--text-secondary)' }}>{d.name}</span>
                    <span style={{ marginLeft: 'auto', fontWeight: 700 }}>{d.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Recent analyses table */}
      {recent.length > 0 && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h3 style={{ fontWeight: 700 }}>Recent Analyses</h3>
            <Link to="/dashboard/history" className="btn btn-ghost btn-sm">View all</Link>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Request ID</th>
                  <th>Assessment</th>
                  <th>Confidence</th>
                  <th>Time</th>
                  <th>Date</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {recent.map((r: any) => (
                  <tr key={r.request_id}>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.78rem', color: 'var(--text-muted)' }}>{r.request_id.slice(0, 8)}…</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        {VERDICT_ICONS[r.assessment as Assessment]}
                        <span className={`assessment-${r.assessment}`} style={{ fontSize: '0.82rem', fontWeight: 600 }}>
                          {ASSESSMENT_LABELS[r.assessment as Assessment] || r.assessment}
                        </span>
                      </div>
                    </td>
                    <td>{Math.round((r.assessment_confidence ?? 0) * 100)}%</td>
                    <td>{r.processing_time_ms}ms</td>
                    <td style={{ fontSize: '0.8rem' }}>{new Date(r.created_at).toLocaleDateString()}</td>
                    <td>
                      <button className="btn btn-ghost btn-sm" onClick={() => navigate(`/dashboard/result/${r.request_id}`)}>
                        View <ArrowRight size={13} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {total === 0 && !loading && (
        <div className="card text-center" style={{ padding: 60 }}>
          <Shield size={48} color="var(--text-muted)" style={{ margin: '0 auto 16px' }} />
          <h3 style={{ fontWeight: 700, marginBottom: 8 }}>No analyses yet</h3>
          <p style={{ color: 'var(--text-muted)', marginBottom: 24 }}>Upload an image to start your first forensic analysis.</p>
          <button className="btn btn-primary" onClick={() => navigate('/dashboard/analyze')}>Analyze First Image</button>
        </div>
      )}
    </div>
  );
}
