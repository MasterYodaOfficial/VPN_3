from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy import event
from sqlalchemy.orm import declarative_base
from contextlib import asynccontextmanager
from app.core.config import settings  # используем config.py

# Создание движка
engine = create_async_engine(settings.DATABASE_URL)

# Включаем поддержку foreign_keys в SQLite
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Фабрика асинхронных сессий
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Базовый класс для моделей
Base = declarative_base()

# Асинхронный контекстный менеджер для aiogram
@asynccontextmanager
async def get_session():
    async with async_session_factory() as session:
        yield session

# FastAPI-совместимая зависимость
async def get_db_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
