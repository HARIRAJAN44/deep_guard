import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { History, Filter, Search, ChevronLeft, ChevronRight, ArrowRight, AlertTriangle, CheckCircle, HelpCircle } from 'lucide-react';
import { usageService, APIError } from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { ASSESSMENT_LABELS, ASSESSMENT_COLORS, type Assessment } from '../types';

const ASSESSMENT_OPTIONS = ['', 'likely_authentic', 'likely_ai_generated', 'likely_manipulated', 'suspicious', 'inconclusive'];

export default function HistoryPage() {
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [page, setPage] = useState(1);
  const [assessment, setAssessment] = useState('');
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { toast } = useToast();

  useEffect(() => {
    setLoading(true);
    const filters: Record<string, string> = {};
    if (assessment) filters.assessment = assessment;
    usageService.getHistory(page, 20, filters)
      .then(data => { setItems(data.items); setTotal(data.total); setPages(data.pages); })
      .catch(err => toast(err instanceof APIError ? err.message : 'Failed to load history', 'error'))
      .finally(() => setLoading(false));
  }, [page, assessment]);

  const icon = (a: Assessment) => {
    if (a === 'likely_authentic') return <CheckCircle size={14} color="var(--success)" />;
    if (a === 'inconclusive') return <HelpCircle size={14} color="var(--text-muted)" />;
    return <AlertTriangle size={14} color={ASSESSMENT_COLORS[a] || 'var(--warning)'} />;
  };

  return (
    <div className="animate-fade-in">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 28, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: '1.8rem', fontWeight: 800, marginBottom: 4 }}>Analysis History</h1>
          <p style={{ color: 'var(--text-secondary)' }}>{total} total analyses</p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <select
            className="input"
            style={{ width: 'auto', minWidth: 200 }}
            value={assessment}
            onChange={e => { setAssessment(e.target.value); setPage(1); }}
            aria-label="Filter by assessment"
          >
            {ASSESSMENT_OPTIONS.map(opt => (
              <option key={opt} value={opt}>
                {opt ? ASSESSMENT_LABELS[opt as Assessment] : 'All Assessments'}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)' }}>Loading…</div>
        ) : items.length === 0 ? (
          <div style={{ padding: 60, textAlign: 'center' }}>
            <History size={40} color="var(--text-muted)" style={{ margin: '0 auto 12px' }} />
            <p style={{ color: 'var(--text-muted)' }}>No analyses found. Try adjusting your filter.</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Request ID</th>
                  <th>File</th>
                  <th>Assessment</th>
                  <th>Confidence</th>
                  <th>Processing</th>
                  <th>Date</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {items.map(item => (
                  <tr key={item.request_id}>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      {item.request_id.slice(0, 8)}…
                    </td>
                    <td style={{ maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.original_filename || 'unnamed'}
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        {icon(item.assessment)}
                        <span style={{ color: ASSESSMENT_COLORS[item.assessment as Assessment], fontWeight: 600, fontSize: '0.82rem' }}>
                          {ASSESSMENT_LABELS[item.assessment as Assessment] || item.assessment}
                        </span>
                      </div>
                    </td>
                    <td>{Math.round((item.assessment_confidence ?? 0) * 100)}%</td>
                    <td>{item.processing_time_ms}ms</td>
                    <td style={{ fontSize: '0.82rem', whiteSpace: 'nowrap' }}>
                      {new Date(item.created_at).toLocaleDateString()} {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td>
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => navigate(`/dashboard/result/${item.request_id}`)}
                        aria-label={`View analysis ${item.request_id}`}
                      >
                        View <ArrowRight size={13} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {pages > 1 && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, marginTop: 20 }}>
          <button className="btn btn-secondary btn-sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>
            <ChevronLeft size={16} />
          </button>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Page {page} of {pages}</span>
          <button className="btn btn-secondary btn-sm" onClick={() => setPage(p => Math.min(pages, p + 1))} disabled={page === pages}>
            <ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
