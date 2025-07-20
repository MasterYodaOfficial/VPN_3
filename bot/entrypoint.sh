#!/bin/bash
set -e

echo "Применение миграций..."
alembic upgrade head

echo "🚀 Запуск контейнера Telegram-бота..."

exec python /app_bot/bot/main.py

