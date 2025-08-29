import os
from typing import List, Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from pydantic_settings import BaseSettings, SettingsConfigDict
from remnawave import RemnawaveSDK


class Settings(BaseSettings):
    """
    Класс для управления настройками приложения с использованием Pydantic.
    Автоматически читает переменные из .envex файла, проверяет их типы и предоставляет
    удобный объектно-ориентированный доступ.
    """
    # --- Настройки путей ---
    SUBSCRIPTION_PATH: str = "/api/v1/subscription"
    TEMPLATES_PATHS: str = "app/templates"
    PAYMENTS_PATH: str = "/payments"

    # --- Database ---
    DATABASE_URL: str  # Pydantic автоматически проверит, что эта переменная есть

    # --- Telegram Bot ---
    BOT_TOKEN: str
    BOT_NAME: str
    SUPPORT_NAME: str
    SUPPORT_URL: str
    OWNER_NAME: str
    ADMIN_IDS: List[int]

    # --- Business Logic ---
    TRIAL_DAYS: int = 3
    REFERRAL_COMMISSION_PERCENT: int = 50

    # --- Payments ---
    YOOKASSA_TOKEN: Optional[str] = None
    YOOKASSA_SHOP_ID: Optional[str] = None
    CRYPTO_TOKEN: Optional[str] = None
    TELEGRAM_STARS: bool = False
    RUB_PER_STAR: float = 1.79

    # --- Infrastructure ---
    DOMAIN_API: str
    LOGO_NAME: str

    # --- Remnawave API ---
    REMNAWAVE_BASE_URL: str
    REMNAWAVE_TOKEN: str
    REMNAWAVE_WEBHOOK_SECRET: Optional[str] = None

    # --- Application State Objects (не из .env, будут инициализированы ниже) ---
    # Мы объявляем их здесь, чтобы иметь доступ через settings.BOT, settings.REMNA_SDK
    BOT: Optional[Bot] = None
    DP_BOT: Optional[Dispatcher] = None
    REMNA_SDK: Optional[RemnawaveSDK] = None

    # Конфигурация Pydantic: указываем, что нужно читать из файла .env
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), '.env'),
        env_file_encoding='utf-8',
        extra='ignore'  # Игнорировать лишние переменные в .env
    )

    def __init__(self, **values):
        """
        Инициализатор, который сначала загружает переменные из .envex,
        а затем инициализирует сложные объекты, такие как Bot и SDK.
        """
        super().__init__(**values)

        # --- Инициализация сложных объектов ПОСЛЕ загрузки всех переменных ---

        # 1. Инициализация Aiogram Bot и Dispatcher
        self.BOT = Bot(token=self.BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
        self.DP_BOT = Dispatcher()
        self.REMNA_SDK = RemnawaveSDK(
            base_url=self.REMNAWAVE_BASE_URL,
            token=self.REMNAWAVE_TOKEN,
        )

    @property
    def WEBHOOK_BOT_PATH(self) -> str:
        return f"/bot/webhook/{self.BOT_TOKEN}"

    @property
    def WEBHOOK_BOT_URL(self) -> str:
        return f"https://{self.DOMAIN_API}{self.WEBHOOK_BOT_PATH}"

    @property
    def WEBHOOK_SECRET(self) -> str:
        return self.BOT_TOKEN.split(":")[0]

    # ... другие свойства, если они понадобятся ...


# --- Создаем ЕДИНСТВЕННЫЙ экземпляр настроек для всего приложения ---
settings = Settings()