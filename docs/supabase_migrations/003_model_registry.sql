-- ══════════════════════════════════════════════════════════════════════════════
-- Migration 003: Model Version Registry + Auto-Rollback Support
--
-- Features:
--   - model_registry: tracks all model versions with metrics
--   - Status tracking: registered | active | rolled_back | archived
--   - Rollback reason logging
--   - JSONB metadata for reproducibility
--
-- Fully idempotent (safe to re-run).
-- ══════════════════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────
-- 1. MODEL REGISTRY TABLE
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS model_registry (
    version TEXT PRIMARY KEY,
    roc_auc FLOAT,
    cv_auc_mean FLOAT,
    best_f1 FLOAT,
    precision FLOAT,
    recall FLOAT,
    train_size INT,
    val_size INT,
    dataset_hash TEXT,
    seed INT,
    feature_count INT,
    storage_path TEXT,
    storage_type TEXT DEFAULT 'local',
    status TEXT DEFAULT 'registered',
    created_at TIMESTAMPTZ DEFAULT now(),
    activated_at TIMESTAMPTZ,
    deactivated_at TIMESTAMPTZ,
    rollback_reason TEXT,
    metadata JSONB
);

-- ─────────────────────────────────────────────────────────────
-- 2. INDEXES
-- ─────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_model_registry_status ON model_registry(status);
CREATE INDEX IF NOT EXISTS idx_model_registry_created ON model_registry(created_at DESC);

-- ─────────────────────────────────────────────────────────────
-- 3. RLS POLICIES
-- ─────────────────────────────────────────────────────────────

ALTER TABLE model_registry ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    -- Drop existing policies if re-run
    DROP POLICY IF EXISTS "Allow public read" ON model_registry;
    DROP POLICY IF EXISTS "Allow backend write" ON model_registry;
END $$;

CREATE POLICY "Allow public read" ON model_registry FOR SELECT USING (true);
CREATE POLICY "Allow backend write" ON model_registry FOR ALL USING (true) WITH CHECK (true);
