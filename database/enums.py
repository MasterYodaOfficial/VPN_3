import enum

class PaymentMethod(str, enum.Enum):
    yookassa = "yookassa"
    crypto = "crypto"
    tg_stars = "tg_stars"

class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    LIMITED = "LIMITED"
    EXPIRED = "EXPIRED"
