"""
QUICK START: Production-ready парсер PDF для РК нормативных актов

Это файл для быстрого старта. Просто запустите и следуйте инструкциям.
"""

import sys
from pathlib import Path

# ============================================================================
# ПОШАГОВЫЙ ГАЙД
# ============================================================================

def main():
    """Главная функция quick-start."""
    
    print("\n" + "=" * 70)
    print("🚀 QUICK START: PDF Parser для РК нормативных актов")
    print("=" * 70)
    
    # Шаг 1: Проверка установки
    print("\n[ШАГИ УСТАНОВКИ]\n")
    
    print("1️⃣  Проверяем установку pdfplumber...")
    try:
        import pdfplumber
        print("   ✓ pdfplumber установлен")
    except ImportError:
        print("   ❌ pdfplumber НЕ установлен!")
        print("\n   Запустите:")
        print("   $ pip install -r requirements.txt")
        print("\n   Или напрямую:")
        print("   $ pip install pdfplumber==0.10.3")
        return 1
    
    print("\n2️⃣  Проверяем основные модули...")
    try:
        from pdf_parser_kz import (
            PDFExtractor,
            TextChunker,
            CacheManager,
            SearchEngine,
            process_pdf,
        )
        print("   ✓ Все модули загружены")
    except ImportError as e:
        print(f"   ❌ Ошибка импорта: {e}")
        return 1
    
    # Шаг 2: Демонстрация
    print("\n[ДЕМОНСТРАЦИЯ]\n")
    
    print("3️⃣  Демонстрация TextChunker (чанкирование текста)...")
    try:
        text = """
        Закон о пастбищах Республики Казахстан.
        
        Глава 1. Пастбища используются для скотоводства.
        
        [ТАБЛИЦА]
        Регион | Площадь | Тип
        Алматы | 5000 | степь
        [/ТАБЛИЦА]
        
        Субсидия составляет 1000000 тенге в год.
        """
        
        chunker = TextChunker()
        chunks = chunker.chunk(text, doc_id="DEMO")
        
        print(f"   ✓ Создано {len(chunks)} чанков")
        print(f"   ✓ Всего символов: {sum(c['char_count'] for c in chunks)}")
        
        for i, chunk in enumerate(chunks):
            print(f"\n   Чанк {i}: {chunk['text'][:60]}...")
    
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return 1
    
    print("\n4️⃣  Демонстрация SearchEngine (поиск)...")
    try:
        search = SearchEngine(chunks)
        results = search.find_relevant_chunks("пастбища скотоводство", top_k=3)
        
        print(f"   ✓ Найдено {len(results)} результатов")
        
        for i, result in enumerate(results):
            print(f"\n   Результат {i + 1}: {result['text'][:60]}...")
    
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return 1
    
    # Шаг 3: Основные команды
    print("\n[ОСНОВНЫЕ КОМАНДЫ]\n")
    
    print("5️⃣  Примеры использования:\n")
    
    print("   # Парсинг PDF документа")
    print("   from pdf_parser_kz import process_pdf")
    print("   chunks = process_pdf('document.pdf', 'DOC_2025')\n")
    
    print("   # Поиск в документе")
    print("   from pdf_parser_kz import SearchEngine")
    print("   search = SearchEngine(chunks)")
    print("   results = search.find_relevant_chunks('запрос', top_k=5)\n")
    
    print("   # Управление кэшем")
    print("   from pdf_parser_kz import CacheManager")
    print("   cache = CacheManager()")
    print("   cache.save_chunks(chunks, 'DOC_2025')")
    print("   chunks = cache.load_chunks('DOC_2025')\n")
    
    # Шаг 4: Файлы в проекте
    print("[ФАЙЛЫ ПРОЕКТА]\n")
    
    files = [
        ("pdf_parser_kz.py", "Основной модуль парсера (500+ строк)"),
        ("examples_usage.py", "7 примеров использования"),
        ("test_pdf_parser.py", "Полный набор тестов"),
        ("requirements.txt", "Зависимости проекта"),
        ("README.md", "Подробная документация"),
        ("QUICKSTART.py", "Этот файл"),
    ]
    
    print("6️⃣  Содержимое папки document_parser:\n")
    
    for filename, description in files:
        filepath = Path(__file__).parent / filename
        if filepath.exists():
            print(f"   ✓ {filename:25} - {description}")
        else:
            print(f"   ❌ {filename:25} - ОТСУТСТВУЕТ!")
    
    # Шаг 5: Следующие шаги
    print("\n[СЛЕДУЮЩИЕ ШАГИ]\n")
    
    print("7️⃣  Что делать дальше:\n")
    
    print("   a) Попробуйте на реальном PDF:")
    print("      chunks = process_pdf('your_document.pdf', 'YOUR_DOC')\n")
    
    print("   b) Запустите примеры использования:")
    print("      python examples_usage.py\n")
    
    print("   c) Запустите тесты (нужен pytest):")
    print("      pip install pytest")
    print("      pytest test_pdf_parser.py -v\n")
    
    print("   d) Интегрируйте в ваш проект:")
    print("      from ml.document_parser import process_pdf\n")
    
    # Итоги
    print("[ИТОГИ]\n")
    
    print("✅ Система готова к использованию!\n")
    
    print("📞 Контакты:")
    print("   Автор: Eldar722")
    print("   Дата: Апрель 2025")
    print("   Проект: subsidies-scoring\n")
    
    print("📚 Документация: README.md")
    print("🧪 Тесты: test_pdf_parser.py")
    print("📋 Примеры: examples_usage.py\n")
    
    print("=" * 70)
    print("✓ QUICK START завершён успешно!")
    print("=" * 70 + "\n")
    
    return 0


