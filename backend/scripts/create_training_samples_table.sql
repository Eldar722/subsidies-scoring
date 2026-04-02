-- Create training_samples table for synthetic data storage
-- Store both original and synthetic training data with is_synthetic flag

CREATE TABLE IF NOT EXISTS training_samples (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    nomero_zajavki TEXT,
    producer_id TEXT,
    oblast TEXT,
    napravlenie_vodstva TEXT,
    naimenovanie_subsidirovanija TEXT,
    rajon_hozjastva TEXT,
    prichitavshajasja_summa NUMERIC,
    normatif NUMERIC,
    data_postuplenija TIMESTAMPTZ,
    
    target SMALLINT,
    
    is_synthetic BOOLEAN DEFAULT FALSE,
    synthetic_method TEXT,
    original_index BIGINT,
    
    year SMALLINT,
    month SMALLINT,
    hour SMALLINT,
    day_of_week SMALLINT,
    day_of_year SMALLINT,
    
    amount_to_norm NUMERIC,
    log_amount NUMERIC,
    log_norm NUMERIC
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_training_samples_is_synthetic 
    ON training_samples (is_synthetic);
CREATE INDEX IF NOT EXISTS idx_training_samples_synthetic_method 
    ON training_samples (synthetic_method);
CREATE INDEX IF NOT EXISTS idx_training_samples_producer_id 
    ON training_samples (producer_id);
CREATE INDEX IF NOT EXISTS idx_training_samples_target 
    ON training_samples (target);

-- Enable RLS
ALTER TABLE training_samples ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Allow public read" ON training_samples FOR SELECT USING (true);
CREATE POLICY "Allow backend write" ON training_samples FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow backend update" ON training_samples FOR UPDATE WITH CHECK (true);
