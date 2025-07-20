import enum

class PaymentMethod(str, enum.Enum):
    yookassa = "yookassa"
    crypto = "crypto"
    # telegram_stars = "telegram_stars"
