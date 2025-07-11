from aiogram.fsm.state import StatesGroup, State


class StepForm(StatesGroup):
    """
    Машина состояний передвижения в меню
    """

    # Profile движения
    COMMAND = State()

    CHOOSE_ACTION_PROFILE = State()  # Ожидание выбора действия (купить, продлить, пересобрать, активировать промо и т.п.)

    # Подписка
    SELECT_TARIFF = State()       # Выбор тарифа
    PAYMENT_METHOD = State()      # Выбор способа оплаты
    CONFIRM_PAYMENT = State()     # Ожидание подтверждения оплаты (или ожидание Webhook'а)

    # Промо
    ENTER_PROMO_CODE = State()    # Ввод промо-кода
    PROMO_ACTIVATION_RESULT = State()  # Показать результат активации

    # Обновление/пересборка
    REGENERATE_CONFIG = State()   # Подтверждение пересборки конфигов

    # Продление
    EXTEND_SUBSCRIPTION = State()  # Продление текущей подписки

    # Дополнительно (по желанию)
    VIEW_REFERRAL = State()       # Просмотр реферальной программы
    CONTACT_SUPPORT = State()     # Контакт с поддержкой