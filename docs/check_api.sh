#!/bin/bash

# Скрипт проверки скорости ответа API (Промпт 5.3)
# Использование: ./check_api.sh [https://ваш-railway.app]
# По умолчанию тестирует локальный сервер

BASE=${1:-"http://localhost:8000"}

echo "🔍 Проверка производительности API на сервере: $BASE"
echo "----------------------------------------------------"

check() {
  # Запрашиваем код ответа и полное время (в секундах), с таймаутом в 10с
  RESULT=$(curl -s -o /dev/null -w "%{http_code} %{time_total}" -m 10 "$BASE$1")
  
  if [ -z "$RESULT" ]; then
    echo "❌ $1: Сервер недоступен (Connection Refused / Timeout)"
    return
  fi
  
  STATUS=$(echo "$RESULT" | awk '{print $1}')
  TIME=$(echo "$RESULT" | awk '{print $2}')
  
  # Форматируем красивый вывод
  if [ "$STATUS" -eq 200 ]; then
    echo "✅ $1: HTTP $STATUS за ${TIME}s"
  else
    echo "⚠️ $1: HTTP $STATUS за ${TIME}s (Возможна ошибка)"
  fi
}

check "/health"
check "/api/metrics"
check "/api/shortlist?top_n=20"
check "/api/producers"
check "/api/fairness"
check "/api/map/regions"

echo "----------------------------------------------------"
echo "🏁 Тест завершён. Все эндпоинты дольше 0.5s (500ms) требуют оптимизации."
