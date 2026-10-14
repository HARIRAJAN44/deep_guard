import { useEffect, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, CheckCircle, AlertTriangle, HelpCircle, Download, Shield, Info, Cpu, BarChart3, Loader2, Trash2, RefreshCw } from 'lucide-react';
import { analysisService, APIError } from '../services/api';
import { useToast } from '../contexts/ToastContext';
import { ASSESSMENT_LABELS, MODEL_DISPLAY_NAMES, type AnalysisResult, type Assessment } from '../types';

function ConfidenceGauge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const r = 52;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (pct / 100) * circumference;
  const color = pct >= 70 ? '#ef4444' : pct >= 50 ? '#f59e0b' : '#22c55e';

  return (
    <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
      <svg width={128} height={128} className="confidence-ring">
        <circle className="confidence-ring-track" cx={64} cy={64} r={r} />
        <circle
          className="confidence-ring-fill"
          cx={64} cy={64} r={r}
          stroke={color}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div style={{ position: 'absolute', textAlign: 'center' }}>
        <div style={{ fontSize: '1.6rem', fontWeight: 900, color }}>{pct}%</div>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>confidence</div>
      </div>
    </div>
  );
}

function ModelBar({ name, score }: { name: string; score: number }) {
  const pct = Math.round(score * 100);
  const leansFake = score <= 0.5;
  const color = leansFake ? 'var(--danger)' : 'var(--success)';
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5, fontSize: '0.82rem' }}>
        <span style={{ color: 'var(--text-secondary)' }}>{name}</span>
        <span style={{ fontWeight: 700, color }}>{pct}% {leansFake ? '(fake-leaning)' : '(real-leaning)'}</span>
      </div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

