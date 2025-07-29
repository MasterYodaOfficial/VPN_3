# fastapi_app/main.py
from fastapi import FastAPI
from fastapi_app.api import subscription as api_router
from fastapi_app.routers import frontend as frontend_router


app = FastAPI(
    docs_url=None,           # отключает Swagger UI
    redoc_url=None,          # отключает ReDoc
    openapi_url=None,
    title="VPN Subscription Service"   # отключает OpenAPI спецификацию
)

# Подключаем роутер для API
app.include_router(api_router.router, prefix="/api/v1/subscription", tags=["Subscription"])

# Подключаем роутер для фронтенда
app.include_router(frontend_router.router)

@app.get("/")
def read_root():
    return {"message": "API is running"}