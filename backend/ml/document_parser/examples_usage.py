"""
Примеры использования Production-ready парсера PDF для РК нормативных актов.

Все примеры полностью рабочие и готовы к использованию.
"""

import logging
from pathlib import Path
from pdf_parser_kz import (
    PDFExtractor,
    TextChunker,
    CacheManager,
    SearchEngine,
    process_pdf,
    logger,
)


# ============================================================================
# ПРИМЕР 1: Простой парсинг с кэшированием (РЕКОМЕНДУЕМЫЙ)
# ============================================================================

def example_simple_parsing():
    """
    Самый простой способ обработки PDF документа.
    
    Использует полный конвейер: парсинг → чанкирование → кэширование.
    Если документ уже парсился раньше — загружает из кэша.
    """
    print("\n" + "=" * 70)
    print("ПРИМЕР 1: Простой парсинг с кэшированием")
    print("=" * 70)
    
    # Путь к вашему PDF (замените на реальный файл)
    pdf_file = Path("reglament_subsidies.pdf")  # или другой документ РК
    doc_id = "REGLAMENT_2025"  # Уникальный идентификатор
    
    # Проверяем существование файла для примера
    if not pdf_file.exists():
        print(f"⚠️  Файл не найден: {pdf_file}")
        print("   Используйте реальный путь к PDF файлу")
        return
    
    # Основная функция обработки
    chunks = process_pdf(
        pdf_path=str(pdf_file),
        doc_id=doc_id,
        force=False  # Если True — переопарсит даже если есть кэш
    )
    
    # Вывод статистики
    print(f"\n✓ Обработано успешно!")
    print(f"  Чанков создано: {len(chunks)}")
    print(f"  Первый чанк: {chunks[0]['text'][:100]}...")
    
    return chunks


# ============================================================================
# ПРИМЕР 2: Использование компонентов отдельно (ПРОДВИНУТЫЙ)
# ============================================================================

def example_component_usage():
    """
    Использование отдельных компонентов парсера.
    
    Полезно если нужна гибкость при обработке PDF.
    """
    print("\n" + "=" * 70)
    print("ПРИМЕР 2: Работа с отдельными компонентами")
    print("=" * 70)
    
    pdf_file = Path("reglament_subsidies.pdf")
    doc_id = "REGLAMENT_2025"
    
    if not pdf_file.exists():
        print(f"⚠️  Файл не найден: {pdf_file}")
        return
    
    # Шаг 1: Парсим PDF
    print("\n1️⃣  Парсим PDF документ...")
    extractor = PDFExtractor(pdf_path=str(pdf_file), doc_id=doc_id)
    parse_result = extractor.parse(force=False)
    
    print(f"   ✓ Распарсено {parse_result['total_pages']} страниц")
    print(f"   ✓ Всего символов: {len(parse_result['raw_text'])}")
    
    # Шаг 2: Разбиваем на чанки
    print("\n2️⃣  Разбиваем текст на чанки...")
    chunker = TextChunker(
        chunk_size=3000,    # Размер чанка в символах
        overlap=200         # Перекрытие между чанками
    )
    chunks = chunker.chunk(
        raw_text=parse_result['raw_text'],
        doc_id=doc_id,
        page_start=1
    )
    
    print(f"   ✓ Создано {len(chunks)} чанков")
    
    # Шаг 3: Сохраняем в кэш
    print("\n3️⃣  Сохраняем в JSON кэш...")
    cache_mgr = CacheManager()
    cache_path = cache_mgr.save_chunks(
        chunks=chunks,
        doc_id=doc_id,
        metadata=parse_result
    )
    
    print(f"   ✓ Сохранено в {cache_path}")
    
    return chunks


# ============================================================================
# ПРИМЕР 3: Поиск в документе (KEYWORD-BASED)
# ============================================================================

def example_search():
    """
    Поиск релевантных фрагментов документа по запросу.
    
    Использует keyword-based поиск (не нужны embeddings и LLM).
    """
    print("\n" + "=" * 70)
    print("ПРИМЕР 3: Поиск по документу")
    print("=" * 70)
    
    pdf_file = Path("reglament_subsidies.pdf")
    doc_id = "REGLAMENT_2025"
    
    if not pdf_file.exists():
        print(f"⚠️  Файл не найден: {pdf_file}")
        return
    
    # Сначала обрабатываем документ
    chunks = process_pdf(
        pdf_path=str(pdf_file),
        doc_id=doc_id,
        force=False
    )
    
    # Инициализируем поисковую систему
    search_engine = SearchEngine(chunks)
    
    # Примеры запросов жка нормативные акты РК
    queries = [
        "пастбища скотоводство регион",
        "размер субсидии производство",
        "условия получения помощи",
    ]
    
    for query in queries:
        print(f"\n🔍 Поиск по запросу: '{query}'")
        
        # Поиск top-5 релевантных чанков
        results = search_engine.find_relevant_chunks(
            query=query,
            top_k=5
        )
        
        if results:
            print(f"   Найдено {len(results)} релевантных чанков:\n")
            
            for idx, chunk in enumerate(results, 1):
                print(f"   {idx}. Чанк #{chunk['chunk_index']} "
                      f"(страница {chunk['page_start']})")
                print(f"      {chunk['text'][:150]}...")
                print()
        else:
            print(f"   ❌ Результатов не найдено")


