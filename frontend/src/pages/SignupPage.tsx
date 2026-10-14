import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Cpu, Eye, EyeOff, Loader2, CheckCircle } from 'lucide-react';
import { authService, APIError } from '../services/api';
import { useToast } from '../contexts/ToastContext';

export default function SignupPage() {
  const [form, setForm] = useState({ name: '', email: '', password: '', confirm_password: '', accept_terms: false });
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const { toast } = useToast();
  const navigate = useNavigate();

  const validate = () => {
    const e: Record<string, string> = {};
    if (!form.name.trim() || form.name.length < 2) e.name = 'Name must be at least 2 characters';
    if (!form.email) e.email = 'Email is required';
    if (form.password.length < 8) e.password = 'Password must be at least 8 characters';
    if (form.password !== form.confirm_password) e.confirm_password = 'Passwords do not match';
    if (!form.accept_terms) e.accept_terms = 'You must accept the terms of service';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setLoading(true);
    try {
      await authService.signup(form);
      toast('Account created! Check your email (or console in dev mode) for your OTP.', 'success');
      navigate(`/verify-otp?email=${encodeURIComponent(form.email)}`);
    } catch (err) {
      toast(err instanceof APIError ? err.message : 'Signup failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const field = (key: keyof typeof form) => ({
    value: form[key] as string,
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, [key]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })),
  });

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px', background: 'radial-gradient(ellipse at top, rgba(99,102,241,0.08) 0%, var(--bg-base) 60%)' }}>
      <div style={{ width: '100%', maxWidth: 460 }}>
        <Link to="/" className="nav-brand" style={{ justifyContent: 'center', marginBottom: 40, display: 'flex' }}>
          <Cpu size={24} color="var(--primary)" />
          Deep<span className="logo-dot">Guard</span>
        </Link>

        <div className="card card-elevated animate-fade-in">
          <h1 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: 6 }}>Create your account</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: 28 }}>Free. No credit card required.</p>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div className="input-group">
              <label className="input-label">Full name</label>
              <input id="name" type="text" className={`input${errors.name ? ' input-error' : ''}`} placeholder="Jane Smith" {...field('name')} />
              {errors.name && <span className="error-msg">{errors.name}</span>}
            </div>

            <div className="input-group">
              <label className="input-label">Email address</label>
              <input id="email" type="email" className={`input${errors.email ? ' input-error' : ''}`} placeholder="you@example.com" {...field('email')} />
              {errors.email && <span className="error-msg">{errors.email}</span>}
            </div>

            <div className="input-group">
              <label className="input-label">Password</label>
              <div style={{ position: 'relative' }}>
                <input id="password" type={showPw ? 'text' : 'password'} className={`input${errors.password ? ' input-error' : ''}`} placeholder="At least 8 characters" {...field('password')} style={{ paddingRight: 44 }} />
                <button type="button" onClick={() => setShowPw(!showPw)} style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 4 }}>
                  {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {errors.password && <span className="error-msg">{errors.password}</span>}
            </div>

            <div className="input-group">
              <label className="input-label">Confirm password</label>
              <input id="confirm_password" type="password" className={`input${errors.confirm_password ? ' input-error' : ''}`} placeholder="Repeat password" {...field('confirm_password')} />
              {errors.confirm_password && <span className="error-msg">{errors.confirm_password}</span>}
            </div>

            <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, cursor: 'pointer', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              <input type="checkbox" id="accept_terms" checked={form.accept_terms} onChange={e => setForm(f => ({ ...f, accept_terms: e.target.checked }))} style={{ marginTop: 2, accentColor: 'var(--primary)' }} />
              I agree to the Terms of Service and Privacy Policy. I understand DeepGuard provides probabilistic analysis, not definitive results.
            </label>
            {errors.accept_terms && <span className="error-msg">{errors.accept_terms}</span>}

            <button type="submit" className="btn btn-primary w-full" disabled={loading} style={{ marginTop: 4 }}>
              {loading ? <Loader2 size={18} className="animate-spin" /> : null}
              {loading ? 'Creating account…' : 'Create Account'}
            </button>
          </form>

          <p style={{ textAlign: 'center', fontSize: '0.9rem', color: 'var(--text-secondary)', marginTop: 24 }}>
            Already have an account?{' '}
            <Link to="/login" style={{ color: 'var(--primary)', fontWeight: 600 }}>Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
