from aiogram.fsm.state import StatesGroup, State


class StepForm(StatesGroup):
    """
    Машина состояний передвижения в меню
    """

    # Profile движения
    COMMAND = State()

    CHOOSE_ACTION_PROFILE = State()  # Ожидание выбора действия (купить, продлить, активировать промо и т.п.)

    # Продление подписки
    CHOOSE_EXTEND_SUBSCRIPTION = State() # Выбор подписки для продления
    PAYMENT_METHOD_EXTEND = State()      # Выбор способа оплаты
    SELECT_TARIFF_EXTEND = State()       # Выбор тарифа для продления
    CONFIRM_PAYMENT_EXTEND = State()     # Ожидание подтверждения оплаты (или ожидание Webhook'а)

    # Покупка новой подписки
    SELECT_TARIFF_BUY = State()       # Выбор нового тарифа
    PAYMENT_METHOD_BUY = State()  # Выбор способа оплаты нового тарифа

    # Админская рассылка
    WAITING_BROADCAST_MESSAGE = State() # Ожидание сообщения от админа
    CONFIRM_BROADCAST = State()         # Ожидание подтверждения рассылки

    # Подписка
    # SELECT_TARIFF = State()       # Выбор тарифа

    # CONFIRM_PAYMENT = State()     # Ожидание подтверждения оплаты (или ожидание Webhook'а)
    #
    # # Промо
    # ENTER_PROMO_CODE = State()    # Ввод промо-кода
    # PROMO_ACTIVATION_RESULT = State()  # Показать результат активации
    #
    # # Обновление/пересборка
    # REGENERATE_CONFIG = State()   # Подтверждение пересборки конфигов
    #
    # # Продление
    #
    # # Дополнительно (по желанию)
    # VIEW_REFERRAL = State()       # Просмотр реферальной программы
    # CONTACT_SUPPORT = State()     # Контакт с поддержкой