# ============================================================================
# ПРИМЕР 4: Работа с кэшем
# ============================================================================

def example_cache_management():
    """
    Управление JSON кэшем документов.
    
    Демонстрирует: сохранение, загрузку, проверку и очистку кэша.
    """
    print("\n" + "=" * 70)
    print("ПРИМЕР 4: Управление кэшем")
    print("=" * 70)
    
    pdf_file = Path("reglament_subsidies.pdf")
    doc_id = "REGLAMENT_2025"
    
    if not pdf_file.exists():
        print(f"⚠️  Файл не найден: {pdf_file}")
        return
    
    cache_mgr = CacheManager()
    
    # Шаг 1: Обработайте и сохраните
    print("\n1️⃣  Сохраняем документ в кэш...")
    chunks = process_pdf(
        pdf_path=str(pdf_file),
        doc_id=doc_id,
        force=True  # Принудительно переопарсим
    )
    print(f"   ✓ Сохранено {len(chunks)} чанков")
    
    # Шаг 2: Проверяем валидность кэша
    print("\n2️⃣  Проверяем кэш...")
    is_valid = cache_mgr.is_cache_valid(doc_id, pdf_file)
    if is_valid:
        print("   ✓ Кэш актуален (свежее чем PDF)")
    else:
        print("   ⚠️  Кэш устарел (старше чем PDF)")
    
    # Шаг 3: Загружаем из кэша
    print("\n3️⃣  Загружаем из кэша...")
    cached_chunks = cache_mgr.load_chunks(doc_id)
    if cached_chunks:
        print(f"   ✓ Загружено {len(cached_chunks)} чанков из кэша")
    else:
        print("   ❌ Кэш не найден")
    
    # Шаг 4: Удаляем кэш
    print("\n4️⃣  Удаляем кэш...")
    cache_mgr.clear_cache(doc_id)
    print("   ✓ Кэш удалён")
    
    # Проверяем что кэша больше нет
    if not cache_mgr.load_chunks(doc_id):
        print("   ✓ Подтверждение: кэша нет")


# ============================================================================
# ПРИМЕР 5: Анализ чанков
# ============================================================================

def example_chunk_analysis():
    """
    Анализ статистики чанков документа.
    
    Показывает: распределение размера, таблицы, метаданные.
    """
    print("\n" + "=" * 70)
    print("ПРИМЕР 5: Анализ статистики чанков")
    print("=" * 70)
    
    pdf_file = Path("reglament_subsidies.pdf")
    doc_id = "REGLAMENT_2025"
    
    if not pdf_file.exists():
        print(f"⚠️  Файл не найден: {pdf_file}")
        return
    
    # Обработаем документ
    chunks = process_pdf(
        pdf_path=str(pdf_file),
        doc_id=doc_id,
        force=False
    )
    
    # Анализ
    print(f"\n📊 Статистика чанков:\n")
    
    # Общая информация
    total_chars = sum(c['char_count'] for c in chunks)
    avg_size = total_chars / len(chunks) if chunks else 0
    
    print(f"  📌 Всего чанков: {len(chunks)}")
    print(f"  📝 Всего символов: {total_chars:,}")
    print(f"  📐 Средний размер чанка: {avg_size:.0f} символов")
    
    # Таб льцы
    chunks_with_tables = sum(1 for c in chunks if c.get('has_table', False))
    print(f"  📋 Чанков с таблицами: {chunks_with_tables}")
    
    # Распределение по страницам
    print(f"\n  Распределение по страницам:")
    page_chunks = {}
    for chunk in chunks:
        page = chunk['page_start']
        page_chunks[page] = page_chunks.get(page, 0) + 1
    
    for page, count in sorted(page_chunks.items())[:10]:  # Первые 10 страниц
        print(f"    Страница {page}: {count} чанков")
    
    if len(page_chunks) > 10:
        print(f"    ... и ещё {len(page_chunks) - 10} страниц")
    
    # Размер чанков
    print(f"\n  Размер чанков:")
    min_size = min(c['char_count'] for c in chunks)
    max_size = max(c['char_count'] for c in chunks)
    print(f"    Минимум: {min_size} символов")
    print(f"    Максимум: {max_size} символов")
    print(f"    Среднее: {avg_size:.0f} символов")


