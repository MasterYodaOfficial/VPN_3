FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app_fast_api

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY ./database /app_fast_api/database
COPY ./fastapi_app /app_fast_api/fastapi_app
COPY ./core /app_fast_api/core

ENV PYTHONPATH=/app_fast_api

# Запускаем uvicorn при старте контейнера
CMD ["uvicorn", "fastapi_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
