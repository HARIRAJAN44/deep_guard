import { useEffect, useState } from 'react';
import { Key, Plus, Trash2, X, Copy, Check, Shield, AlertTriangle, Loader2 } from 'lucide-react';
import { apiKeyService, APIError } from '../services/api';
import { useToast } from '../contexts/ToastContext';
import type { APIKey } from '../types';

function CreateKeyModal({ onClose, onCreate }: { onClose: () => void; onCreate: (key: APIKey) => void }) {
  const [form, setForm] = useState({
    name: '',
    environment: 'development',
    retention: 'delete_immediately',
    allow_model_improvement: false,
  });
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) { toast('Key name is required', 'warning'); return; }
    setLoading(true);
    try {
      const key = await apiKeyService.createKey(form);
      onCreate(key);
    } catch (err) {
      toast(err instanceof APIError ? err.message : 'Failed to create API key', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-label="Create API key">
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
          <h2 style={{ fontWeight: 800, fontSize: '1.2rem' }}>Create API Key</h2>
          <button className="btn btn-ghost btn-icon" onClick={onClose} aria-label="Close modal"><X size={18} /></button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="input-group">
            <label className="input-label">Key name</label>
            <input className="input" placeholder="e.g. News Website Production" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required />
          </div>

          <div className="input-group">
            <label className="input-label">Environment</label>
            <select className="input" value={form.environment} onChange={e => setForm(f => ({ ...f, environment: e.target.value }))}>
              <option value="development">Development (dg_test_…)</option>
              <option value="production">Production (dg_live_…)</option>
            </select>
          </div>

          <div className="input-group">
            <label className="input-label">Image retention policy</label>
            <select className="input" value={form.retention} onChange={e => setForm(f => ({ ...f, retention: e.target.value }))}>
              <option value="delete_immediately">Delete immediately after analysis</option>
              <option value="retain_7d">Retain for 7 days</option>
              <option value="retain_30d">Retain for 30 days</option>
              <option value="retain_90d">Retain for 90 days</option>
            </select>
          </div>

          <div style={{ padding: '14px 16px', background: 'var(--bg-surface)', border: '1px solid var(--bg-border)', borderRadius: 'var(--radius-sm)' }}>
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, cursor: 'pointer', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              <input
                type="checkbox"
                checked={form.allow_model_improvement}
                onChange={e => setForm(f => ({ ...f, allow_model_improvement: e.target.checked }))}
                style={{ marginTop: 2, accentColor: 'var(--primary)' }}
                aria-label="Allow model improvement"
              />
              <div>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>Allow model improvement</div>
                I explicitly consent to DeepGuard using eligible images submitted via this key to improve AI models. Images will never be used without this explicit opt-in.
              </div>
            </label>
          </div>

          <button type="submit" className="btn btn-primary w-full" disabled={loading} style={{ marginTop: 4 }}>
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Key size={16} />}
            {loading ? 'Creating…' : 'Create API Key'}
          </button>
        </form>
      </div>
    </div>
  );
}

function KeyRevealModal({ fullKey, onClose }: { fullKey: string; onClose: () => void }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(fullKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="New API key">
      <div className="modal-box">
        <div style={{ textAlign: 'center', marginBottom: 20 }}>
          <div style={{ fontSize: '2.5rem', marginBottom: 8 }}>🔑</div>
          <h2 style={{ fontWeight: 800, marginBottom: 8 }}>Your New API Key</h2>
          <p style={{ color: 'var(--danger)', fontWeight: 600, fontSize: '0.88rem', marginBottom: 4 }}>⚠️ This key will only be shown once. Copy it now.</p>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>Store it securely. You cannot recover the full key later.</p>
        </div>
        <div className="api-key-reveal">{fullKey}</div>
        <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
          <button className="btn btn-primary w-full" onClick={copy}>
            {copied ? <Check size={16} /> : <Copy size={16} />}
            {copied ? 'Copied!' : 'Copy Key'}
          </button>
          <button className="btn btn-secondary" onClick={onClose}>Done</button>
        </div>
      </div>
    </div>
  );
}

