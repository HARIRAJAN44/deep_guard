// TypeScript types for DeepGuard

export interface User {
  id: string;
  email: string;
  name: string;
  email_verified: boolean;
  plan: string;
  created_at: string;
  last_login_at?: string;
}

export interface PrivacyPolicy {
  retention: 'delete_immediately' | 'retain_7d' | 'retain_30d' | 'retain_90d';
  allow_model_improvement: boolean;
  policy_version: string;
  consented_at: string;
}

export interface APIKey {
  id: string;
  name: string;
  environment: 'development' | 'production';
  prefix: string;
  status: 'active' | 'revoked';
  privacy_policy: PrivacyPolicy;
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  created_at: string;
  last_used_at?: string;
  full_key?: string; // only present immediately after creation
}

export interface ModelScore {
  label: 'likely_real' | 'likely_fake' | 'inconclusive' | 'error' | 'unavailable';
  score: number;
  status: 'success' | 'error' | 'unavailable';
}

export interface EnsembleResult {
  models: Record<string, ModelScore>;
  ensemble_label: string;
  ensemble_score: number;
  models_run: number;
  models_available: number;
  explanation: string;
}

export interface ProvenanceResult {
  status: 'indicator_found' | 'no_indicator_found' | 'error';
  provider?: string;
  indicator_type?: string;
  confidence: number;
  explanation: string;
  details?: Record<string, any>;
}

export interface MetadataResult {
  has_exif: boolean;
  camera_make?: string;
  camera_model?: string;
  software?: string;
  capture_timestamp?: string;
  gps_present: boolean;
  editing_software?: string;
  metadata_integrity: 'consistent' | 'inconsistent' | 'partial' | 'missing' | 'unknown';
  explanation: string;
  raw_fields?: Record<string, string>;
}

export type Assessment =
  | 'likely_authentic'
  | 'likely_ai_generated'
  | 'likely_manipulated'
  | 'suspicious'
  | 'inconclusive';

export interface AnalysisResult {
  request_id: string;
  status: string;
  assessment: Assessment;
  assessment_confidence: number;
  assessment_explanation: string;
  assessment_reasons: string[];
  stages: {
    provenance?: ProvenanceResult;
    metadata?: MetadataResult;
    ensemble?: EnsembleResult;
  };
  model_version: string;
  processing_time_ms: number;
  created_at: string;
}

export interface UsageStats {
  period_days: number;
  total_requests: number;
  successful: number;
  failed: number;
  by_assessment: Record<Assessment, number>;
  daily_series: Array<{ date: string; count: number }>;
}

export interface HistoryItem {
  id: string;
  request_id: string;
  assessment: Assessment;
  assessment_confidence: number;
  processing_time_ms: number;
  created_at: string;
  original_filename?: string;
  api_key_id?: string;
}

export const ASSESSMENT_LABELS: Record<Assessment, string> = {
  likely_authentic: 'Likely Authentic',
  likely_ai_generated: 'Likely AI-Generated',
  likely_manipulated: 'Likely Manipulated',
  suspicious: 'Suspicious',
  inconclusive: 'Inconclusive',
};

export const ASSESSMENT_COLORS: Record<Assessment, string> = {
  likely_authentic: '#22c55e',
  likely_ai_generated: '#ef4444',
  likely_manipulated: '#f97316',
  suspicious: '#f59e0b',
  inconclusive: '#64748b',
};

export const MODEL_DISPLAY_NAMES: Record<string, string> = {
  color_pattern: 'Color-Pattern Analyzer',
  facial_pattern: 'Facial-Pattern Analyzer',
  texture_pattern: 'Texture-Pattern Analyzer',
  temporal_feature: 'Temporal-Feature Analyzer',
  artifact_pattern: 'Artifact-Pattern Analyzer',
};
