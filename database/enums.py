import enum

class PaymentMethod(str, enum.Enum):
    yookassa = "yookassa"
    crypto = "crypto"
    tg_stars = "tg_stars"
