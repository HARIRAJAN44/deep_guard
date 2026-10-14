import { useState } from 'react';
import { Cpu, Copy, Check, Code2, Terminal, Zap } from 'lucide-react';
import { Link } from 'react-router-dom';

const TABS = ['cURL', 'Python', 'JavaScript'];

const CODE: Record<string, string> = {
  cURL: `curl -X POST https://localhost:8000/api/v1/analyze/image \\
  -H "Authorization: Bearer dg_live_YOUR_API_KEY" \\
  -F "file=@image.jpg"`,
  Python: `import requests

url = "http://localhost:8000/api/v1/analyze/image"
headers = {"Authorization": "Bearer dg_live_YOUR_API_KEY"}

with open("image.jpg", "rb") as f:
    response = requests.post(
        url,
        headers=headers,
        files={"file": f}
    )

result = response.json()
print(result["data"]["assessment"])
print(result["data"]["assessment_confidence"])`,
  JavaScript: `const formData = new FormData();
formData.append('file', imageFile);

const response = await fetch(
  'http://localhost:8000/api/v1/analyze/image',
  {
    method: 'POST',
    headers: { 'Authorization': 'Bearer dg_live_YOUR_API_KEY' },
    body: formData,
  }
);

const { data } = await response.json();
console.log(data.assessment, data.assessment_confidence);`,
};

const RESPONSE_EXAMPLE = `{
  "success": true,
  "data": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "assessment": "likely_ai_generated",
    "assessment_confidence": 0.87,
    "assessment_explanation": "Based on multi-stage forensic analysis, this image is assessed as: LIKELY AI-GENERATED (confidence: 87%)...",
    "assessment_reasons": [
      "A provenance indicator associated with 'Stable Diffusion' was detected.",
      "The ML ensemble (5 analyzers) indicates manipulated/synthetic characteristics."
    ],
    "stages": {
      "provenance": {
        "status": "indicator_found",
        "provider": "Stable Diffusion",
        "confidence": 0.85,
        "explanation": "..."
      },
      "metadata": {
        "has_exif": false,
        "metadata_integrity": "missing",
        "explanation": "No EXIF metadata was detected."
      },
      "ensemble": {
        "models": {
          "color_pattern": { "label": "likely_fake", "score": 0.21, "status": "success" },
          "facial_pattern": { "label": "likely_fake", "score": 0.18, "status": "success" },
          "texture_pattern": { "label": "likely_fake", "score": 0.09, "status": "success" },
          "temporal_feature": { "label": "inconclusive", "score": 0.49, "status": "success" },
          "artifact_pattern": { "label": "likely_fake", "score": 0.13, "status": "success" }
        },
        "ensemble_label": "likely_fake",
        "ensemble_score": 0.22,
        "models_run": 5
      }
    },
    "model_version": "v1",
    "processing_time_ms": 1240
  }
}`;

const ENDPOINTS = [
  { method: 'POST', path: '/api/v1/analyze/image', desc: 'Submit an image for three-stage forensic analysis', auth: 'Bearer API Key or JWT' },
  { method: 'GET', path: '/api/v1/analyze/{request_id}', desc: 'Retrieve a previous analysis result', auth: 'Bearer API Key or JWT' },
  { method: 'DELETE', path: '/api/v1/analyze/{request_id}', desc: 'Delete an analysis record and image', auth: 'Bearer API Key or JWT' },
  { method: 'GET', path: '/api/v1/usage/', desc: 'Get usage statistics (days, breakdown)', auth: 'Bearer JWT' },
  { method: 'GET', path: '/api/v1/usage/history', desc: 'Paginated analysis history', auth: 'Bearer JWT' },
  { method: 'POST', path: '/api/v1/api-keys/', desc: 'Create a new API key', auth: 'Bearer JWT' },
  { method: 'GET', path: '/api/v1/api-keys/', desc: 'List API keys for current user', auth: 'Bearer JWT' },
  { method: 'POST', path: '/api/v1/api-keys/{id}/revoke', desc: 'Revoke an API key', auth: 'Bearer JWT' },
  { method: 'GET', path: '/api/v1/health/', desc: 'System health and model status', auth: 'None' },
  { method: 'GET', path: '/docs', desc: 'Interactive OpenAPI documentation (FastAPI)', auth: 'None' },
];

