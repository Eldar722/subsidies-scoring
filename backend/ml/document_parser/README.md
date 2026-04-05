# Production-ready парсер PDF для нормативно-правовых актов РК

**Версия:** 1.0.0  
**Автор:** Eldar722  
**Дата:** 2025  
**Язык:** Python 3.8+  

---

## 📋 Оглавление

1. [Описание](#описание)
2. [Возможности](#возможности)
3. [Установка](#установка)
4. [Быстрый старт](#быстрый-старт)
5. [Архитектура](#архитектура)
6. [Примеры использования](#примеры-использования)
7. [API документация](#api-документация)
8. [Проверка качества](#проверка-качества)
9. [Интеграция в проект](#интеграция-в-проект)
10. [FAQ](#faq)

---

## 📖 Описание

Production-ready парсер PDF для нормативно-правовых актов Республики Казахстан.

**Основные задачи:**
- ✅ Извлечение текста из больших PDF (100+ страниц)
- ✅ Извлечение таблиц без потери данных
- ✅ Эффективная обработка памяти (постраничная, не весь документ в памяти)
- ✅ Интеллектуальный чанкинг по абзацам (3000 символов, 200 overlap)
- ✅ Кэширование результатов в JSON
- ✅ Keyword-based поиск по документу
- ✅ Обработка ошибок (битые страницы, пустые документы)

**Точность парсинга:**
- Сохранение всех числовых данных, процентов, денежных единиц
- Сохранение названий регионов, типов пастбищ, видов производства
- Неразрывные таблицы (не разрываются посередине)
- Поддержка русского и казахского языков

---

## ✨ Возможности

| Возможность | Описание | Статус |
|-------------|---------|--------|
| **Парсинг PDF** | Извлечение текста и таблиц | ✅ Готово |
| **Чанкинг** | Разбиение на части по 3000 символов | ✅ Готово |
| **Кэширование** | JSON кэш (ensure_ascii=False) | ✅ Готово |
| **Поиск** | Keyword-based по чанкам | ✅ Готово |
| **Logs** | Информативное логирование | ✅ Готово |
| **Error handling** | Обработка битых страниц | ✅ Готово |
| **Type hints** | Полная типизация кода | ✅ Готово |
| **Docstrings** | Русские комментарии | ✅ Готово |

---

## 🔧 Установка

### Требования системы

- Python 3.8+
- pip или conda
- ~50 МБ свободного места (для кэша JSON)

### Шаг 1: Установка зависимостей

```bash
# Перейдите в папку парсера
cd backend/ml/document_parser/

# Установите зависимости
pip install -r requirements.txt
```

### Шаг 2: Проверка установки

```bash
# Проверьте что pdfplumber установлен
python -c "import pdfplumber; print('✓ pdfplumber OK')"
```

### Шаг 3 (опционально): Добавьте в requirements.txt проекта

Если парсер интегрируется в subsidies-scoring:

```bash
# Добавьте в backend/requirements.txt:
cat backend/ml/document_parser/requirements.txt >> backend/requirements.txt
```

---

## 🚀 Быстрый старт

### Простейший пример

```python
from ml.document_parser.pdf_parser_kz import process_pdf

# Парсим PDF
chunks = process_pdf(
    pdf_path="norms_2025.pdf",
    doc_id="NORMS_2025",
    force=False  # Используем кэш если существует
)

# Вывод
print(f"✓ Получено {len(chunks)} чанков")
print(f"  Первый чанк: {chunks[0]['text'][:200]}...")
```

### Поиск в документе

```python
from ml.document_parser.pdf_parser_kz import SearchEngine

# Создаём поисковый движок
search = SearchEngine(chunks)

# Ищем релевантные фрагменты
results = search.find_relevant_chunks(
    query="пастбища скотоводство регион",
    top_k=5
)

# Выводим результаты
for chunk in results:
    print(f"Страница {chunk['page_start']}: {chunk['text'][:100]}...")
```

---

## 🏗️ Архитектура

### Компоненты системы

```
pdf_parser_kz.py
├── PDFExtractor          # Парсинг PDF
│   ├── _extract_page_content()
│   ├── _detect_paragraphs()
│   ├── _format_table()
│   └── parse()
│
├── TextChunker           # Чанкинг текста
│   ├── _is_table_boundary()
│   ├── _find_safe_split()
│   └── chunk()
│
├── CacheManager          # JSON кэширование
│   ├── save_chunks()
│   ├── load_chunks()
│   ├── is_cache_valid()
│   └── clear_cache()
│
├── SearchEngine          # Поиск по чанкам
│   ├── _tokenize()
│   ├── _score_chunk()
│   └── find_relevant_chunks()
│
└── process_pdf()         # Главная функция обработки
```

### Поток данных

```
PDF файл
  ↓
PDFExtractor.parse()
  ├─ Парсим постранично (буферизация по 10 страниц)
  ├─ Извлекаем текст + таблицы
  └─ Возвращаем raw_text
  ↓
TextChunker.chunk()
  ├─ Разбиваем по абзацам
  ├─ Формируем чанки (3000 символов, 200 overlap)
  └─ Возвращаем список чанков
  ↓
CacheManager.save_chunks()
  ├─ Сохраняем в JSON (ensure_ascii=False)
  └─ Кэш готов к повторному использованию
  ↓
SearchEngine.find_relevant_chunks()
  ├─ Токенизируем запрос
  ├─ Скорим чанки (совпадения слов)
  └─ Возвращаем top_k релевантных
```

### Размер данных

| Параметр | Значение | Примечание |
|----------|----------|-----------|
| Размер чанка | 3000 символов | Оптимум для LLM и RAG |
| Перекрытие | 200 символов | За связность между чанками |
| Батч обработки | 10 страниц | Постраничная память |
| Кэш формат | JSON | UTF-8, ensure_ascii=False |

---

## 📚 Примеры использования

### Пример 1: Полная обработка (рекомендуется)

```python
from ml.document_parser.pdf_parser_kz import process_pdf

# Полный конвейер: парсинг → чанкирование → кэширование
chunks = process_pdf(
    pdf_path="reglament_2025.pdf",
    doc_id="REG_2025_01",
    force=False,  # Если False — использует кэш
    cache_dir=Path("json_cache")  # Папка кэша
)

print(f"Чанков: {len(chunks)}")
print(f"Символов: {sum(c['char_count'] for c in chunks)}")
```

### Пример 2: Работа с компонентами отдельно

```python
from ml.document_parser.pdf_parser_kz import (
    PDFExtractor,
    TextChunker,
    CacheManager
)

# Шаг 1: Парсим
extractor = PDFExtractor(pdf_path="document.pdf", doc_id="DOC_2025")
parsed = extractor.parse(force=True)  # True = переопарсим

# Шаг 2: Чанкируем
chunker = TextChunker(chunk_size=3000, overlap=200)
chunks = chunker.chunk(
    raw_text=parsed['raw_text'],
    doc_id="DOC_2025",
    page_start=1
)

# Шаг 3: Сохраняем
cache_mgr = CacheManager()
cache_mgr.save_chunks(chunks, doc_id="DOC_2025", metadata=parsed)
```

### Пример 3: Поиск

```python
from ml.document_parser.pdf_parser_kz import SearchEngine

search = SearchEngine(chunks)

# Поиск с разными запросами
queries = [
    "пастбища скотоводство",
    "размер субсидии",
    "условия получения",
]

for query in queries:
    results = search.find_relevant_chunks(query, top_k=3)
    print(f"Запрос '{query}': {len(results)} результатов")
```

### Пример 4: Управление кэшем

```python
from ml.document_parser.pdf_parser_kz import CacheManager

cache_mgr = CacheManager()

# Проверить валидность кэша
is_valid = cache_mgr.is_cache_valid("DOC_2025", Path("document.pdf"))

# Загрузить кэш
chunks = cache_mgr.load_chunks("DOC_2025")

# Удалить кэш
cache_mgr.clear_cache("DOC_2025")
```

---

## 📖 API документация

### process_pdf()

**Главная функция обработки документа.**

```python
def process_pdf(
    pdf_path: str,
    doc_id: str,
    force: bool = False,
    cache_dir: Path = CACHE_DIR,
) -> List[Dict[str, Any]]:
    """
    Полная обработка: парсинг → чанкирование → кэширование.
    
    Args:
        pdf_path: Путь к PDF файлу
        doc_id: Уникальный идентификатор (например, "REG_2025")
        force: Если True, переопарсит даже если есть кэш
        cache_dir: Папка для JSON кэша
    
    Returns:
        Список чанков:
        [{
            'doc_id': str,
            'page_start': int,
            'chunk_index': int,
            'text': str,
            'char_count': int,
            'has_table': bool
        }, ...]
    
    Example:
        chunks = process_pdf('law.pdf', 'LAW_2025')
    """
```

### PDFExtractor

```python
class PDFExtractor:
    """Парсинг PDF документов."""
    
    def __init__(self, pdf_path: str, doc_id: str) -> None:
        """Инициализация с проверкой файла."""
    
    def parse(self, force: bool = False) -> Dict[str, Any]:
        """
        Парсит весь PDF постранично.
        
        Returns: {
            'doc_id': str,
            'total_pages': int,
            'raw_text': str,
            'parse_timestamp': str,
            'filename': str
        }
        """
```

### TextChunker

```python
class TextChunker:
    """Разбиение текста на чанки."""
    
    def __init__(
        self,
        chunk_size: int = 3000,
        overlap: int = 200
    ) -> None:
        """Инициализация с размерами."""
    
    def chunk(
        self,
        raw_text: str,
        doc_id: str,
        page_start: int = 1
    ) -> List[Dict[str, Any]]:
        """Разбивает текст на чанки с overlap."""
```

### CacheManager

```python
class CacheManager:
    """Управление JSON кэшем."""
    
    def save_chunks(
        self,
        chunks: List[Dict],
        doc_id: str,
        metadata: Optional[Dict] = None
    ) -> Path:
        """Сохраняет чанки в JSON."""
    
    def load_chunks(
        self,
        doc_id: str
    ) -> Optional[List[Dict]]:
        """Загружает чанки из кэша."""
    
    def is_cache_valid(
        self,
        doc_id: str,
        pdf_path: Path
    ) -> bool:
        """Проверяет актуальность кэша."""
    
    def clear_cache(self, doc_id: str) -> None:
        """Удаляет кэш."""
```

### SearchEngine

```python
class SearchEngine:
    """Поиск по чанкам."""
    
    def __init__(self, chunks: List[Dict]) -> None:
        """Инициализация с чанками."""
    
    def find_relevant_chunks(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Поиск релевантных чанков.
        
        Args:
            query: Поисковый запрос (естественный язык)
            top_k: Количество результатов
        
        Returns:
            Список чанков, отсортированный по релевантности DESC
        """
```

---

## ✅ Проверка качества

### Проверка 1: Парсинг большого документа

```python
# Протестировать на документе 100+ страниц
chunks = process_pdf("large_document_100pp.pdf", "LARGE_DOC")

# Проверки:
assert len(chunks) > 0, "Чанки не созданы"
assert all(len(c['text']) > 0 for c in chunks), "Пусто чанки"
assert all(c['char_count'] == len(c['text']) for c in chunks), "Размер неправильный"

print(f"✓ Парсинг большого документа OK ({len(chunks)} чанков)")
```

### Проверка 2: Таблицы не разбиты

```python
# Проверить что таблицы не разбиваются посередине
for chunk in chunks:
    if "[ТАБЛИЦА]" in chunk['text']:
        assert "[/ТАБЛИЦА]" in chunk['text'], "Таблица не закрыта в чанке"

print("✓ Таблицы целые (не разбиты)")
```

### Проверка 3: Кэш и поиск

```python
# Кэш работает
chunks1 = process_pdf("doc.pdf", "DOC", force=True)
chunks2 = process_pdf("doc.pdf", "DOC", force=False)  # из кэша
assert len(chunks1) == len(chunks2), "Кэш НЕ работает"

# Поиск работает
search = SearchEngine(chunks)
results = search.find_relevant_chunks("тестовый запрос", top_k=5)
assert len(results) <= 5, "Поиск вернул больше результатов чем top_k"

print("✓ Кэш и поиск OK")
```

### Проверка 4: Обработка ошибок

```python
# Несуществующий файл
try:
    process_pdf("nonexistent.pdf", "NONEXISTENT")
    assert False, "Должна быть ошибка"
except FileNotFoundError:
    print("✓ Ошибка FileNotFoundError обработана")

# Битый PDF
try:
    process_pdf("corrupted.pdf", "CORRUPTED")
except ValueError:
    print("✓ Ошибка ValueError обработана")
```

---

## 🔌 Интеграция в проект

### Вариант 1: Внутри subsidies-scoring (ТЕКУЩИЙ)

**Файлы уже в:**
```
backend/ml/document_parser/
├── pdf_parser_kz.py
├── examples_usage.py
├── requirements.txt
└── README.md (этот файл)
```

**Использование в коде:**

```python
# В backend/main.py или routers/documents.py

from ml.document_parser.pdf_parser_kz import process_pdf, SearchEngine

@app.post("/api/documents/parse")
async def parse_document(file: UploadFile = File(...)):
    """Парсит загруженный PDF."""
    
    # Сохраняем файл
    pdf_path = Path(f"data/documents/{file.filename}")
    
    # Парсим
    chunks = process_pdf(
        pdf_path=str(pdf_path),
        doc_id=file.filename.split(".")[0],
        force=False
    )
    
    return {
        "chunks_count": len(chunks),
        "total_chars": sum(c['char_count'] for c in chunks)
    }
```

### Вариант 2: Stand-alone библиотека

**Скопируйте в свой проект:**

```bash
cp -r backend/ml/document_parser/ /path/to/your/project/pdf_parser_kz/
```

**Затем используйте:**

```python
from pdf_parser_kz.pdf_parser_kz import process_pdf

chunks = process_pdf("document.pdf", "DOC_2025")
```

### Вариант 3: pip пакет (будущее)

```bash
# Установить как пакет (когда будет на PyPI)
pip install pdf-parser-kz

# Использовать
from pdf_parser_kz import process_pdf
```

---

## ❓ FAQ

### Q: Какой формат кэша используется?

A: JSON с `ensure_ascii=False` для поддержки русского и казахского языков.

```json
{
  "doc_id": "REG_2025",
  "chunks_count": 42,
  "total_chars": 125000,
  "cached_at": "2025-04-03T14:30:00",
  "metadata": {...},
  "chunks": [...]
}
```

### Q: Можно ли использовать OCR для скан-копий?

A: Текущая версия работает с текстовыми PDF. Для OCR нужна дополнительная интеграция (tesseract/paddleOCR).

### Q: Какой размер чанка оптимален?

A: 3000 символов — оптимум для LLM контекста и RAG систем.

### Q: Может ли парсер работать с казахским йиком?

A: Да! pdfplumber работает с Unicode, поддерживает русский и казахский.

### Q: Как переопарсить документ заново?

A: 

```python
chunks = process_pdf(pdf_path, doc_id, force=True)
```

### Q: Где сохраняется кэш?

A: По умолчанию в папке `json_cache/` рядом с парсером.

```python
# Или указать свою папку
chunks = process_pdf(pdf_path, doc_id, cache_dir=Path("my_cache"))
```

### Q: Какой размер PDF поддерживается?

A: Тестировалось на 100+ страниц. Память потребляется постранично, поэтому даже 500-страничные документы обрабатываются эффективно.

### Q: Работает ли поиск на казахском?

A: Да, keyword-based поиск работает с любым языком, поддерживаемым Unicode.

---

## 📝 Лицензия

Встроено в проект subsidies-scoring. В свободном использовании.

---

## 👨‍💻 Автор

**Eldar722**  
Production-ready PDF parser для РК нормативных актов  
Апрель 2025

---

## 📞 Поддержка

Если возникли вопросы или нашли ошибки:

1. Проверьте примеры в `examples_usage.py`
2. Посмотрите логи (logger.info/warning)
3. Убедитесь что pdf_path и doc_id правильно переданы
4. Проверьте кэш (может быть устарелым)

---

**Последнее обновление:** 3 апреля 2025 г.