export default function APIKeysPage() {
  const [keys, setKeys] = useState<APIKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newKey, setNewKey] = useState<string | null>(null);
  const { toast } = useToast();

  const loadKeys = () => {
    setLoading(true);
    apiKeyService.listKeys()
      .then(setKeys)
      .catch(err => toast(err instanceof APIError ? err.message : 'Failed to load keys', 'error'))
      .finally(() => setLoading(false));
  };

  useEffect(loadKeys, []);

  const handleCreate = (key: APIKey) => {
    setShowCreate(false);
    if (key.full_key) setNewKey(key.full_key);
    setKeys(prev => [{ ...key, full_key: undefined }, ...prev]);
    toast('API key created!', 'success');
  };

  const handleRevoke = async (id: string, name: string) => {
    if (!confirm(`Revoke key "${name}"? This cannot be undone.`)) return;
    try {
      await apiKeyService.revokeKey(id);
      setKeys(prev => prev.map(k => k.id === id ? { ...k, status: 'revoked' as const } : k));
      toast('API key revoked', 'success');
    } catch (err) {
      toast(err instanceof APIError ? err.message : 'Revoke failed', 'error');
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this API key permanently?')) return;
    try {
      await apiKeyService.deleteKey(id);
      setKeys(prev => prev.filter(k => k.id !== id));
      toast('API key deleted', 'success');
    } catch (err) {
      toast(err instanceof APIError ? err.message : 'Delete failed', 'error');
    }
  };

  return (
    <div className="animate-fade-in">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 28, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: '1.8rem', fontWeight: 800, marginBottom: 4 }}>API Keys</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Manage API access. Each key has its own privacy policy.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          <Plus size={16} /> Create API Key
        </button>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>Loading…</div>
      ) : keys.length === 0 ? (
        <div className="card text-center" style={{ padding: 60 }}>
          <Key size={48} color="var(--text-muted)" style={{ margin: '0 auto 16px' }} />
          <h3 style={{ fontWeight: 700, marginBottom: 8 }}>No API keys yet</h3>
          <p style={{ color: 'var(--text-muted)', marginBottom: 24 }}>Create an API key to integrate DeepGuard into your application.</p>
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
            <Plus size={16} /> Create First Key
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {keys.map(key => (
            <div key={key.id} className="card" style={{ opacity: key.status === 'revoked' ? 0.6 : 1 }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                    <Key size={16} color="var(--primary)" />
                    <span style={{ fontWeight: 700 }}>{key.name}</span>
                    <span className={`badge ${key.status === 'active' ? 'badge-success' : 'badge-danger'}`}>{key.status}</span>
                    <span className="badge badge-muted">{key.environment}</span>
                  </div>
                  <div style={{ fontFamily: 'monospace', fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: 12 }}>
                    {key.prefix}{'•'.repeat(20)}
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    <span>📊 {key.total_requests} requests</span>
                    <span>✅ {key.successful_requests} success</span>
                    <span>❌ {key.failed_requests} failed</span>
                    <span>🗑️ Retention: {key.privacy_policy.retention.replace(/_/g, ' ')}</span>
                    <span>🔬 Model improvement: {key.privacy_policy.allow_model_improvement ? 'Opted in' : 'Not consented'}</span>
                    {key.last_used_at && <span>🕒 Last used: {new Date(key.last_used_at).toLocaleDateString()}</span>}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  {key.status === 'active' && (
                    <button className="btn btn-secondary btn-sm" onClick={() => handleRevoke(key.id, key.name)}>
                      <Shield size={14} /> Revoke
                    </button>
                  )}
                  <button className="btn btn-danger btn-sm" onClick={() => handleDelete(key.id)}>
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreate && <CreateKeyModal onClose={() => setShowCreate(false)} onCreate={handleCreate} />}
      {newKey && <KeyRevealModal fullKey={newKey} onClose={() => setNewKey(null)} />}
    </div>
  );
}
