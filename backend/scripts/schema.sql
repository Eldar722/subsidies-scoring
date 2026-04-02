-- ============================================================
-- Supabase Schema for Subsidies Scoring
-- Run this once in Supabase SQL Editor:
-- https://supabase.com/dashboard/project/wzmrsxnxzldzmlbkvdpi/sql
-- ============================================================

-- 1. Producers
CREATE TABLE IF NOT EXISTS producers (
  producer_id TEXT PRIMARY KEY,
  region TEXT,
  direction TEXT,
  total_applications INT DEFAULT 0,
  completion_rate FLOAT DEFAULT 0
);

-- 2. ML Scores
CREATE TABLE IF NOT EXISTS scores (
  producer_id TEXT PRIMARY KEY,
  ml_score FLOAT,
  ml_rank INT,
  fcfs_rank INT,
  delta INT,
  hidden_talent BOOLEAN DEFAULT FALSE,
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 3. SHAP Values (top-N per producer)
CREATE TABLE IF NOT EXISTS shap_values (
  id BIGSERIAL PRIMARY KEY,
  producer_id TEXT,
  feature TEXT,
  shap_value FLOAT,
  feature_value FLOAT,
  feature_label TEXT
);
CREATE INDEX IF NOT EXISTS idx_shap_producer ON shap_values(producer_id);

-- 4. Model Metrics
CREATE TABLE IF NOT EXISTS model_metrics (
  run_id TEXT PRIMARY KEY,
  roc_auc FLOAT,
  avg_precision FLOAT,
  best_f1 FLOAT,
  optimal_threshold FLOAT,
  cv_auc_mean FLOAT,
  train_size INT,
  val_size INT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 5. Fairness Cache
CREATE TABLE IF NOT EXISTS fairness_cache (
  id TEXT PRIMARY KEY,
  data JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 6. Gemini Advice Cache
CREATE TABLE IF NOT EXISTS gemini_advice (
  producer_id TEXT PRIMARY KEY,
  advice JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for common filters
CREATE INDEX IF NOT EXISTS idx_scores_ml_score ON scores(ml_score DESC);
CREATE INDEX IF NOT EXISTS idx_scores_hidden ON scores(hidden_talent) WHERE hidden_talent = TRUE;
CREATE INDEX IF NOT EXISTS idx_producers_region ON producers(region);
CREATE INDEX IF NOT EXISTS idx_producers_direction ON producers(direction);
