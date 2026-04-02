-- Migration: Create training_samples table for synthetic data storage
-- Purpose: Store both original and synthetic training data with is_synthetic flag

-- ══════════════════════════════════════════════════════════════════════════════
-- Table creation
-- ══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS training_samples (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Данные из оригинального/синтетического набора
    номер_заявки TEXT,
    producer_id TEXT,
    область TEXT,
    направление_водства TEXT,
    наименование_субсидирования TEXT,
    район_хозяйства TEXT,
    причитавшаяся_сумма NUMERIC,
    норматив NUMERIC,
    дата_поступления TIMESTAMPTZ,
    
    -- Целеве знач (1 = одобрено/исполнено, 0 = отклонено)
    target SMALLINT,
    
    -- Флаги метаданных
    is_synthetic BOOLEAN DEFAULT FALSE,
    synthetic_method TEXT,  -- 'borderline_smote', 'gaussian', 'bootstrap', NULL для оригинала
    original_index BIGINT,  -- индекс оригинального образца (для синтики)
    
    -- Временные признаки (вычисляются)
    year SMALLINT,
    month SMALLINT,
    hour SMALLINT,
    day_of_week SMALLINT,
    day_of_year SMALLINT,
    
    -- Производные финансовые
    amount_to_norm NUMERIC,
    log_amount NUMERIC,
    log_norm NUMERIC
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_training_samples_is_synthetic 
    ON training_samples (is_synthetic);
CREATE INDEX IF NOT EXISTS idx_training_samples_synthetic_method 
    ON training_samples (synthetic_method);
CREATE INDEX IF NOT EXISTS idx_training_samples_producer_id 
    ON training_samples (producer_id);
CREATE INDEX IF NOT EXISTS idx_training_samples_target 
    ON training_samples (target);

-- ══════════════════════════════════════════════════════════════════════════════
-- Row Level Security
-- ══════════════════════════════════════════════════════════════════════════════

ALTER TABLE training_samples ENABLE ROW LEVEL SECURITY;

-- Разрешить чтение фронтенду / API
CREATE POLICY "Allow public read" ON training_samples FOR SELECT USING (true);

-- Разрешить записьнемного бэкенду
CREATE POLICY "Allow backend write" ON training_samples FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow backend update" ON training_samples FOR UPDATE WITH CHECK (true);

-- ══════════════════════════════════════════════════════════════════════════════
-- Комментарии для документации
-- ══════════════════════════════════════════════════════════════════════════════

COMMENT ON TABLE training_samples IS 'Training data with synthetic samples for ML model improvement';
COMMENT ON COLUMN training_samples.is_synthetic IS '1 если синтетический образец, 0 если оригинальный';
COMMENT ON COLUMN training_samples.synthetic_method IS 'Метод генерации (borderline_smote, gaussian, bootstrap)';
COMMENT ON COLUMN training_samples.original_index IS 'Индекс оригинального образца, на основе которого создана синтетика (для трассировки)';
