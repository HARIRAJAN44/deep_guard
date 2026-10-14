import { useNavigate, Link } from 'react-router-dom';
import { Shield, ArrowRight, Cpu, Eye, Database, Zap, Lock, CheckCircle, ChevronRight } from 'lucide-react';

const PIPELINE_STEPS = [
  { icon: '🖼️', label: 'Image Upload', desc: 'Secure, validated upload' },
  { icon: '🔍', label: 'Provenance Check', desc: 'AI signature detection' },
  { icon: '📋', label: 'EXIF Forensics', desc: 'Metadata analysis' },
  { icon: '🤖', label: 'ML Ensemble', desc: '5 pattern analyzers' },
  { icon: '⚖️', label: 'Evidence Fusion', desc: 'Weighted assessment' },
  { icon: '📊', label: 'Forensic Report', desc: 'Probabilistic verdict' },
];

const FEATURES = [
  { icon: Shield, title: 'Three-Stage Pipeline', desc: 'Provenance signals, EXIF metadata forensics, and 5-model ML ensemble combined through evidence fusion.' },
  { icon: Eye, title: 'Transparent Results', desc: 'Every assessment explains why. We show individual stage results and overall confidence honestly.' },
  { icon: Lock, title: 'Privacy-First', desc: 'Choose your data retention policy. Images can be deleted immediately after analysis.' },
  { icon: Zap, title: 'Developer API', desc: 'RESTful API with API keys, rate limiting, usage tracking, and full OpenAPI documentation.' },
  { icon: Database, title: 'Evidence Not Proof', desc: 'DeepGuard provides probabilistic forensic indicators — not absolute verdicts.' },
  { icon: Cpu, title: '5 ML Models', desc: 'Ensemble of trained pattern analyzers. Results are model scores, not calibrated certainties.' },
];

const USE_CASES = [
  { emoji: '📰', title: 'News Publishers', desc: 'Verify images before publication' },
  { emoji: '📱', title: 'Social Platforms', desc: 'Content moderation at scale via API' },
  { emoji: '🔬', title: 'Researchers', desc: 'Forensic analysis tooling' },
  { emoji: '🏢', title: 'Enterprises', desc: 'Integrate into existing workflows' },
  { emoji: '👨‍💻', title: 'Developers', desc: 'Build on the DeepGuard API' },
  { emoji: '🧑‍⚖️', title: 'Journalists', desc: 'Due diligence on visual content' },
];

