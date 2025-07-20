FROM python:3.11-slim

WORKDIR /app_bot

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./bot /app_bot/bot
COPY ./alembic /app_bot/alembic
COPY alembic.ini /app_bot
COPY ./database /app_bot/database
COPY ./core /app_bot/core

ENV PYTHONPATH=/app_bot

ENTRYPOINT ["/app_bot/bot/entrypoint.sh"]
