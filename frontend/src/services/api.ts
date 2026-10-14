// API service — all backend calls go through here

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

function getToken(): string | null {
  return localStorage.getItem('dg_token');
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  extraHeaders?: Record<string, string>,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...authHeaders(),
    ...extraHeaders,
  };
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const json = await res.json();
  if (!res.ok) {
    const err = json?.error || json?.detail || { message: 'Request failed' };
    throw new APIError(err.message || JSON.stringify(err), err.code, res.status);
  }
  return json.data ?? json;
}

export class APIError extends Error {
  constructor(
    message: string,
    public code?: string,
    public status?: number,
  ) {
    super(message);
    this.name = 'APIError';
  }
}

// ── Auth ─────────────────────────────────────────────────────────────────────
export const authService = {
  async signup(data: { email: string; name: string; password: string; confirm_password: string; accept_terms: boolean }) {
    return request<{ user_id: string; message: string }>('POST', '/auth/signup', data);
  },
  async login(email: string, password: string) {
    const result = await request<{ access_token: string; user_id: string }>('POST', '/auth/login', { email, password });
    localStorage.setItem('dg_token', result.access_token);
    return result;
  },
  async logout() {
    localStorage.removeItem('dg_token');
  },
  async verifyOTP(email: string, otp: string, purpose = 'email_verification') {
    return request('POST', '/auth/verify-otp', { email, otp, purpose });
  },
  async resendOTP(email: string, purpose = 'email_verification') {
    return request('POST', '/auth/resend-otp', { email, purpose });
  },
  async getMe() {
    return request<any>('GET', '/auth/me');
  },
  isAuthenticated(): boolean {
    return !!getToken();
  },
};

// ── Analysis ─────────────────────────────────────────────────────────────────
export const analysisService = {
  async analyzeImage(file: File, onProgress?: (stage: string) => void): Promise<any> {
    const token = getToken();
    const formData = new FormData();
    formData.append('file', file);

    onProgress?.('Uploading image…');
    const res = await fetch(`${API_URL}/analyze/image`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    const json = await res.json();
    if (!res.ok) {
      const err = json?.error || json?.detail || { message: 'Analysis failed' };
      throw new APIError(err.message || JSON.stringify(err), err.code, res.status);
    }
    return json.data ?? json;
  },

  async getAnalysis(requestId: string) {
    return request<any>('GET', `/analyze/${requestId}`);
  },

  async deleteAnalysis(requestId: string) {
    return request('DELETE', `/analyze/${requestId}`);
  },
};

// ── API Keys ──────────────────────────────────────────────────────────────────
export const apiKeyService = {
  async createKey(data: {
    name: string;
    environment: string;
    retention: string;
    allow_model_improvement: boolean;
  }) {
    return request<any>('POST', '/api-keys/', data);
  },
  async listKeys() {
    return request<any[]>('GET', '/api-keys/');
  },
  async revokeKey(id: string) {
    return request('POST', `/api-keys/${id}/revoke`);
  },
  async deleteKey(id: string) {
    return request('DELETE', `/api-keys/${id}`);
  },
};

// ── Usage ─────────────────────────────────────────────────────────────────────
export const usageService = {
  async getUsage(days = 30) {
    return request<any>('GET', `/usage/?days=${days}`);
  },
  async getHistory(page = 1, limit = 20, filters?: Record<string, string>) {
    const params = new URLSearchParams({ page: String(page), limit: String(limit), ...filters });
    return request<any>('GET', `/usage/history?${params}`);
  },
};

// ── Health ────────────────────────────────────────────────────────────────────
export const healthService = {
  async check() {
    return request<any>('GET', '/health/');
  },
};

// ── Users ─────────────────────────────────────────────────────────────────────
export const userService = {
  async getStats() {
    return request<any>('GET', '/users/me/stats');
  },
};
