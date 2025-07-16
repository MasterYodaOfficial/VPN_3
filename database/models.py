from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, ForeignKey, Float, Text, func, Enum
)
from sqlalchemy.orm import relationship, declarative_base
from database.enums import PaymentMethod

Base = declarative_base()



class User(Base):
    __tablename__ = "users"

    telegram_id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    balance = Column(Integer, default=0)

    # Реферальная система
    inviter_id = Column(Integer, ForeignKey("users.telegram_id"), nullable=True)
    inviter = relationship("User", remote_side=[telegram_id], back_populates="invited_users")
    invited_users = relationship("User", back_populates="inviter")

    referral_code = Column(String, unique=True, index=True)
    is_admin = Column(Boolean, default=False)
    has_trial = Column(Boolean, default=True)

    # Связи
    subscriptions = relationship("Subscription", back_populates="user")
    payments = relationship("Payment", back_populates="user")

    @property
    def active_subscriptions(self):
        return [sub for sub in self.subscriptions if sub.is_active]

    @property
    def total_subscriptions_count(self) -> int:
        return len(self.subscriptions)

    @property
    def active_subscriptions_count(self) -> int:
        return len(self.active_subscriptions)

    @property
    def invited_users_count(self) -> int:
        return len(self.invited_users)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, ForeignKey("users.telegram_id"))
    start_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)

    service_name = Column(String, nullable=False)
    uuid_name = Column(String, nullable=False)

    tariff_id = Column(Integer, ForeignKey("tariffs.id"), nullable=True)

    # Промокод (если использован)
    promo_id = Column(Integer, ForeignKey("promocodes.id"), nullable=True)

    # Связи
    user = relationship("User", back_populates="subscriptions")
    tariff = relationship("Tariff", back_populates="subscriptions")
    configs = relationship(
        "Config",
        back_populates="subscription",
        cascade="all, delete-orphan"
    )
    promo = relationship("Promocode", back_populates="subscriptions")
    payments = relationship("Payment", back_populates="subscription")


class Config(Base):
    __tablename__ = "configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subscription_id = Column(
        Integer,
        ForeignKey("subscriptions.id", ondelete="CASCADE")
    )

    server_id = Column(Integer, ForeignKey("servers.id"))

    config_data = Column(Text, nullable=False)  # Сгенерированный конфиг (vmess/vless и т.п.)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    subscription = relationship("Subscription", back_populates="configs")
    server = relationship("Server", back_populates="configs")


class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    api_url = Column(String, nullable=False)

    link_ip = Column(String, nullable=True)
    login = Column(String, nullable=True)
    password = Column(String, nullable=True)

    max_clients = Column(Integer)
    current_clients = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    # Связи
    configs = relationship("Config", back_populates="server")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.telegram_id"))

    amount = Column(Integer, nullable=False)
    currency = Column(String, default="RUB")
    status = Column(String, default="pending")  # pending, success, failed
    method = Column(Enum(PaymentMethod), nullable=False)  # yookassa, cripto
    external_payment_id = Column(String, unique=True, nullable=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    tariff_id = Column(Integer, ForeignKey("tariffs.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="payments")
    subscription = relationship("Subscription", back_populates="payments")
    tariff = relationship("Tariff", back_populates="payments")


class Promocode(Base):
    __tablename__ = "promocodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True, nullable=False)
    discount_percent = Column(Integer, nullable=False)  # Например: 10 = 10%

    usage_limit = Column(Integer, default=1)
    used_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    subscriptions = relationship("Subscription", back_populates="promo")


class Tariff(Base):
    __tablename__ = "tariffs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)  # Название: "1 месяц", "6 месяцев" и т.п.
    duration_days = Column(Integer, nullable=False)  # Сколько дней длится подписка
    price = Column(Integer, nullable=False)
    currency = Column(String, default="RUB")
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


    subscriptions = relationship("Subscription", back_populates="tariff")
    payments = relationship("Payment", back_populates="tariff")






