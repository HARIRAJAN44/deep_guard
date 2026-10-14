import { Link } from 'react-router-dom';
import { Cpu, Home } from 'lucide-react';

export default function NotFoundPage() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-base)', textAlign: 'center', padding: 24 }}>
      <div>
        <div style={{ fontSize: '6rem', fontWeight: 900, background: 'linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', marginBottom: 8 }}>404</div>
        <h1 style={{ fontSize: '1.8rem', fontWeight: 800, marginBottom: 12 }}>Page Not Found</h1>
        <p style={{ color: 'var(--text-secondary)', marginBottom: 32, maxWidth: 400 }}>
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
          <Link to="/" className="btn btn-primary">
            <Home size={16} /> Back to Home
          </Link>
          <Link to="/dashboard" className="btn btn-secondary">Go to Dashboard</Link>
        </div>
      </div>
    </div>
  );
}