const FAQ = [
  { q: 'Is DeepGuard 100% accurate?', a: 'No. DeepGuard provides probabilistic forensic indicators. No single tool can guarantee whether an image is real or fake. Results should be treated as evidence, not proof.' },
  { q: 'What happens to my uploaded images?', a: 'You control retention. Images can be deleted immediately after analysis, retained temporarily, or under a custom policy you select per API key.' },
  { q: 'What do the ML models actually detect?', a: 'The five models are binary classifiers trained on a real/fake face image dataset. They output pattern-level scores that contribute to the overall assessment — they are not specialized domain algorithms.' },
  { q: 'Can I use this as a developer?', a: 'Yes. Create an account, generate an API key, and POST images to /api/v1/analyze/image. Full documentation is available on the Docs page.' },
];

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
      {/* Nav */}
      <nav className="nav">
        <div className="nav-brand">
          <Cpu size={22} color="var(--primary)" />
          Deep<span className="logo-dot">Guard</span>
        </div>
        <div className="nav-links">
          <a href="#how-it-works" className="nav-link">How It Works</a>
          <Link to="/docs" className="nav-link">API</Link>
          <Link to="/login" className="nav-link">Sign In</Link>
          <button className="btn btn-primary btn-sm" onClick={() => navigate('/signup')}>
            Get Started
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="hero-section">
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, background: 'var(--primary-light)', border: '1px solid rgba(99,102,241,0.2)', borderRadius: 'var(--radius-pill)', padding: '6px 16px', fontSize: '0.8rem', fontWeight: 600, color: 'var(--primary)', marginBottom: 32 }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--primary)', animation: 'pulse 2s infinite' }} />
          Multi-Stage Forensic Analysis
        </div>
        <h1 className="hero-title">
          Detect Deepfakes<br />
          <span className="gradient-text">Before They Spread.</span>
        </h1>
        <p className="hero-subtitle">
          Multi-stage image forensics combining provenance signals, metadata analysis,
          and AI-powered visual detection. Probabilistic results, total transparency.
        </p>
        <div style={{ display: 'flex', gap: 16, justifyContent: 'center', flexWrap: 'wrap' }}>
          <button className="btn btn-primary btn-lg" onClick={() => navigate('/signup')}>
            Analyze an Image <ArrowRight size={18} />
          </button>
          <Link to="/docs" className="btn btn-secondary btn-lg">
            Explore API <ChevronRight size={18} />
          </Link>
        </div>
        <p style={{ marginTop: 24, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          ⚠️ DeepGuard provides probabilistic forensic analysis — results are not definitive proof.
        </p>
      </section>

      {/* Pipeline visualization */}
      <section id="how-it-works" style={{ padding: '80px 0' }}>
        <div className="container">
          <div className="text-center" style={{ marginBottom: 48 }}>
            <h2 style={{ fontSize: '2rem', fontWeight: 800, marginBottom: 12 }}>Three-Stage Analysis Pipeline</h2>
            <p style={{ color: 'var(--text-secondary)', maxWidth: 560, margin: '0 auto' }}>
              Every image passes through three independent forensic stages before a final
              evidence-weighted assessment is produced.
            </p>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 16 }}>
            {PIPELINE_STEPS.map((step, i) => (
              <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', position: 'relative' }}>
                {i < PIPELINE_STEPS.length - 1 && (
                  <ChevronRight size={16} style={{ position: 'absolute', right: -8, top: 20, color: 'var(--text-muted)', zIndex: 1 }} />
                )}
                <div style={{ width: 64, height: 64, borderRadius: 'var(--radius-md)', background: 'var(--bg-card)', border: '1px solid var(--bg-border)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.8rem', marginBottom: 12 }}>
                  {step.icon}
                </div>
                <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: 4 }}>{step.label}</div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{step.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section style={{ padding: '80px 0', background: 'var(--bg-surface)' }}>
        <div className="container">
          <div className="text-center" style={{ marginBottom: 48 }}>
            <h2 style={{ fontSize: '2rem', fontWeight: 800, marginBottom: 12 }}>Why DeepGuard?</h2>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 20 }}>
            {FEATURES.map((f, i) => (
              <div key={i} className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ width: 44, height: 44, borderRadius: 'var(--radius-sm)', background: 'var(--primary-light)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <f.icon size={20} color="var(--primary)" />
                </div>
                <h3 style={{ fontWeight: 700, fontSize: '1rem' }}>{f.title}</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', lineHeight: 1.7 }}>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Use cases */}
      <section style={{ padding: '80px 0' }}>
        <div className="container">
          <div className="text-center" style={{ marginBottom: 48 }}>
            <h2 style={{ fontSize: '2rem', fontWeight: 800, marginBottom: 12 }}>Who Uses DeepGuard?</h2>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 16 }}>
            {USE_CASES.map((uc, i) => (
              <div key={i} className="card text-center" style={{ padding: 24 }}>
                <div style={{ fontSize: '2rem', marginBottom: 12 }}>{uc.emoji}</div>
                <div style={{ fontWeight: 700, marginBottom: 6 }}>{uc.title}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{uc.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section style={{ padding: '80px 0', background: 'var(--bg-surface)' }}>
        <div className="container-sm">
          <div className="text-center" style={{ marginBottom: 48 }}>
            <h2 style={{ fontSize: '2rem', fontWeight: 800, marginBottom: 12 }}>Frequently Asked Questions</h2>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {FAQ.map((item, i) => (
              <div key={i} className="card">
                <div style={{ fontWeight: 700, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 10 }}>
                  <CheckCircle size={16} color="var(--primary)" style={{ flexShrink: 0 }} />
                  {item.q}
                </div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: 1.7, paddingLeft: 26 }}>{item.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section style={{ padding: '100px 24px', textAlign: 'center', background: 'linear-gradient(180deg, var(--bg-base) 0%, rgba(99,102,241,0.06) 100%)' }}>
        <h2 style={{ fontSize: '2.5rem', fontWeight: 900, marginBottom: 20 }}>
          Start Analyzing Images <span className="gradient-text">Today</span>
        </h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: 36, maxWidth: 480, margin: '0 auto 36px' }}>
          Free account. No credit card required. API access included.
        </p>
        <div style={{ display: 'flex', gap: 16, justifyContent: 'center', flexWrap: 'wrap' }}>
          <button className="btn btn-primary btn-lg" onClick={() => navigate('/signup')}>
            Create Free Account <ArrowRight size={18} />
          </button>
          <Link to="/docs" className="btn btn-secondary btn-lg">View API Docs</Link>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ borderTop: '1px solid var(--bg-border)', padding: '32px 24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginBottom: 12 }}>
          <Cpu size={16} color="var(--primary)" />
          <strong style={{ color: 'var(--text-secondary)' }}>DeepGuard</strong>
        </div>
        <p>AI-Powered Deepfake Identification & Media Provenance</p>
        <p style={{ marginTop: 8 }}>
          DeepGuard provides probabilistic forensic analysis. Results should not be treated as
          definitive proof of authenticity or manipulation.
        </p>
      </footer>
    </div>
  );
}