# ============================================================================
# ПРОВЕРКА СИСТЕМЫ
# ============================================================================

def check_system():
    """Проверяет систему перед началом."""
    
    print("\n" + "=" * 70)
    print("🔍 ПРОВЕРКА СИСТЕМЫ")
    print("=" * 70 + "\n")
    
    checks = []
    
    # Проверка Python версии
    print(f"📌 Python версия: {sys.version}")
    
    # Проверка pdfplumber
    try:
        import pdfplumber
        print(f"📌 pdfplumber: {pdfplumber.__version__ if hasattr(pdfplumber, '__version__') else 'установлен'}")
        checks.append(True)
    except ImportError:
        print(f"❌ pdfplumber: НЕ установлен")
        checks.append(False)
    
    # Проверка файлов
    print(f"📌 Текущая папка: {Path.cwd()}\n")
    
    files_to_check = [
        "pdf_parser_kz.py",
        "requirements.txt",
        "README.md",
        "examples_usage.py",
        "test_pdf_parser.py",
    ]
    
    print("Файлы проекта:")
    for filename in files_to_check:
        filepath = Path(filename)
        if filepath.exists():
            size = filepath.stat().st_size / 1024  # в KB
            print(f"  ✓ {filename:25} ({size:.1f} KB)")
            checks.append(True)
        else:
            print(f"  ❌ {filename:25} ОТСУТСТВУЕТ")
            checks.append(False)
    
    # Итоговая проверка
    all_ok = all(checks)
    
    if all_ok:
        print("\n✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ\n")
    else:
        print("\n⚠️  ЕСТЬ ПРОБЛЕМЫ, СМОТРИТЕ ВЫШЕ\n")
    
    return all_ok


# ============================================================================
# ПРИМЕРЫ КОМАНД
# ============================================================================

def print_examples():
    """Выводит примеры команд."""
    
    examples = """
    ============================================================================
    ПРИМЕРЫ КОМАНД
    ============================================================================
    
    # 1. Простой парсинг (загружает из кэша если существует)
    from pdf_parser_kz import process_pdf
    chunks = process_pdf("reglament.pdf", "REG_2025")
    
    # 2. Парсинг с переопарсингом
    chunks = process_pdf("reglament.pdf", "REG_2025", force=True)
    
    # 3. Поиск в документе
    from pdf_parser_kz import SearchEngine
    search = SearchEngine(chunks)
    results = search.find_relevant_chunks("пастбища производство", top_k=5)
    
    # 4. Сохранение и загрузка кэша
    from pdf_parser_kz import CacheManager
    cache = CacheManager()
    cache.save_chunks(chunks, "DOC_ID")
    chunks = cache.load_chunks("DOC_ID")
    
    # 5. Работа с компонентами отдельно
    from pdf_parser_kz import PDFExtractor, TextChunker
    
    extractor = PDFExtractor("doc.pdf", "DOC_ID")
    parsed = extractor.parse()
    
    chunker = TextChunker()
    chunks = chunker.chunk(parsed['raw_text'], "DOC_ID")
    
    # 6. Статистика чанков
    total_chars = sum(c['char_count'] for c in chunks)
    chunks_with_tables = sum(1 for c in chunks if c.get('has_table'))
    print(f"Чанков: {len(chunks)}, Символов: {total_chars}, Таблиц: {chunks_with_tables}")
    
    ============================================================================
    """
    
    print(examples)


# ============================================================================
# MAIN WITH MENU
# ============================================================================

if __name__ == "__main__":
    """Главная точка входа."""
    
    print("""
    ╔════════════════════════════════════════════════════════════════════════╗
    ║                                                                        ║
    ║   Production-ready парсер PDF для РК нормативных актов               ║
    ║                                                                        ║
    ║   Версия: 1.0.0                                                       ║
    ║   Автор: Eldar722                                                     ║
    ║   Дата: Апрель 2025                                                   ║
    ║                                                                        ║
    ╚════════════════════════════════════════════════════════════════════════╝
    """)
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "--check":
            check_system()
        elif command == "--examples":
            print_examples()
        elif command == "--help":
            print("""
Использование: python QUICKSTART.py [команда]

Команды:
  (без аргументов)  - Запустить full quick start
  --check           - Проверить систему
  --examples        - Показать примеры команд
  --help            - Показать эту справку
            """)
        else:
            print(f"Неизвестная команда: {command}")
            print("Используйте: python QUICKSTART.py --help")
    else:
        # Полный quick start
        sys.exit(main())
