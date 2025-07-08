import os
from dotenv import load_dotenv
from pathlib import Path

# Загружаем переменные из .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    # База данных
    DATABASE_URL: str = os.getenv("DATABASE_URL")

    # Telegram Bot
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")




# Создаём синглтон
settings = Settings()
