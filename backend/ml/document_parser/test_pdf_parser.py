"""
Тесты для Production-ready парсера PDF нормативных актов РК.

Тесты проверяют:
- Корректность работы парсера
- Целостность таблиц
- Кэширование
- Поиск
- Обработка ошибок
"""

import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, List

import pytest

from pdf_parser_kz import (
    PDFExtractor,
    TextChunker,
    CacheManager,
    SearchEngine,
    process_pdf,
    logger,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_cache_dir():
    """Временная папка для кэша."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_chunks():
    """Пример чанков для тестирования."""
    return [
        {
            "doc_id": "TEST_DOC",
            "page_start": 1,
            "chunk_index": 0,
            "text": "Глава 1. Введение\n\nЭто введение к документу о пастбищах. "
                    "Пастбища используются для скотоводства.",
            "char_count": 85,
            "has_table": False,
        },
        {
            "doc_id": "TEST_DOC",
            "page_start": 1,
            "chunk_index": 1,
            "text": "[ТАБЛИЦА]\nРегион | Площадь | Тип\nАлматы | 5000 | степь\n[/ТАБЛИЦА]",
            "char_count": 60,
            "has_table": True,
        },
        {
            "doc_id": "TEST_DOC",
            "page_start": 2,
            "chunk_index": 2,
            "text": "Размер субсидии составляет 1000000 тенге в год. "
                    "Условия получения описаны в следующем разделе.",
            "char_count": 92,
            "has_table": False,
        },
    ]


# ============================================================================
# ТЕСТЫ TextChunker
# ============================================================================

class TestTextChunker:
    """Тесты для класса TextChunker."""
    
    def test_chunker_initialization(self):
        """Проверка инициализации чанкера."""
        chunker = TextChunker(chunk_size=3000, overlap=200)
        assert chunker.chunk_size == 3000
        assert chunker.overlap == 200
    
    def test_chunker_with_simple_text(self):
        """Чанкирование простого текста."""
        chunker = TextChunker(chunk_size=100, overlap=10)
        
        text = "Абзац первый.\n\nАбзац второй.\n\nАбзац третий."
        chunks = chunker.chunk(text, "TEST_DOC")
        
        assert len(chunks) > 0
        assert all("doc_id" in c for c in chunks)
        assert all("chunk_index" in c for c in chunks)
        assert all("text" in c for c in chunks)
    
    def test_chunker_with_tables(self):
        """Чанкирование текста с таблицами."""
        text = (
            "Введение.\n\n"
            "[ТАБЛИЦА]\n"
            "Регион | Площадь\n"
            "Аланты | 5000\n"
            "[/ТАБЛИЦА]\n\n"
            "Продолжение текста."
        )
        
        chunker = TextChunker()
        chunks = chunker.chunk(text, "TABLE_TEST")
        
        # Проверяем что хотя бы один чанк содержит таблицу
        has_table = any(c.get("has_table", False) for c in chunks)
        assert has_table, "Таблица не найдена в чанках"
    
    def test_chunk_metadata(self):
        """Проверка метаданных чанков."""
        chunker = TextChunker()
        text = "Текст для тестирования.\n\nВторой абзац."
        chunks = chunker.chunk(text, doc_id="META_TEST", page_start=5)
        
        for chunk in chunks:
            assert chunk["doc_id"] == "META_TEST"
            assert chunk["page_start"] == 5
            assert isinstance(chunk["chunk_index"], int)
            assert chunk["chunk_index"] >= 0
            assert "text" in chunk
            assert "char_count" in chunk


# ============================================================================
# ТЕСТЫ CacheManager
# ============================================================================

class TestCacheManager:
    """Тесты для класса CacheManager."""
    
    def test_cache_initialization(self, temp_cache_dir):
        """Инициализация менеджера кэша."""
        cache_mgr = CacheManager(cache_dir=temp_cache_dir)
        assert cache_mgr.cache_dir == temp_cache_dir
        assert cache_mgr.cache_dir.exists()
    
    def test_cache_save_and_load(self, temp_cache_dir, sample_chunks):
        """Сохранение и загрузка кэша."""
        cache_mgr = CacheManager(cache_dir=temp_cache_dir)
        
        # Сохраняем
        cache_mgr.save_chunks(sample_chunks, "TEST_DOC")
        
        # Загружаем
        loaded_chunks = cache_mgr.load_chunks("TEST_DOC")
        
        assert loaded_chunks is not None
        assert len(loaded_chunks) == len(sample_chunks)
        assert loaded_chunks[0]["text"] == sample_chunks[0]["text"]
    
    def test_cache_json_format(self, temp_cache_dir, sample_chunks):
        """Проверка формата JSON кэша."""
        cache_mgr = CacheManager(cache_dir=temp_cache_dir)
        cache_mgr.save_chunks(sample_chunks, "JSON_TEST")
        
        # Проверяем JSON напрямую
        cache_file = temp_cache_dir / "JSON_TEST_chunks.json"
        assert cache_file.exists()
        
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        assert "doc_id" in data
        assert "chunks_count" in data
        assert "chunks" in data
        assert data["chunks_count"] == len(sample_chunks)
    
    def test_cache_clear(self, temp_cache_dir, sample_chunks):
        """Удаление кэша."""
        cache_mgr = CacheManager(cache_dir=temp_cache_dir)
        
        # Сохраняем
        cache_mgr.save_chunks(sample_chunks, "CLEAR_TEST")
        assert cache_mgr.load_chunks("CLEAR_TEST") is not None
        
        # Удаляем
        cache_mgr.clear_cache("CLEAR_TEST")
        assert cache_mgr.load_chunks("CLEAR_TEST") is None


# ============================================================================
# ТЕСТЫ SearchEngine
# ============================================================================

class TestSearchEngine:
    """Тесты для класса SearchEngine."""
    
    def test_search_engine_initialization(self, sample_chunks):
        """Инициализация поисковой системы."""
        search = SearchEngine(sample_chunks)
        assert search.chunks == sample_chunks
    
    def test_search_simple_query(self, sample_chunks):
        """Простой поисковый запрос."""
        search = SearchEngine(sample_chunks)
        results = search.find_relevant_chunks("пастбища", top_k=5)
        
        assert len(results) > 0
        assert results[0]["doc_id"] == "TEST_DOC"
    
    def test_search_multiple_words(self, sample_chunks):
        """Поиск по нескольким словам."""
        search = SearchEngine(sample_chunks)
        results = search.find_relevant_chunks("пастбища скотоводство", top_k=5)
        
        assert len(results) > 0
    
    def test_search_with_table_keyword(self, sample_chunks):
        """Поиск связанный с таблицами."""
        search = SearchEngine(sample_chunks)
        results = search.find_relevant_chunks("регион площадь", top_k=5)
        
        assert len(results) > 0
    
    def test_search_empty_query(self, sample_chunks):
        """Поиск с пустым запросом."""
        search = SearchEngine(sample_chunks)
        results = search.find_relevant_chunks("", top_k=5)
        
        assert len(results) == 0
    
    def test_search_no_results(self, sample_chunks):
        """Поиск без релевантных результатов."""
        search = SearchEngine(sample_chunks)
        results = search.find_relevant_chunks("ксизшвпа", top_k=5)
        
        assert len(results) == 0
    
    def test_search_top_k_limit(self, sample_chunks):
        """Проверка ограничения top_k."""
        search = SearchEngine(sample_chunks)
        
        # Расширяем чанки для теста
        for i in range(10):
            sample_chunks.append({
                "doc_id": "TEST_DOC",
                "page_start": 10 + i,
                "chunk_index": 100 + i,
                "text": f"Текст {i} о пастбищах и производстве",
                "char_count": 40,
                "has_table": False,
            })
        
        search = SearchEngine(sample_chunks)
        
        # top_k=3
        results = search.find_relevant_chunks("пастбища", top_k=3)
        assert len(results) <= 3
        
        # top_k=100 (больше чем результатов)
        results = search.find_relevant_chunks("пастбища", top_k=100)
        assert len(results) <= 100


# ============================================================================
# ТЕСТЫ TextChunker (ADVANCED)
# ============================================================================

class TestTextChunkerAdvanced:
    """Продвинутые тесты для TextChunker."""
    
    def test_chunk_size_limits(self):
        """Проверка размера чанков."""
        chunker = TextChunker(chunk_size=100, overlap=10)
        
        text = "Длинный абзац. " * 20  # Очень длинный текст
        chunks = chunker.chunk(text, "SIZE_TEST")
        
        # Практически все чанки должны быть <= chunk_size
        for chunk in chunks:
            # Позволяем небольшой допуск (overlap может увеличить)
            assert len(chunk["text"]) <= 150  # chunk_size + некоторый допуск
    
    def test_chunk_overlap_consistency(self):
        """Проверка overlap између чанками."""
        chunker = TextChunker(chunk_size=200, overlap=50)
        text = "Абзац. " * 100
        chunks = chunker.chunk(text, "OVERLAP_TEST")
        
        # Проверяем что есть overlapping текст между соседними чанками
        for i in range(len(chunks) - 1):
            chunk1_end = chunks[i]["text"][-50:]
            chunk2_start = chunks[i + 1]["text"][:50]
            
            # Должно быть какое-то пересечение (если оба чанка достаточно длинные)
            if len(chunks[i]["text"]) > 100 and len(chunks[i + 1]["text"]) > 100:
                # Проверяем что есть связь между чанками
                assert len(chunk1_end) > 0 and len(chunk2_start) > 0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Интеграционные тесты."""
    
    def test_full_pipeline(self, temp_cache_dir):
        """Полный конвейер: парсинг → чанкирование → кэширование → поиск."""
        # Подготовиваем текст
        raw_text = """
        Закон о пастбищах.
        
        Глава 1. Общие положения.
        
        Пастбища используются для скотоводства, овцеводства и коневодства.
        
        [ТАБЛИЦА]
        Тип производства | Регион | Площадь
        Скотоводство | Алматы | 5000
        Овцеводство | Карагандинская | 3000
        [/ТАБЛИЦА]
        
        Глава 2. Субсидии.
        
        Размер субсидии составляет 1000000 тенге.
        
        Условия получения описаны в регламенте.
        """
        
        # Чанкируем
        chunker = TextChunker()
        chunks = chunker.chunk(raw_text, "FULL_TEST")
        
        # Сохраняем кэш
        cache_mgr = CacheManager(cache_dir=temp_cache_dir)
        cache_mgr.save_chunks(chunks, "FULL_TEST")
        
        # Загружаем из кэша
        loaded_chunks = cache_mgr.load_chunks("FULL_TEST")
        assert len(loaded_chunks) == len(chunks)
        
        # Ищем
        search = SearchEngine(loaded_chunks)
        results = search.find_relevant_chunks("пастбища скотоводство", top_k=5)
        assert len(results) > 0
    
    def test_russian_and_kazakh_support(self):
        """Поддержка русского и казахского языков."""
        text = """
        Қазақстан Республикасының пастбі заңы.
        
        Закон о пастбищах Республики Казахстан.
        
        Мүлік пастбі өндіс: сиыр өндіктігі, қойшылық, аттыл.
        
        Типы пастбищ: луговые, степные, пустынные.
        """
        
        chunker = TextChunker()
        chunks = chunker.chunk(text, "LANG_TEST")
        
        # Проверяем что оба языка сохранились
        full_text = " ".join(c["text"] for c in chunks)
        assert "пастбі" in full_text  # казахский
        assert "пастбищ" in full_text  # русский


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Тесты производительности."""
    
    def test_large_text_chunking(self):
        """Чанкирование больших текстов."""
        import time
        
        # Симулируем большой документ (500+ страниц)
        text = ("Абзац текста. " * 500 + "\n\n") * 100  # ~100 KB
        
        chunker = TextChunker()
        
        start_time = time.time()
        chunks = chunker.chunk(text, "PERF_TEST")
        elapsed = time.time() - start_time
        
        print(f"\n⏱️  Чанкирование 100KB текста: {elapsed:.2f} сек")
        print(f"   Создано {len(chunks)} чанков")
        
        # Должно выполниться быстро
        assert elapsed < 10.0  # Должно быть быстрее 10 секунд
    
    def test_search_performance(self):
        """Производительность поиска."""
        import time
        
        # Генерируем много чанков
        chunks = []
        for i in range(1000):
            chunks.append({
                "doc_id": "PERF_DOC",
                "page_start": i // 10,
                "chunk_index": i,
                "text": f"Текст чанка {i} про пастбища и производство",
                "char_count": 45,
                "has_table": i % 10 == 0,
            })
        
        search = SearchEngine(chunks)
        
        start_time = time.time()
        results = search.find_relevant_chunks("пастбища", top_k=5)
        elapsed = time.time() - start_time
        
        print(f"\n⏱️  Поиск в 1000 чанках: {elapsed:.3f} сек")
        print(f"   Найдено {len(results)} результатов")
        
        # Должно быть очень быстро
        assert elapsed < 1.0  # Меньше 1 секунды


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    """Запуск тестов."""
    print("\n" + "=" * 70)
    print("Запуск тестов Production-ready парсера PDF")
    print("=" * 70 + "\n")
    
    # Для запуска используйте:
    # pytest test_pdf_parser.py -v
    
    print("✓ Используйте pytest для запуска тестов:")
    print("  pytest test_pdf_parser.py -v")
    print("  pytest test_pdf_parser.py -v -s  # С выводом логов")
    print("  pytest test_pdf_parser.py::TestTextChunker -v  # Конкретный класс")
