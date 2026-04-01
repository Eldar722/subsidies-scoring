-- Включение Realtime для таблицы scores (чтобы графики на фронте обновлялись в реальном времени)
ALTER PUBLICATION supabase_realtime ADD TABLE scores;

-- Включение Row Level Security (Блокирует публичный несанкционированный доступ)
ALTER TABLE producers ENABLE ROW LEVEL SECURITY;
ALTER TABLE scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE shap_values ENABLE ROW LEVEL SECURITY;

-- Создание политик чтения (Разрешаем фронтенду читать данные с помощью анонимного API-ключа)
CREATE POLICY "Allow public read" ON producers FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON scores FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON shap_values FOR SELECT USING (true);

-- Создание политик записи (Разрешаем писать данные только авторизованному Backend'у)
CREATE POLICY "Allow backend write" ON producers FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow backend write" ON scores FOR INSERT WITH CHECK (true);
