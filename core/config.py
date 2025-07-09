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
    BOT_NAME: str = os.getenv("BOT_NAME")
    SUPPORT_NAME: str = os.getenv("SUPPORT_NAME", "Support_VPN")
    OWNER_NAME:str = os.getenv("OWNER_NAME")
    ADMINS = os.getenv("ADMINS", None)
    ADMIN_IDS = []
    if ADMINS:
        ADMIN_IDS = [int(uid.strip()) for uid in ADMINS.split(",") if uid.strip()]

    # Промо-доступ
    TRIAL_DAYS: int = int(os.getenv("TRIAL_DAYS", 0))



# Создаём синглтон
settings = Settings()