# ============================================================================
# ПРИМЕР 6: Интеграция в FastAPI
# ============================================================================

def example_integration_fastapi():
    """
    Пример интеграции парсера в FastAPI приложение.
    
    Этот код показывает как использовать парсер в backend.
    """
    print("\n" + "=" * 70)
    print("ПРИМЕР 6: Интеграция в FastAPI")
    print("=" * 70)
    
    example_code = """
    # Добавьте это в ваш main.py (backend)
    
    from fastapi import FastAPI, UploadFile, File
    from ml.document_parser.pdf_parser_kz import process_pdf, SearchEngine
    from pathlib import Path
    
    app = FastAPI()
    
    @app.post("/api/documents/parse")
    async def parse_document(file: UploadFile = File(...)):
        '''Парсит загруженный PDF документ.'''
        
        # Сохраняем файл
        pdf_path = Path(f"data/documents/{file.filename}")
        with open(pdf_path, "wb") as f:
            f.write(await file.read())
        
        # Парсим документ
        doc_id = file.filename.split(".")[0]
        chunks = process_pdf(
            pdf_path=str(pdf_path),
            doc_id=doc_id,
            force=False
        )
        
        return {
            "doc_id": doc_id,
            "chunks_count": len(chunks),
            "total_chars": sum(c['char_count'] for c in chunks),
            "status": "success"
        }
    
    @app.get("/api/documents/{doc_id}/search")
    async def search_document(doc_id: str, query: str):
        '''Поиск по загруженному документу.'''
        
        from ml.document_parser.pdf_parser_kz import CacheManager
        
        cache_mgr = CacheManager()
        chunks = cache_mgr.load_chunks(doc_id)
        
        if not chunks:
            return {"error": "Документ не найден", "status": "error"}
        
        search_engine = SearchEngine(chunks)
        results = search_engine.find_relevant_chunks(query, top_k=5)
        
        return {
            "query": query,
            "results_count": len(results),
            "results": results,
            "status": "success"
        }
    """
    
    print(example_code)


# ============================================================================
# ПРИМЕР 7: Батч обработка нескольких документов
# ============================================================================

def example_batch_processing():
    """
    Обработка нескольких PDF документов подряд.
    
    Полезно для массовой обработки нормативных актов РК.
    """
    print("\n" + "=" * 70)
    print("ПРИМЕР 7: Батч обработка документов")
    print("=" * 70)
    
    # Список документов для обработки
    documents = [
        ("law_2025.pdf", "LAW_2025"),
        ("resolution_2025.pdf", "RESOLUTION_2025"),
        ("regulation_2025.pdf", "REGULATION_2025"),
    ]
    
    print("\n📂 Обработка документов...\n")
    
    all_chunks = {}
    
    for pdf_file, doc_id in documents:
        pdf_path = Path(pdf_file)
        
        if not pdf_path.exists():
            print(f"  ⚠️  Пропущено (не найден): {pdf_file}")
            continue
        
        print(f"  ⏳ Обработка: {doc_id}...")
        
        try:
            chunks = process_pdf(
                pdf_path=str(pdf_path),
                doc_id=doc_id,
                force=False
            )
            
            all_chunks[doc_id] = chunks
            print(f"     ✓ Готово ({len(chunks)} чанков)\n")
        
        except Exception as e:
            print(f"     ❌ Ошибка: {str(e)}\n")
            continue
    
    # Итоговая статистика
    print(f"📊 Итого:\n")
    print(f"  Документов обработано: {len(all_chunks)}")
    total_chunks = sum(len(c) for c in all_chunks.values())
    print(f"  Всего чанков: {total_chunks}")


# ============================================================================
# ГЛАВНЫЙ ВХОД
# ============================================================================

if __name__ == "__main__":
    """
    Запуск примеров использования.
    
    Закомментируйте/раскомментируйте нужные примеры.
    """
    
    print("\n" + "=" * 70)
    print("ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ: Production-ready парсер PDF для РК")
    print("=" * 70)
    
    # Пример 1: Простой парсинг (РЕКОМЕНДУЕТСЯ НАЧАТЬ ОТСЮДА)
    # example_simple_parsing()
    
    # Пример 2: Компоненты отдельно
    # example_component_usage()
    
    # Пример 3: Поиск
    # example_search()
    
    # Пример 4: Кэш
    # example_cache_management()
    
    # Пример 5: Анализ
    # example_chunk_analysis()
    
    # Пример 6: Интеграция в FastAPI
    example_integration_fastapi()
    
    # Пример 7: Батч обработка
    # example_batch_processing()
    
    print("\n" + "=" * 70)
    print("✓ Примеры готовы!")
    print("=" * 70)
    print("\nДля запуска примера раскомментируйте нужную функцию в __main__")
    print("и запустите: python examples_usage.py")
