"""
__init__.py для package ml.document_parser

Экспортирует основные классы и функции парсера.
"""

from .pdf_parser_kz import (
    PDFExtractor,
    TextChunker,
    CacheManager,
    SearchEngine,
    process_pdf,
    logger,
)

__version__ = "1.0.0"
__author__ = "Eldar722"
__all__ = [
    "PDFExtractor",
    "TextChunker",
    "CacheManager",
    "SearchEngine",
    "process_pdf",
    "logger",
]