export default function ResultPage() {
  const { requestId } = useParams<{ requestId: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [result, setResult] = useState<AnalysisResult | null>(location.state?.result ?? null);
  const [loading, setLoading] = useState(!result);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!result && requestId) {
      analysisService.getAnalysis(requestId)
        .then(setResult)
        .catch(err => { toast(err instanceof APIError ? err.message : 'Failed to load result', 'error'); navigate('/dashboard/history'); })
        .finally(() => setLoading(false));
    }
  }, [requestId]);

  const handleDelete = async () => {
    if (!requestId || !confirm('Delete this analysis record?')) return;
    setDeleting(true);
    try {
      await analysisService.deleteAnalysis(requestId);
      toast('Analysis deleted', 'success');
      navigate('/dashboard/history');
    } catch (err) {
      toast(err instanceof APIError ? err.message : 'Delete failed', 'error');
    } finally {
      setDeleting(false);
    }
  };

  const handleDownloadJSON = () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `deepguard-${result.request_id.slice(0, 8)}.json`;
    a.click();
  };

  if (loading) return <div className="flex items-center justify-center" style={{ padding: 80 }}><Loader2 size={36} className="animate-spin" color="var(--primary)" /></div>;
  if (!result) return null;

  const { assessment, assessment_confidence, assessment_explanation, assessment_reasons, stages, processing_time_ms, model_version, created_at } = result;
  const prov = stages.provenance;
  const meta = stages.metadata;
  const ens = stages.ensemble;

  const verdictClass = `verdict-${assessment}`;

  return (
    <div className="animate-fade-in" style={{ maxWidth: 800, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 32 }}>
        <button className="btn btn-ghost btn-icon" onClick={() => navigate(-1)} aria-label="Go back">
          <ArrowLeft size={18} />
        </button>
        <div>
          <h1 style={{ fontSize: '1.6rem', fontWeight: 800 }}>Forensic Analysis Report</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>
            ID: {result.request_id} · {new Date(created_at).toLocaleString()} · {processing_time_ms}ms · Model {model_version}
          </p>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          <button className="btn btn-secondary btn-sm" onClick={handleDownloadJSON}>
            <Download size={14} /> JSON
          </button>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/dashboard/analyze')}>
            <RefreshCw size={14} /> New
          </button>
          <button className="btn btn-danger btn-sm" onClick={handleDelete} disabled={deleting}>
            {deleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
          </button>
        </div>
      </div>

      {/* Final verdict */}
      <div className="card card-elevated" style={{ textAlign: 'center', marginBottom: 24, padding: 40 }}>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginBottom: 16, letterSpacing: '0.08em', textTransform: 'uppercase', fontWeight: 600 }}>Overall Assessment</p>
        <div className={`verdict-badge ${verdictClass}`} style={{ justifyContent: 'center', display: 'inline-flex', marginBottom: 24 }}>
          {assessment === 'likely_authentic' && <CheckCircle size={20} />}
          {['likely_ai_generated', 'likely_manipulated', 'suspicious'].includes(assessment) && <AlertTriangle size={20} />}
          {assessment === 'inconclusive' && <HelpCircle size={20} />}
          {ASSESSMENT_LABELS[assessment as Assessment] || assessment}
        </div>
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 20 }}>
          <ConfidenceGauge value={assessment_confidence} />
        </div>
        <p style={{ color: 'var(--text-secondary)', maxWidth: 580, margin: '0 auto 20px', lineHeight: 1.7, fontSize: '0.9rem' }}>
          {assessment_explanation}
        </p>
        {assessment_reasons.length > 0 && (
          <div style={{ textAlign: 'left', maxWidth: 580, margin: '0 auto' }}>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.78rem', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 10 }}>Key Evidence</p>
            {assessment_reasons.map((r, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 8, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                <span style={{ color: 'var(--primary)', flexShrink: 0 }}>•</span>
                {r}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Stage 1 — Provenance */}
      {prov && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
            <div className={`stage-number${prov.status === 'indicator_found' ? ' active' : prov.status === 'no_indicator_found' ? ' complete' : ''}`}>1</div>
            <h2 style={{ fontWeight: 700 }}>Stage 1 — Provenance Analysis</h2>
            <span className={`badge ${prov.status === 'indicator_found' ? 'badge-danger' : 'badge-success'}`} style={{ marginLeft: 'auto' }}>
              {prov.status === 'indicator_found' ? '⚠ Indicator Found' : '✓ None Detected'}
            </span>
          </div>
          {prov.provider && <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 8 }}><strong>Provider:</strong> {prov.provider} · Type: {prov.indicator_type} · Strength: {Math.round(prov.confidence * 100)}%</p>}
          <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.7 }}>{prov.explanation}</p>
          <div style={{ marginTop: 12, padding: '10px 14px', background: 'rgba(245,158,11,0.07)', borderRadius: 'var(--radius-sm)', fontSize: '0.78rem', color: 'var(--text-muted)', borderLeft: '3px solid var(--warning)' }}>
            ⚠️ Provenance indicators are forensic evidence — they do not constitute definitive proof of manipulation.
          </div>
        </div>
      )}

      {/* Stage 2 — Metadata */}
      {meta && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
            <div className="stage-number complete">2</div>
            <h2 style={{ fontWeight: 700 }}>Stage 2 — Metadata Forensics</h2>
            <span className={`badge ${meta.has_exif ? 'badge-info' : 'badge-muted'}`} style={{ marginLeft: 'auto' }}>
              {meta.has_exif ? 'Metadata Present' : 'No Metadata'}
            </span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12, marginBottom: 14 }}>
            {[
              { label: 'Camera Make', value: meta.camera_make },
              { label: 'Camera Model', value: meta.camera_model },
              { label: 'Software', value: meta.software },
              { label: 'Capture Time', value: meta.capture_timestamp },
              { label: 'GPS Present', value: meta.gps_present ? 'Yes' : 'No' },
              { label: 'Editing Software', value: meta.editing_software },
              { label: 'Integrity', value: meta.metadata_integrity },
            ].map(({ label, value }) => value && (
              <div key={label} style={{ padding: '10px 14px', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--bg-border)' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
                <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>{String(value)}</div>
              </div>
            ))}
          </div>
          <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.7 }}>{meta.explanation}</p>
          <div style={{ marginTop: 12, padding: '10px 14px', background: 'rgba(99,102,241,0.06)', borderRadius: 'var(--radius-sm)', fontSize: '0.78rem', color: 'var(--text-muted)', borderLeft: '3px solid var(--primary)' }}>
            ℹ️ EXIF metadata can be removed, modified, copied, or spoofed. Its presence or absence is evidence, not proof.
          </div>
        </div>
      )}

      {/* Stage 3 — ML Ensemble */}
      {ens && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
            <div className="stage-number complete">3</div>
            <h2 style={{ fontWeight: 700 }}>Stage 3 — ML Pattern Ensemble</h2>
            <span className="badge badge-info" style={{ marginLeft: 'auto' }}>
              {ens.models_run}/{ens.models_available} models
            </span>
          </div>
          <div style={{ marginBottom: 16 }}>
            {Object.entries(ens.models).map(([key, m]) => (
              m.status === 'success' && (
                <ModelBar key={key} name={MODEL_DISPLAY_NAMES[key] || key} score={m.score} />
              )
            ))}
          </div>
          <div style={{ padding: '14px 18px', background: 'var(--bg-surface)', borderRadius: 'var(--radius-md)', border: '1px solid var(--bg-border)', marginBottom: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <Cpu size={18} color="var(--primary)" />
              <div>
                <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>Ensemble Result: {ASSESSMENT_LABELS[ens.ensemble_label as Assessment] || ens.ensemble_label}</div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Score: {Math.round(ens.ensemble_score * 100)}% · {ens.explanation}</div>
              </div>
            </div>
          </div>
          <div style={{ padding: '10px 14px', background: 'rgba(245,158,11,0.07)', borderRadius: 'var(--radius-sm)', fontSize: '0.78rem', color: 'var(--text-muted)', borderLeft: '3px solid var(--warning)' }}>
            ⚠️ These are raw model scores from binary classifiers — not calibrated probabilities. They are pattern indicators, not specialized domain analysis.
          </div>
        </div>
      )}
    </div>
  );
}
