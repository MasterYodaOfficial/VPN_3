FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем ВЕСЬ код проекта
COPY . .

# Устанавливаем PYTHONPATH, чтобы импорты из корня работали
ENV PYTHONPATH=/app

# Миграции
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]

# Запускаем FastAPI-приложение (которое теперь управляет и ботом)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]