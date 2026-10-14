import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Cpu, Loader2, RefreshCw, CheckCircle2 } from 'lucide-react';
import { authService, APIError } from '../services/api';
import { useToast } from '../contexts/ToastContext';

export default function OTPPage() {
  const [params] = useSearchParams();
  const email = params.get('email') || '';
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [verified, setVerified] = useState(false);
  const inputs = useRef<(HTMLInputElement | null)[]>([]);
  const { toast } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    if (cooldown > 0) {
      const t = setTimeout(() => setCooldown(c => c - 1), 1000);
      return () => clearTimeout(t);
    }
  }, [cooldown]);

  const handleChange = (idx: number, val: string) => {
    if (!/^\d*$/.test(val)) return;
    const next = [...otp];
    next[idx] = val.slice(-1);
    setOtp(next);
    if (val && idx < 5) inputs.current[idx + 1]?.focus();
  };

  const handleKeyDown = (idx: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !otp[idx] && idx > 0) {
      inputs.current[idx - 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (pasted.length === 6) {
      setOtp(pasted.split(''));
      inputs.current[5]?.focus();
    }
  };

  const handleVerify = async () => {
    const code = otp.join('');
    if (code.length !== 6) { toast('Enter all 6 digits', 'warning'); return; }
    setLoading(true);
    try {
      await authService.verifyOTP(email, code);
      setVerified(true);
      toast('Email verified! Redirecting to login…', 'success');
      setTimeout(() => navigate('/login'), 2000);
    } catch (err) {
      toast(err instanceof APIError ? err.message : 'Verification failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setResending(true);
    try {
      await authService.resendOTP(email);
      toast('New OTP sent (check console in dev mode)', 'success');
      setCooldown(60);
    } catch (err) {
      toast(err instanceof APIError ? err.message : 'Resend failed', 'error');
    } finally {
      setResending(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px', background: 'radial-gradient(ellipse at top, rgba(99,102,241,0.08) 0%, var(--bg-base) 60%)' }}>
      <div style={{ width: '100%', maxWidth: 420 }}>
        <Link to="/" className="nav-brand" style={{ justifyContent: 'center', marginBottom: 40, display: 'flex' }}>
          <Cpu size={24} color="var(--primary)" />
          Deep<span className="logo-dot">Guard</span>
        </Link>

        <div className="card card-elevated animate-fade-in text-center">
          {verified ? (
            <>
              <CheckCircle2 size={64} color="var(--success)" style={{ margin: '0 auto 20px' }} />
              <h2 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: 10 }}>Email Verified!</h2>
              <p style={{ color: 'var(--text-muted)' }}>Redirecting to login…</p>
            </>
          ) : (
            <>
              <div style={{ fontSize: '2.5rem', marginBottom: 16 }}>📬</div>
              <h1 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: 8 }}>Check your email</h1>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: 6 }}>
                We sent a 6-digit code to
              </p>
              <p style={{ color: 'var(--text-primary)', fontWeight: 700, marginBottom: 8 }}>{email}</p>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.78rem', marginBottom: 28 }}>
                In development mode, the OTP is printed in the backend console.
              </p>

              <div className="otp-container" onPaste={handlePaste}>
                {otp.map((digit, i) => (
                  <input
                    key={i}
                    ref={el => { inputs.current[i] = el; }}
                    className="otp-input"
                    type="text"
                    inputMode="numeric"
                    maxLength={1}
                    value={digit}
                    onChange={e => handleChange(i, e.target.value)}
                    onKeyDown={e => handleKeyDown(i, e)}
                    aria-label={`OTP digit ${i + 1}`}
                  />
                ))}
              </div>

              <button className="btn btn-primary w-full" style={{ marginTop: 24 }} onClick={handleVerify} disabled={loading}>
                {loading ? <Loader2 size={18} className="animate-spin" /> : null}
                {loading ? 'Verifying…' : 'Verify Email'}
              </button>

              <button
                className="btn btn-ghost w-full"
                style={{ marginTop: 12 }}
                onClick={handleResend}
                disabled={resending || cooldown > 0}
              >
                <RefreshCw size={15} />
                {cooldown > 0 ? `Resend in ${cooldown}s` : resending ? 'Sending…' : 'Resend OTP'}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
