-- ══════════════════════════════════════════════════════════════════════════════
-- Migration 002: Stabilize Schema + SHAP Staging Table
-- 
-- Principles:
--   - Fully idempotent (safe to re-run)
--   - IF NOT EXISTS everywhere
--   - ON CONFLICT DO UPDATE instead of destructive delete→insert
--   - Staging table for atomic SHAP operations
--
-- Usage:
--   python backend/scripts/migrate.py
--   OR: python backend/scripts/run_supabase_sql.py docs/supabase_migrations/002_stabilize_schema.sql
-- ══════════════════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────
-- 1. CORE TABLES (idempotent — IF NOT EXISTS)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS producers (
    producer_id TEXT PRIMARY KEY,
    region TEXT,
    direction TEXT,
    total_applications INT DEFAULT 0,
    completion_rate FLOAT DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS scores (
    producer_id TEXT PRIMARY KEY,
    ml_score FLOAT,
    ml_rank INT,
    fcfs_rank INT,
    delta INT,
    hidden_talent BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS shap_values (
    id BIGSERIAL PRIMARY KEY,
    producer_id TEXT NOT NULL,
    feature TEXT NOT NULL,
    shap_value FLOAT,
    feature_value FLOAT,
    feature_label TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
);

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

CREATE TABLE IF NOT EXISTS fairness_cache (
    id TEXT PRIMARY KEY,
    data JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS gemini_advice (
    producer_id TEXT PRIMARY KEY,
    advice_json JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ─────────────────────────────────────────────────────────────
-- 2. SHAP STAGING TABLE (for atomic swap operations)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS shap_values_staging (
    id BIGSERIAL PRIMARY KEY,
    producer_id TEXT NOT NULL,
    feature TEXT NOT NULL,
    shap_value FLOAT,
    feature_value FLOAT,
    feature_label TEXT
);

-- ─────────────────────────────────────────────────────────────
-- 3. UNIQUE CONSTRAINTS (idempotent — IF NOT EXISTS on index)
-- ─────────────────────────────────────────────────────────────

-- SHAP unique constraint: ensures upsert ON CONFLICT works
-- First, clean up any NULL/empty producer_id or feature
DELETE FROM shap_values
WHERE producer_id IS NULL
   OR feature IS NULL
   OR trim(producer_id) = ''
   OR trim(feature) = '';

-- Deduplicate: keep highest id for each (producer_id, feature)
DELETE FROM shap_values a
USING shap_values b
WHERE a.producer_id = b.producer_id
  AND a.feature = b.feature
  AND a.id < b.id;

-- Now safe to create the unique index
CREATE UNIQUE INDEX IF NOT EXISTS shap_values_producer_feature_key
    ON shap_values (producer_id, feature);

-- Staging table also gets the unique index for upsert support
CREATE UNIQUE INDEX IF NOT EXISTS shap_staging_producer_feature_key
    ON shap_values_staging (producer_id, feature);

-- ─────────────────────────────────────────────────────────────
-- 4. ADD updated_at WHERE MISSING (idempotent via DO $$ block)
-- ─────────────────────────────────────────────────────────────

DO $$
BEGIN
    -- producers
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'producers' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE producers ADD COLUMN updated_at TIMESTAMPTZ DEFAULT now();
    END IF;

    -- scores
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'scores' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE scores ADD COLUMN updated_at TIMESTAMPTZ DEFAULT now();
    END IF;

    -- shap_values
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'shap_values' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE shap_values ADD COLUMN updated_at TIMESTAMPTZ DEFAULT now();
    END IF;
END $$;

-- ─────────────────────────────────────────────────────────────
-- 5. PERFORMANCE INDEXES
-- ─────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_shap_producer ON shap_values(producer_id);
CREATE INDEX IF NOT EXISTS idx_scores_ml_score ON scores(ml_score DESC);
CREATE INDEX IF NOT EXISTS idx_scores_hidden ON scores(hidden_talent) WHERE hidden_talent = TRUE;
CREATE INDEX IF NOT EXISTS idx_producers_region ON producers(region);
CREATE INDEX IF NOT EXISTS idx_producers_direction ON producers(direction);

-- ─────────────────────────────────────────────────────────────
-- 6. gemini_advice: ensure advice_json column exists
-- ─────────────────────────────────────────────────────────────

DO $$
BEGIN
    -- Rename legacy 'advice' → 'advice_json' if needed
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'gemini_advice' AND column_name = 'advice'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'gemini_advice' AND column_name = 'advice_json'
    ) THEN
        ALTER TABLE gemini_advice RENAME COLUMN advice TO advice_json;
    END IF;
END $$;

-- ─────────────────────────────────────────────────────────────
-- 7. RLS POLICIES (idempotent — DROP IF EXISTS then CREATE)
-- ─────────────────────────────────────────────────────────────

-- Enable RLS on all tables
ALTER TABLE producers ENABLE ROW LEVEL SECURITY;
ALTER TABLE scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE shap_values ENABLE ROW LEVEL SECURITY;
ALTER TABLE model_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE fairness_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE gemini_advice ENABLE ROW LEVEL SECURITY;
ALTER TABLE shap_values_staging ENABLE ROW LEVEL SECURITY;

-- Public read policies (idempotent via DO $$ block)
DO $$
DECLARE
    t TEXT;
BEGIN
    FOR t IN SELECT unnest(ARRAY['producers', 'scores', 'shap_values', 'model_metrics', 
                                  'fairness_cache', 'gemini_advice', 'shap_values_staging'])
    LOOP
        -- Drop existing policy if exists (idempotent)
        EXECUTE format('DROP POLICY IF EXISTS "Allow public read" ON %I', t);
        EXECUTE format('CREATE POLICY "Allow public read" ON %I FOR SELECT USING (true)', t);
        
        EXECUTE format('DROP POLICY IF EXISTS "Allow backend write" ON %I', t);
        EXECUTE format('CREATE POLICY "Allow backend write" ON %I FOR ALL USING (true) WITH CHECK (true)', t);
    END LOOP;
END $$;
