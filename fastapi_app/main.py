# fastapi_app/main.py
from fastapi import FastAPI
from fastapi_app.api import subscription

app = FastAPI(
    docs_url=None,           # отключает Swagger UI
    redoc_url=None,          # отключает ReDoc
    openapi_url=None         # отключает OpenAPI спецификацию
)

# Подключаем роут
app.include_router(subscription.router, prefix="/subscription", tags=["subscription"])
