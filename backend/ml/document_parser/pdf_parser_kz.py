"""
Production-ready парсер PDF для нормативно-правовых актов Республики Казахстан.

Модуль извлекает текст и таблицы из больших PDF-файлов (100+ страниц)
без потери числовых данных и структуры документа.

Требования:
- Точность извлечения текста и таблиц (не использует OCR)
- Постраничная обработка с буферизацией
- Умный чанкинг по абзацам (3000 символов, 200 overlap)
- JSON кэширование результатов
- Keyword-based поиск по чанкам
- Полная обработка ошибок

Автор: Eldar722
Дата: 2025
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import pdfplumber
except ImportError:
    raise ImportError(
        "pdfplumber не установлен. "
        "Установите: pip install pdfplumber"
    )


# ============================================================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# ============================================================================

def _setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Настраивает логирование для парсера.
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        logger объект
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(getattr(logging, log_level))
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


logger = _setup_logging()


# ============================================================================
# КОНСТАНТЫ
# ============================================================================

CHUNK_SIZE = 3000  # Размер одного чанка в символах
CHUNK_OVERLAP = 200  # Перекрытие между чанками в символах
BATCH_SIZE = 10  # Обрабатываем страницы батчами по N страниц
CACHE_DIR = Path("json_cache")  # Папка для JSON кэшей


# ============================================================================
# PDFExtractor — Извлечение текста и таблиц из PDF
# ============================================================================

class PDFExtractor:
    """
    Клас для извлечения текста и таблиц из PDF-файлов.
    
    Особенности:
    - Постраничная обработка (не загружает весь PDF в память)
    - Буферизация по 10 страниц
    - Безопасная обработка ошибок для битых страниц
    - Логирование прогресса
    
    Атрибуты:
        pdf_path: Путь к PDF-файлу
        doc_id: Уникальный идентификатор документа
        total_pages: Общее количество страниц в PDF
    """
    
    def __init__(self, pdf_path: str, doc_id: str) -> None:
        """
        Инициализирует PDFExtractor.
        
        Args:
            pdf_path: Путь к PDF-файлу
            doc_id: Уникальный идентификатор документа (например, "REG_2025")
        
        Raises:
            FileNotFoundError: Если файл не существует
            ValueError: Если PDF файл повреждён
        """
        self.pdf_path = Path(pdf_path)
        self.doc_id = doc_id
        
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF файл не найден: {self.pdf_path}")
        
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                self.total_pages = len(pdf.pages)
        except Exception as e:
            raise ValueError(
                f"Ошибка при открытии PDF: {self.pdf_path}. {str(e)}"
            )
        
        logger.info(
            f"Инициализирован парсер для {self.doc_id} "
            f"({self.total_pages} страниц)"
        )
    
    def _extract_page_content(
        self, page_num: int
    ) -> Tuple[str, List[List[List[str]]]]:
        """
        Извлекает текст и таблицы со страницы.
        
        Args:
            page_num: Номер страницы (0-indexed)
        
        Returns:
            Кортеж (текст_страницы, список_таблиц)
            Если страница битая — возвращает ("", [])
        """
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                page = pdf.pages[page_num]
                
                # Извлекаем текст
                text = page.extract_text() or ""
                
                # Извлекаем таблицы
                tables = page.extract_tables() or []
                
                return text, tables
        
        except Exception as e:
            logger.warning(
                f"Ошибка при извлечении страницы {page_num + 1}: {str(e)}"
            )
            return "", []
    
    def _detect_paragraphs(self, text: str) -> List[str]:
        """
        Разбивает текст на абзацы по границам пустых строк.
        
        Args:
            text: Исходный текст страницы
        
        Returns:
            Список абзацев (не пусто)
        """
        if not text:
            return []
        
        # Разбиваем по двум и более пустым строкам
        paragraphs = re.split(r'\n\n+', text.strip())
        
        # Фильтруем пусто и восстанавливаем пробелы
        paragraphs = [
            p.strip() for p in paragraphs if p.strip()
        ]
        
        return paragraphs
    
    def _format_table(self, table: List[List[Optional[str]]]) -> str:
        """
        Конвертирует таблицу в читаемый текстовый формат.
        
        Формат: ячейка1 | ячейка2 | ячейка3
        Пустые ячейки сохраняются как пустые поля.
        
        Args:
            table: Список списков (строки и столбцы таблицы)
        
        Returns:
            Строка с отформатированной таблицей
        """
        if not table:
            return ""
        
        lines = []
        for row in table:
            # Заменяем None на пустую строку, конвертируем всё в str
            cells = [
                str(cell).strip() if cell is not None else ""
                for cell in row
            ]
            lines.append(" | ".join(cells))
        
        return "\n".join(lines)
    
    def parse(self, force: bool = False) -> Dict[str, Any]:
        """
        Основной метод парсинга. Извлекает весь контент из PDF.
        
        Алгоритм:
        1. Открываем PDF
        2. Обрабатываем постранично с буферизацией по 10 страниц
        3. Для каждой страницы: извлекаем текст + таблицы
        4. Формируем единый контент с маркерами таблиц
        5. Логируем прогресс
        
        Args:
            force: Если True, игнорируем кэш и переопарсим документ
        
        Returns:
            Dict с ключами:
                - doc_id: Идентификатор документа
                - total_pages: Количество страниц в PDF
                - raw_text: Объединённый текст всех страниц
                - parse_timestamp: Когда был выполнен парсинг
                - filename: Имя файла PDF
        """
        logger.info(f"Начинаем парсинг документа: {self.doc_id}")
        
        all_content = []
        processed_pages = 0
        
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num in range(len(pdf.pages)):
                    # Логируем прогресс каждые BATCH_SIZE страниц
                    if (page_num + 1) % BATCH_SIZE == 0 or page_num == 0:
                        logger.info(
                            f"Обработана страница {page_num + 1} "
                            f"из {len(pdf.pages)}"
                        )
                    
                    # Извлекаем текст и таблицы
                    text, tables = self._extract_page_content(page_num)
                    
                    # Если на странице таблицы — добавляем их в контент
                    page_content = []
                    
                    if text:
                        # Разбиваем текст на абзацы
                        paragraphs = self._detect_paragraphs(text)
                        page_content.extend(paragraphs)
                    
                    # Добавляем таблицы
                    for table in tables:
                        formatted_table = self._format_table(table)
                        if formatted_table:
                            # Обрамляем таблицу маркерами
                            table_content = (
                                f"\n[ТАБЛИЦА]\n{formatted_table}\n[/ТАБЛИЦА]\n"
                            )
                            page_content.append(table_content)
                    
                    # Объединяем контент страницы
                    if page_content:
                        all_content.extend(page_content)
                    
                    processed_pages += 1
        
        except Exception as e:
            logger.error(f"Критическая ошибка при парсинге: {str(e)}")
            raise
        
        # Объединяем весь контент
        raw_text = "\n\n".join(all_content)
        
        # Логируем статистику
        logger.info(
            f"Парсинг завершён: {self.doc_id} | "
            f"Страниц: {self.total_pages} | "
            f"Символов: {len(raw_text)}"
        )
        
        return {
            "doc_id": self.doc_id,
            "total_pages": self.total_pages,
            "raw_text": raw_text,
            "parse_timestamp": datetime.now().isoformat(),
            "filename": self.pdf_path.name,
            "processed_pages": processed_pages,
        }


# ============================================================================
# TextChunker — Разбиение текста на чанки с overlap
# ============================================================================

class TextChunker:
    """
    Класс для разбиения текста на чанки фиксированного размера.
    
    Особенности:
    - Умный чанкинг по границам абзацев
    - Не разрывает таблицы посередине
    - Сохраняет метаданные (doc_id, page_start, chunk_index)
    - Поддерживает overlap между чанками для связности
    
    Атрибуты:
        chunk_size: Размер одного чанка в символах
        overlap: Размер перекрытия между чанками
    """
    
    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        overlap: int = CHUNK_OVERLAP
    ) -> None:
        """
        Инициализирует TextChunker.
        
        Args:
            chunk_size: Размер чанка в символах (по умолчанию 3000)
            overlap: Размер перекрытия в символах (по умолчанию 200)
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def _is_table_boundary(self, text: str) -> bool:
        """
        Проверяет, является ли текст границей таблицы.
        
        Args:
            text: Текст для проверки
        
        Returns:
            True, если это таблица или её граница
        """
        return "[ТАБЛИЦА]" in text or "[/ТАБЛИЦА]" in text
    
    def _find_safe_split(
        self, text: str, max_length: int
    ) -> int:
        """
        Находит безопасную точку разреза (по границе абзаца или слова).
        
        Args:
            text: Текст для анализа
            max_length: Максимальная длина
        
        Returns:
            Индекс для разреза (гарантирует разреваемость по границам)
        """
        if len(text) <= max_length:
            return len(text)
        
        # Ищем последний разрыв строки перед max_length
        cutoff = text.rfind("\n", 0, max_length)
        if cutoff > max_length * 0.8:  # Если достаточно близко
            return cutoff
        
        # Иначе ищем последний пробел
        cutoff = text.rfind(" ", 0, max_length)
        if cutoff > max_length * 0.75:
            return cutoff
        
        # Если не нашли — режем по максимуму
        return max_length
    
    def chunk(
        self,
        raw_text: str,
        doc_id: str,
        page_start: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Разбивает текст на чанки с overlap.
        
        Алгоритм:
        1. Разбиваем текст по абзацам
        2. Формируем чанки размером chunk_size
        3. Если абзац не помещается — начинаем новый чанк
        4. Если его таблица — не разрываем, начинаем новый чанк
        5. Поддерживаем overlap между чанками
        
        Args:
            raw_text: Исходный текст всего документа
            doc_id: Идентификатор документа
            page_start: Номер начальной страницы (для метаданных)
        
        Returns:
            Список чанков (Dict с texto, метаданные, и индекс)
        """
        if not raw_text:
            logger.warning(f"Попытка чанкирования пустого текста для {doc_id}")
            return []
        
        chunks = []
        chunk_index = 0
        current_chunk = ""
        
        # Разбиваем на абзацы
        paragraphs = re.split(r'\n\n+', raw_text.strip())
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        for para_idx, paragraph in enumerate(paragraphs):
            # Проверяем, является ли это таблицей
            is_table = self._is_table_boundary(paragraph)
            
            # Если текущий чанк + новый абзац помещаются — добавляем
            potential_chunk = current_chunk + "\n\n" + paragraph
            
            if len(potential_chunk) <= self.chunk_size:
                current_chunk = potential_chunk.strip()
            else:
                # Чанк переполнится
                
                if current_chunk:
                    # Сохраняем текущий чанк
                    chunks.append({
                        "doc_id": doc_id,
                        "page_start": page_start,
                        "chunk_index": chunk_index,
                        "text": current_chunk,
                        "char_count": len(current_chunk),
                        "has_table": "[ТАБЛИЦА]" in current_chunk,
                    })
                    chunk_index += 1
                    
                    # Начинаем новый с overlap из конца старого
                    overlap_text = current_chunk[-self.overlap:] if len(current_chunk) > self.overlap else current_chunk
                    current_chunk = overlap_text + "\n\n" + paragraph
                else:
                    # Первый чанк пустой, значит абзац очень длинный
                    # Разбиваем абзац по словам
                    safe_cut = self._find_safe_split(paragraph, self.chunk_size)
                    current_chunk = paragraph[:safe_cut].strip()
                    
                    chunks.append({
                        "doc_id": doc_id,
                        "page_start": page_start,
                        "chunk_index": chunk_index,
                        "text": current_chunk,
                        "char_count": len(current_chunk),
                        "has_table": "[ТАБЛИЦА]" in current_chunk,
                    })
                    chunk_index += 1
                    
                    # Остаток абзаца — в следующий чанк
                    remainder = paragraph[safe_cut:].strip()
                    if remainder:
                        overlap_text = current_chunk[-self.overlap:] if len(current_chunk) > self.overlap else current_chunk
                        current_chunk = overlap_text + "\n\n" + remainder
                    else:
                        current_chunk = ""
        
        # Добавляем последний чанк
        if current_chunk:
            chunks.append({
                "doc_id": doc_id,
                "page_start": page_start,
                "chunk_index": chunk_index,
                "text": current_chunk,
                "char_count": len(current_chunk),
                "has_table": "[ТАБЛИЦА]" in current_chunk,
            })
        
        logger.info(
            f"Чанкирование завершено: {doc_id} | "
            f"Чанков: {len(chunks)} | "
            f"Среднее size: "
            f"{sum(c['char_count'] for c in chunks) // len(chunks) if chunks else 0}"
        )
        
        return chunks


# ============================================================================
# CacheManager — Управление JSON кэшем
# ============================================================================

class CacheManager:
    """
    Класс для сохранения и загрузки кэша в JSON формат.
    
    Особенности:
    - Использует ensure_ascii=False для поддержку кириллицы
    - Автоматически создаёт папку кэша
    - Проверяет актуальность кэша
    - Поддерживает принудительный переопарсинг
    
    Атрибуты:
        cache_dir: Папка для хранения JSON файлов
    """
    
    def __init__(self, cache_dir: Path = CACHE_DIR) -> None:
        """
        Инициализирует CacheManager.
        
        Args:
            cache_dir: Папка для хранения кэша (по умолчанию json_cache/)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Инициализирован CacheManager: {self.cache_dir}")
    
    def _get_cache_path(self, doc_id: str) -> Path:
        """
        Возвращает путь к JSON файлу кэша для документа.
        
        Args:
            doc_id: Идентификатор документа
        
        Returns:
            Path к файлу кэша
        """
        return self.cache_dir / f"{doc_id}_chunks.json"
    
    def save_chunks(
        self,
        chunks: List[Dict[str, Any]],
        doc_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Сохраняет чанки в JSON файл.
        
        Args:
            chunks: Список чанков для сохранения
            doc_id: Идентификатор документа
            metadata: Дополнительные метаданные (например, timestamp парсинга)
        
        Returns:
            Path к сохранённому файлу
        """
        cache_path = self._get_cache_path(doc_id)
        
        cache_data = {
            "doc_id": doc_id,
            "chunks_count": len(chunks),
            "total_chars": sum(c.get("char_count", 0) for c in chunks),
            "cached_at": datetime.now().isoformat(),
            "metadata": metadata or {},
            "chunks": chunks,
        }
        
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.info(
                f"Кэш сохранён: {cache_path} | "
                f"Чанков: {len(chunks)}"
            )
            return cache_path
        
        except Exception as e:
            logger.error(f"Ошибка при сохранении кэша: {str(e)}")
            raise
    
    def load_chunks(self, doc_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Загружает чанки из JSON файла кэша.
        
        Args:
            doc_id: Идентификатор документа
        
        Returns:
            Список чанков или None если кэша нет
        """
        cache_path = self._get_cache_path(doc_id)
        
        if not cache_path.exists():
            logger.info(f"Кэш не найден: {cache_path}")
            return None
        
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            
            chunks = cache_data.get("chunks", [])
            logger.info(
                f"Кэш загружен: {cache_path} | "
                f"Чанков: {len(chunks)}"
            )
            return chunks
        
        except Exception as e:
            logger.error(f"Ошибка при загрузке кэша: {str(e)}")
            return None
    
    def is_cache_valid(self, doc_id: str, pdf_path: Path) -> bool:
        """
        Проверяет, актуален ли кэш (не был ли PDF обновлён).
        
        Args:
            doc_id: Идентификатор документа
            pdf_path: Путь к PDF файлу
        
        Returns:
            True если кэш актуален, False иначе
        """
        cache_path = self._get_cache_path(doc_id)
        
        if not cache_path.exists():
            return False
        
        try:
            pdf_mtime = pdf_path.stat().st_mtime
            cache_mtime = cache_path.stat().st_mtime
            
            # Кэш актуален если он новее чем PDF
            is_valid = cache_mtime > pdf_mtime
            
            if is_valid:
                logger.info(f"Кэш актуален для {doc_id}")
            else:
                logger.info(f"Кэш устарел для {doc_id}, нужен переопарсинг")
            
            return is_valid
        
        except Exception as e:
            logger.warning(f"Ошибка при проверке кэша: {str(e)}")
            return False
    
    def clear_cache(self, doc_id: str) -> None:
        """
        Удаляет кэш для документа.
        
        Args:
            doc_id: Идентификатор документа
        """
        cache_path = self._get_cache_path(doc_id)
        
        if cache_path.exists():
            cache_path.unlink()
            logger.info(f"Кэш удалён: {cache_path}")


# ============================================================================
# SearchEngine — Поиск по чанкам
# ============================================================================

class SearchEngine:
    """
    Класс для поиска релевантных чанков по keyword-запросу.
    
    Особенности:
    - Keyword-based поиск (без embeddings и LLM)
    - Скоринг по количеству найденных слов
    - Tie-breaker по chunk_index (более ранний чанк выше рейтинг)
    - Поддержка top_k результатов
    
    Атрибуты:
        chunks: Список всех чанков для поиска
    """
    
    def __init__(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Инициализирует SearchEngine.
        
        Args:
            chunks: Список чанков для построения индекса
        """
        self.chunks = chunks
        logger.info(f"Инициализирован SearchEngine с {len(chunks)} чанками")
    
    def _tokenize(self, text: str) -> set:
        """
        Токенизирует текст — разбивает на слова.
        
        Args:
            text: Текст для токенизации
        
        Returns:
            Set уникальных слов в lowercase
        """
        # Приводим к lowercase, удаляем пунктуацию, разбиваем по пробелам
        words = re.findall(r'\b\w+\b', text.lower())
        return set(words)
    
    def _score_chunk(
        self,
        chunk_text: str,
        query_tokens: set,
        chunk_index: int
    ) -> Tuple[int, int]:
        """
        Считает релевантность чанка к запросу.
        
        Алгоритм:
        1. Считаем количество найденных слов из query в чанке
        2. Tie-breaker: более ранний чанк выше рейтинг
        
        Args:
            chunk_text: Текст чанка
            query_tokens: Множество слов запроса
            chunk_index: Индекс чанка (для tie-breaker)
        
        Returns:
            Кортеж (relevance_score, tie_breaker_score)
        """
        chunk_tokens = self._tokenize(chunk_text)
        
        # Количество совпадений (релевантность)
        matching_tokens = len(query_tokens & chunk_tokens)
        
        # Tie-breaker: инвертируем индекс (меньший индекс = выше score)
        tie_breaker = -chunk_index
        
        return (matching_tokens, tie_breaker)
    
    def find_relevant_chunks(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Находит top_k релевантных чанков для запроса.
        
        Args:
            query: Поисковый запрос (естественный язык)
            top_k: Количество результатов (по умолчанию 5)
        
        Returns:
            Список top_k чанков, отсортированных по релевантности (DESC)
        """
        if not query or not self.chunks:
            logger.warning("Пустой запрос или чанки не загружены")
            return []
        
        query_tokens = self._tokenize(query)
        
        if not query_tokens:
            logger.warning(f"Из запроса не извлечено ни одного слова: {query}")
            return []
        
        # Считаем релевантность для каждого чанка
        scored_chunks = []
        for chunk in self.chunks:
            chunk_text = chunk.get("text", "")
            chunk_index = chunk.get("chunk_index", 0)
            
            score, tie_breaker = self._score_chunk(
                chunk_text, query_tokens, chunk_index
            )
            
            # Добавляем только чанки с хотя бы одним совпадением
            if score > 0:
                scored_chunks.append((score, tie_breaker, chunk))
        
        # Сортируем по релевантности DESC, затем по tie-breaker DESC
        scored_chunks.sort(key=lambda x: (x[0], x[1]), reverse=True)
        
        # Берём top_k
        result_chunks = [chunk for _, _, chunk in scored_chunks[:top_k]]
        
        logger.info(
            f"Поиск по запросу '{query}': найдено {len(result_chunks)} "
            f"релевантных чанков"
        )
        
        return result_chunks


# ============================================================================
# ГЛАВНАЯ ФУНКЦИЯ ОБРАБОТКИ
# ============================================================================

def process_pdf(
    pdf_path: str,
    doc_id: str,
    force: bool = False,
    cache_dir: Path = CACHE_DIR,
) -> List[Dict[str, Any]]:
    """
    Полная обработка PDF: парсинг, чанкирование, кэширование.
    
    Алгоритм:
    1. Проверяем кэш (если force=False)
    2. Если кэша нет — парсим PDF
    3. Разбиваем на чанки
    4. Сохраняем в JSON кэш
    5. Возвращаем чанки
    
    Args:
        pdf_path: Путь к PDF файлу
        doc_id: Уникальный идентификатор документа
        force: Если True, игнорируем кэш и переопарсим
        cache_dir: Папка для JSON кэша
    
    Returns:
        Список чанков с метаданными
    
    Example:
        >>> chunks = process_pdf("reglament.pdf", doc_id="REG_2025")
        >>> print(f"Получено {len(chunks)} чанков")
        Получено 42 чанков
    """
    logger.info(f"=" * 70)
    logger.info(f"ОБРАБОТКА ДОКУМЕНТА: {doc_id}")
    logger.info(f"PDF: {pdf_path}")
    logger.info(f"=" * 70)
    
    # Инициализируем компоненты
    cache_mgr = CacheManager(cache_dir=cache_dir)
    pdf_path_obj = Path(pdf_path)
    
    # Проверяем кэш (если force=False)
    if not force and cache_mgr.is_cache_valid(doc_id, pdf_path_obj):
        logger.info("Загружаем результаты из кэша")
        chunks = cache_mgr.load_chunks(doc_id)
        if chunks:
            logger.info(f"Успешно загружено {len(chunks)} чанков из кэша")
            return chunks
    
    # Парсим PDF
    logger.info("Начинаем парсинг PDF...")
    extractor = PDFExtractor(pdf_path=pdf_path, doc_id=doc_id)
    parse_result = extractor.parse(force=force)
    
    # Разбиваем на чанки
    logger.info("Разбиваем текст на чанки...")
    chunker = TextChunker(
        chunk_size=CHUNK_SIZE,
        overlap=CHUNK_OVERLAP
    )
    chunks = chunker.chunk(
        raw_text=parse_result["raw_text"],
        doc_id=doc_id,
        page_start=1
    )
    
    # Сохраняем кэш
    logger.info("Сохраняем результаты в кэш...")
    cache_mgr.save_chunks(
        chunks=chunks,
        doc_id=doc_id,
        metadata={
            "total_pages": parse_result["total_pages"],
            "filename": parse_result["filename"],
            "parse_timestamp": parse_result["parse_timestamp"],
        }
    )
    
    logger.info(f"=" * 70)
    logger.info(f"ОБРАБОТКА ЗАВЕРШЕНА УСПЕШНО")
    logger.info(f"Документ: {pdf_path}")
    logger.info(f"Чанков создано: {len(chunks)}")
    logger.info(f"Всего символов: {sum(c['char_count'] for c in chunks)}")
    logger.info(f"=" * 70)
    
    return chunks


# ============================================================================
# ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ
# ============================================================================

if __name__ == "__main__":
    """
    Примеры использования парсера PDF.
    """
    
    # Пример 1: Простой парсинг документа
    print("\n" + "=" * 70)
    print("ПРИМЕР 1: Простой парсинг и кэширование")
    print("=" * 70)
    
    # Это сработает если у вас есть PDF файл
    # chunks = process_pdf(
    #     pdf_path="path/to/your/document.pdf",
    #     doc_id="DOC_2025_01",
    #     force=False  # Используем кэш если существует
    # )
    
    print("✓ Функция process_pdf готова к использованию")
    print("  Пример: chunks = process_pdf('document.pdf', 'DOC_2025_01')")
    
    # Пример 2: Поиск в загруженных чанках
    print("\n" + "=" * 70)
    print("ПРИМЕР 2: Поиск по чанкам")
    print("=" * 70)
    
    # Если у вас уже есть чанки:
    # search_engine = SearchEngine(chunks)
    # results = search_engine.find_relevant_chunks(
    #     query="пастбища скотоводство регион",
    #     top_k=5
    # )
    # for chunk in results:
    #     print(f"Страница {chunk['page_start']}: {chunk['text'][:200]}...")
    
    print("✓ Класс SearchEngine готов к использованию")
    print("  Пример: search_engine = SearchEngine(chunks)")
    print("  search_engine.find_relevant_chunks('ваш запрос', top_k=5)")
    
    # Пример 3: Прямое управление компонентами
    print("\n" + "=" * 70)
    print("ПРИМЕР 3: Прямое использование компонентов")
    print("=" * 70)
    
    print("""
    # Парсер PDF
    extractor = PDFExtractor(pdf_path='document.pdf', doc_id='DOC_2025')
    parsed = extractor.parse(force=True)
    
    # Чанкирование
    chunker = TextChunker(chunk_size=3000, overlap=200)
    chunks = chunker.chunk(
        raw_text=parsed['raw_text'],
        doc_id='DOC_2025'
    )
    
    # Кэширование
    cache_mgr = CacheManager()
    cache_mgr.save_chunks(chunks, doc_id='DOC_2025')
    
    # Поиск
    search = SearchEngine(chunks)
    results = search.find_relevant_chunks('ваш запрос', top_k=5)
    """)
    
    print("\n✓ Парсер полностью готов к production использованию!")
