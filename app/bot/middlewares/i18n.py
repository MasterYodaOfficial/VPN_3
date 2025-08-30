from aiogram.utils.i18n import I18n
from app.core.config import settings


i18n = I18n(path=settings.LOCALES_DIR, default_locale=settings.DEFAULT_LANGUAGE, domain="messages")


i18n_middleware = i18n.middleware()