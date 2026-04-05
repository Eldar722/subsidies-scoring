-- Миграция production: SHAP (уникальность) + gemini_advice (advice_json).
-- Применение:
--   A) Supabase Dashboard → SQL Editor → вставить и Run
--   B) Локально: DATABASE_URL="postgresql://postgres:...@db.xxx.supabase.co:5432/postgres"
--      python backend/scripts/run_supabase_sql.py docs/supabase_migrations/001_shap_unique_gemini_advice_json.sql

-- 0) Мусорные строки (мешают NOT NULL / дедупу)
DELETE FROM shap_values
WHERE producer_id IS NULL
   OR feature IS NULL
   OR trim(producer_id) = ''
   OR trim(feature) = '';

-- 1) SHAP: дубликаты — оставить одну строку с max(id) на (producer_id, feature)
DELETE FROM shap_values a
USING shap_values b
WHERE a.producer_id = b.producer_id
  AND a.feature = b.feature
  AND a.id < b.id;

-- 2) NOT NULL
ALTER TABLE shap_values
  ALTER COLUMN producer_id SET NOT NULL,
  ALTER COLUMN feature SET NOT NULL;

-- 3) Уникальный индекс (идемпотентно; совпадает с именем CONSTRAINT в schema.sql)
CREATE UNIQUE INDEX IF NOT EXISTS shap_values_producer_feature_key
  ON shap_values (producer_id, feature);

-- 4) gemini_advice: переименовать advice → advice_json, если нужно
DO $$
BEGIN
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

-- 5) Обе колонки (редкий случай после ручных правок): слить в advice_json
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'gemini_advice' AND column_name = 'advice'
  ) AND EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'gemini_advice' AND column_name = 'advice_json'
  ) THEN
    UPDATE gemini_advice SET advice_json = COALESCE(advice_json, advice) WHERE advice_json IS NULL;
    ALTER TABLE gemini_advice DROP COLUMN advice;
  END IF;
END $$;
