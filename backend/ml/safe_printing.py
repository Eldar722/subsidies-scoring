"""
safe_printing.py — безопасная печать с fallback на ASCII для Windows консоли.

Решает проблему: UnicodeEncodeError при выводе UTF-8 символов на Windows.
"""

import sys
from typing import Any, Optional

# Unicode символы → ASCII fallback
UNICODE_MAP = {
    "✓": "[OK]",
    "✗": "[FAIL]",
    "✅": "[OK]",
    "❌": "[ERROR]",
    "⚠": "[WARN]",
    "🔧": "[CONFIG]",
    "📊": "[DATA]",
    "📈": "[METRICS]",
    "💾": "[SAVE]",
    "📋": "[INFO]",
    "🚀": "[START]",
    "═": "=",
    "─": "-",
    "└": "|",
    "┘": "|",
    "├": "|",
    "│": "|",
    "↑": "^",
    "↓": "v",
    "→": "->",
    "←": "<-",
    "Δ": "D",
}


def safe_print(*args, **kwargs):
    """Print с автоматическим fallback на ASCII для Windows.
    
    Если консоль не поддерживает UTF-8, заменяет символы на ASCII.
    """
    try:
        # Попытка печати как есть
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # Fallback: заменить проблемные символы
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                safe_str = arg
                for unicode_char, ascii_char in UNICODE_MAP.items():
                    safe_str = safe_str.replace(unicode_char, ascii_char)
                safe_args.append(safe_str)
            else:
                safe_args.append(arg)
        
        # Печать с заменяющей строкой
        print(*safe_args, **kwargs)


def format_metric(name: str, value: float, unit: str = "") -> str:
    """Форматировать метрику безопасно."""
    try:
        if unit == "%":
            return f"{name}: {value:.1f}%"
        else:
            return f"{name}: {value:.4f} {unit}"
    except (ValueError, TypeError):
        return f"{name}: {value}"


def print_section(title: str):
    """Печать заголовка секции безопасно."""
    safe_print("\n" + "=" * 70)
    safe_print(f"  {title}")
    safe_print("=" * 70)


def print_success(msg: str):
    """Печать успеха."""
    safe_print(f"✓ {msg}")


def print_error(msg: str):
    """Печать ошибки."""
    safe_print(f"✗ {msg}")


def print_warning(msg: str):
    """Печать предупреждения."""
    safe_print(f"[WARN] {msg}")


def print_info(msg: str):
    """Печать информации."""
    safe_print(f"[INFO] {msg}")


if __name__ == "__main__":
    # Test
    print_section("Testing Safe Printing")
    print_success("Unicode fallback working")
    print_error("Test error message")
    print_warning("Test warning message")
    print_info("Test info message")
    
    safe_print("\nMetric examples:")
    safe_print(format_metric("ROC-AUC", 0.8100))
    safe_print(format_metric("Improvement", 8.7, "%"))
