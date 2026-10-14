import { useCallback, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, X, ImageIcon, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { analysisService, APIError } from '../services/api';
import { useToast } from '../contexts/ToastContext';

const STAGES = [
  { key: 'provenance', label: 'Stage 1 — Provenance Analysis', desc: 'Checking for AI generation indicators…' },
  { key: 'metadata', label: 'Stage 2 — Metadata Forensics', desc: 'Inspecting EXIF and image metadata…' },
  { key: 'ensemble', label: 'Stage 3 — ML Pattern Ensemble', desc: 'Running 5 trained AI pattern analyzers…' },
  { key: 'fusion', label: 'Evidence Fusion', desc: 'Combining all signals into final assessment…' },
];

const ALLOWED = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
const MAX_MB = 10;

export default function AnalyzePage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [currentStage, setCurrentStage] = useState(-1);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleFile = (f: File) => {
    setError(null);
    if (!ALLOWED.includes(f.type)) { setError('Only JPEG, PNG, and WEBP images are supported.'); return; }
    if (f.size > MAX_MB * 1024 * 1024) { setError(`File must be under ${MAX_MB} MB.`); return; }
    setFile(f);
    const reader = new FileReader();
    reader.onload = e => setPreview(e.target?.result as string);
    reader.readAsDataURL(f);
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, []);

  const handleAnalyze = async () => {
    if (!file) return;
    setAnalyzing(true);
    setError(null);
    setCurrentStage(0);

    try {
      // Simulate stage progress while waiting for the actual API call
      const timer = (ms: number) => new Promise(r => setTimeout(r, ms));
      const stageTimer = async () => {
        for (let i = 0; i < STAGES.length - 1; i++) {
          setCurrentStage(i);
          await timer(900);
        }
        setCurrentStage(STAGES.length - 1);
      };

      const [result] = await Promise.all([
        analysisService.analyzeImage(file),
        stageTimer(),
      ]);

      toast('Analysis complete!', 'success');
      navigate(`/dashboard/result/${result.request_id}`, { state: { result } });
    } catch (err) {
      const msg = err instanceof APIError ? err.message : 'Analysis failed. Please try again.';
      setError(msg);
      toast(msg, 'error');
    } finally {
      setAnalyzing(false);
      setCurrentStage(-1);
    }
  };

  return (
    <div className="animate-fade-in" style={{ maxWidth: 700, margin: '0 auto' }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: '1.8rem', fontWeight: 800, marginBottom: 8 }}>Analyze Image</h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          Upload an image to run the three-stage forensic pipeline. Results are probabilistic,
          not definitive.
        </p>
      </div>

      {/* Upload zone */}
      {!file && (
        <div
          className={`upload-zone${dragging ? ' dragover' : ''}`}
          onDragOver={e => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => fileRef.current?.click()}
          role="button"
          tabIndex={0}
          aria-label="Upload image for analysis"
          onKeyDown={e => e.key === 'Enter' && fileRef.current?.click()}
        >
          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
            aria-hidden="true"
          />
          <Upload size={48} color="var(--text-muted)" style={{ margin: '0 auto 16px' }} />
          <p style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: 8 }}>Drop an image here</p>
          <p style={{ color: 'var(--text-muted)', marginBottom: 16 }}>or click to browse files</p>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Supports JPEG, PNG, WEBP — max {MAX_MB} MB</p>
        </div>
      )}

      {/* Preview */}
      {file && !analyzing && (
        <div className="card animate-fade-in">
          <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start', flexWrap: 'wrap' }}>
            <div style={{ width: 160, height: 120, borderRadius: 'var(--radius-md)', overflow: 'hidden', background: 'var(--bg-surface)', flexShrink: 0, border: '1px solid var(--bg-border)' }}>
              {preview && <img src={preview} alt="Preview" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />}
            </div>
            <div style={{ flex: 1, minWidth: 200 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <ImageIcon size={16} color="var(--text-muted)" />
                <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{file.name}</span>
              </div>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: 4 }}>
                {(file.size / 1024 / 1024).toFixed(2)} MB · {file.type}
              </p>
              <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
                <button className="btn btn-primary" onClick={handleAnalyze}>
                  Run Analysis
                </button>
                <button className="btn btn-ghost" onClick={() => { setFile(null); setPreview(null); setError(null); }}>
                  <X size={16} /> Remove
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Stage progress during analysis */}
      {analyzing && (
        <div className="card animate-fade-in">
          <div style={{ textAlign: 'center', marginBottom: 28 }}>
            <Loader2 size={36} color="var(--primary)" className="animate-spin" style={{ margin: '0 auto 12px' }} />
            <h3 style={{ fontWeight: 700 }}>Analyzing image…</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: 4 }}>
              Please wait while we run the forensic pipeline
            </p>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {STAGES.map((stage, i) => (
              <div key={stage.key} className={`stage-card${i === currentStage ? ' active' : ''}${i < currentStage ? ' complete' : ''}`}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div className={`stage-number${i === currentStage ? ' active' : ''}${i < currentStage ? ' complete' : ''}`}>
                    {i < currentStage ? <CheckCircle2 size={14} /> : i + 1}
                  </div>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{stage.label}</div>
                    {i === currentStage && (
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 2 }}>{stage.desc}</div>
                    )}
                    {i < currentStage && (
                      <div style={{ fontSize: '0.78rem', color: 'var(--success)', marginTop: 2 }}>Complete</div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="card animate-fade-in" style={{ borderColor: 'var(--danger)', background: 'rgba(239,68,68,0.05)', display: 'flex', alignItems: 'center', gap: 12 }}>
          <AlertCircle size={20} color="var(--danger)" style={{ flexShrink: 0 }} />
          <div>
            <div style={{ fontWeight: 600, color: 'var(--danger)', marginBottom: 4 }}>Analysis Error</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.88rem' }}>{error}</div>
          </div>
        </div>
      )}

      {/* Info disclaimer */}
      <div style={{ marginTop: 24, padding: '14px 18px', background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.15)', borderRadius: 'var(--radius-md)', fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
        ℹ️ <strong style={{ color: 'var(--text-secondary)' }}>Privacy note:</strong> By default, images are deleted immediately after analysis. You can change this per API key in Settings → API Keys.
      </div>
    </div>
  );
}
