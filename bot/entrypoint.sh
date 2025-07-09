#!/bin/bash
set -e

echo "🚀 Запуск контейнера Telegram-бота..."
exec python /app_bot/bot/main.py