const METHOD_COLORS: Record<string, string> = {
  GET: '#22c55e', POST: '#6366f1', DELETE: '#ef4444', PUT: '#f59e0b',
};

function CodeBlock({ code, lang }: { code: string; lang: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => { navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 2000); };
  return (
    <div className="code-block">
      <button className="copy-btn" onClick={copy}>{copied ? '✓ Copied' : 'Copy'}</button>
      <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{code}</pre>
    </div>
  );
}

export default function DocsPage() {
  const [activeTab, setActiveTab] = useState('Python');

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
      {/* Nav */}
      <nav className="nav">
        <Link to="/" className="nav-brand">
          <Cpu size={22} color="var(--primary)" />
          Deep<span className="logo-dot">Guard</span>
        </Link>
        <div className="nav-links">
          <Link to="/login" className="nav-link">Sign In</Link>
          <Link to="/signup" className="btn btn-primary btn-sm">Get Started</Link>
        </div>
      </nav>

      <div style={{ display: 'flex', maxWidth: 1200, margin: '0 auto', padding: '48px 24px', gap: 40 }}>
        {/* Sidebar TOC */}
        <aside style={{ width: 200, flexShrink: 0, position: 'sticky', top: 80, height: 'fit-content' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {['Overview', 'Authentication', 'Image Analysis', 'Response Format', 'Endpoints', 'Rate Limits', 'Privacy', 'Examples'].map(s => (
              <a key={s} href={`#${s.toLowerCase().replace(/\s+/g, '-')}`} className="sidebar-item" style={{ fontSize: '0.85rem' }}>{s}</a>
            ))}
          </div>
        </aside>

        {/* Main content */}
        <main style={{ flex: 1, maxWidth: 800 }}>
          <h1 style={{ fontSize: '2.5rem', fontWeight: 900, marginBottom: 12 }}>
            API <span className="gradient-text">Documentation</span>
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '1.05rem', marginBottom: 48, lineHeight: 1.7 }}>
            The DeepGuard API provides programmatic access to the three-stage forensic image analysis pipeline.
            Integrate deepfake detection into your own applications, workflows, or content moderation systems.
          </p>

          {/* Overview */}
          <section id="overview" style={{ marginBottom: 48 }}>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: 16 }}>Overview</h2>
            <div className="card" style={{ marginBottom: 16, borderColor: 'rgba(245,158,11,0.3)', background: 'rgba(245,158,11,0.05)' }}>
              <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <span style={{ fontSize: '1.2rem' }}>⚠️</span>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: 1.7 }}>
                  <strong style={{ color: 'var(--warning)' }}>Important Disclaimer:</strong> DeepGuard provides probabilistic forensic analysis.
                  Results are indicators, not definitive proof. No tool can guarantee whether an image is real or AI-generated.
                </p>
              </div>
            </div>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: 12 }}>
              <strong>Base URL:</strong> <code style={{ fontFamily: 'monospace', color: 'var(--primary)' }}>http://localhost:8000/api/v1</code>
            </p>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
              All responses use a consistent envelope: <code style={{ fontFamily: 'monospace', color: 'var(--primary)' }}>{'{"success": true, "data": {...}}'}</code>
            </p>
          </section>

          {/* Authentication */}
          <section id="authentication" style={{ marginBottom: 48 }}>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: 16 }}>Authentication</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 16, lineHeight: 1.7 }}>
              API keys use Bearer authentication. Create a key in your dashboard, then include it in the <code style={{ fontFamily: 'monospace', color: 'var(--primary)' }}>Authorization</code> header.
            </p>
            <CodeBlock code={`Authorization: Bearer dg_live_YOUR_API_KEY_HERE`} lang="http" />
            <div style={{ marginTop: 16, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <div className="badge badge-info">dg_live_… = Production key</div>
              <div className="badge badge-muted">dg_test_… = Development key</div>
            </div>
          </section>

          {/* Image Analysis */}
          <section id="image-analysis" style={{ marginBottom: 48 }}>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: 16 }}>Image Analysis</h2>
            <div style={{ marginBottom: 16 }}>
              <span style={{ fontFamily: 'monospace', fontWeight: 700, color: METHOD_COLORS.POST, marginRight: 8 }}>POST</span>
              <code style={{ fontFamily: 'monospace' }}>/api/v1/analyze/image</code>
            </div>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 16, lineHeight: 1.7 }}>
              Submit a JPEG, PNG, or WEBP image. Returns a full forensic report covering provenance, metadata, and ML ensemble stages.
            </p>

            {/* Code examples */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
              {TABS.map(tab => (
                <button
                  key={tab}
                  className={`btn ${activeTab === tab ? 'btn-primary' : 'btn-secondary'} btn-sm`}
                  onClick={() => setActiveTab(tab)}
                >
                  {tab}
                </button>
              ))}
            </div>
            <CodeBlock code={CODE[activeTab]} lang={activeTab.toLowerCase()} />
          </section>

          {/* Response */}
          <section id="response-format" style={{ marginBottom: 48 }}>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: 16 }}>Response Format</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 16, lineHeight: 1.7 }}>Example successful response:</p>
            <CodeBlock code={RESPONSE_EXAMPLE} lang="json" />
          </section>

          {/* Endpoints */}
          <section id="endpoints" style={{ marginBottom: 48 }}>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: 16 }}>All Endpoints</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {ENDPOINTS.map(ep => (
                <div key={ep.path} className="card" style={{ padding: '14px 18px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                    <span style={{ fontFamily: 'monospace', fontWeight: 700, color: METHOD_COLORS[ep.method], fontSize: '0.82rem', minWidth: 48 }}>{ep.method}</span>
                    <code style={{ fontFamily: 'monospace', fontSize: '0.88rem', color: 'var(--text-primary)', flex: 1 }}>{ep.path}</code>
                    <span className="badge badge-muted" style={{ fontSize: '0.72rem' }}>{ep.auth}</span>
                  </div>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginTop: 6 }}>{ep.desc}</p>
                </div>
              ))}
            </div>
            <p style={{ marginTop: 16, color: 'var(--text-muted)', fontSize: '0.88rem' }}>
              💡 Full interactive documentation: <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer" style={{ color: 'var(--primary)' }}>http://localhost:8000/docs</a>
            </p>
          </section>

          {/* Rate Limits */}
          <section id="rate-limits" style={{ marginBottom: 48 }}>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: 16 }}>Rate Limits</h2>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
              Rate limits are applied per API key. On exceeding limits, the API returns <code style={{ fontFamily: 'monospace', color: 'var(--danger)' }}>429 Too Many Requests</code>.
              Free plan: 100 requests/month per key. Limits are configurable per plan.
            </p>
          </section>

          {/* Privacy */}
          <section id="privacy" style={{ marginBottom: 48 }}>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: 16 }}>Privacy</h2>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: 12 }}>
              Each API key carries a privacy policy you select at creation time:
            </p>
            <ul style={{ color: 'var(--text-secondary)', lineHeight: 1.9, paddingLeft: 20 }}>
              <li><strong>Delete immediately</strong> — Images are deleted from all storage the moment analysis completes.</li>
              <li><strong>Retain 7/30/90 days</strong> — Images are stored temporarily under the configured period, then deleted.</li>
              <li><strong>Model improvement consent</strong> — Only explicitly opted-in images may be used for future model training. No silent data collection.</li>
            </ul>
          </section>
        </main>
      </div>
    </div>
  );
}
