from __future__ import annotations
from datetime import datetime
from typing import List, Optional, Self

from sqlalchemy import (
    String, ForeignKey, func, MetaData, select
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship, selectinload

from .enums import PaymentMethod
from database.session import get_session
# --- Настройка базового класса с конвенцией именования ---
# Это стандартная практика, чтобы ключи и индексы в БД
# именовались одинаково и предсказуемо.
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_`%(constraint_name)s`",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
Base = declarative_base(metadata=MetaData(naming_convention=naming_convention))


class User(Base):
    __tablename__ = "users"

    # --- Колонки с типами ---
    telegram_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[Optional[str]]
    link: Mapped[Optional[str]]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    balance: Mapped[int] = mapped_column(default=0)
    inviter_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.telegram_id"))
    referral_code: Mapped[str] = mapped_column(unique=True, index=True)
    is_admin: Mapped[bool] = mapped_column(default=False)
    has_trial: Mapped[bool] = mapped_column(default=True)
    had_first_purchase: Mapped[bool] = mapped_column(default=False)

    # --- Связи (relationships) с типами ---
    inviter: Mapped[Optional["User"]] = relationship(remote_side=[telegram_id], back_populates="invited_users")
    invited_users: Mapped[List["User"]] = relationship(back_populates="inviter")
    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    payments: Mapped[List["Payment"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    @property
    def active_subscriptions(self) -> List["Subscription"]:
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

    # --- CRUD МЕТОДЫ ДЛЯ МОДЕЛИ USER ---

    @classmethod
    async def get_by_telegram_id(cls, session: AsyncSession, telegram_id: int) -> Optional[Self]:
        """Получает пользователя со всеми его связанными данными по telegram_id."""
        stmt = (
            select(cls)
            .options(
                selectinload(cls.subscriptions),
                selectinload(cls.invited_users),
                selectinload(cls.inviter),
            )
            .where(cls.telegram_id == telegram_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_referral_code(cls, session: AsyncSession, referral_code: str) -> Optional[Self]:
        """Находит пользователя по его реферальному коду."""
        stmt = select(cls).where(cls.referral_code == referral_code)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def create(cls, session: AsyncSession, **kwargs) -> Self:
        """Создает нового пользователя."""
        user = cls(**kwargs)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    async def update(self, session: AsyncSession, **kwargs) -> Self:
        """Обновляет поля текущего объекта пользователя."""
        for key, value in kwargs.items():
            setattr(self, key, value)
        await session.commit()
        await session.refresh(self)
        return self


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"))
    start_date: Mapped[datetime] = mapped_column(server_default=func.now())
    end_date: Mapped[datetime]
    is_active: Mapped[bool] = mapped_column(default=True)
    remnawave_uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    remnawave_short_uuid: Mapped[str] = mapped_column(String(48), unique=True, index=True)
    subscription_name: Mapped[str]
    subscription_url: Mapped[str]
    tariff_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tariffs.id"))
    promo_id: Mapped[Optional[int]] = mapped_column(ForeignKey("promocodes.id"))

    user: Mapped["User"] = relationship(back_populates="subscriptions")
    tariff: Mapped[Optional["Tariff"]] = relationship(back_populates="subscriptions")
    promo: Mapped[Optional["Promocode"]] = relationship(back_populates="subscriptions")
    payments: Mapped[List["Payment"]] = relationship(back_populates="subscription", cascade="all, delete-orphan")

    @classmethod
    async def create(cls, session: AsyncSession, **kwargs) -> Self:
        subscription = cls(**kwargs)
        session.add(subscription)
        await session.commit()
        await session.refresh(subscription)
        return subscription

    @classmethod
    async def get_by_id(cls, session: AsyncSession, sub_id: int) -> Optional[Self]:
        return await session.get(cls, sub_id)

    async def update(self, session: AsyncSession, **kwargs) -> Self:
        """Обновляет поля текущей подписки."""
        for key, value in kwargs.items():
            setattr(self, key, value)
        await session.commit()
        await session.refresh(self)
        return self


class Payment(Base):
    __tablename__ = "payments_gateways"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"))
    amount: Mapped[int]
    currency: Mapped[str] = mapped_column(default="RUB")
    status: Mapped[str] = mapped_column(default="pending")
    method: Mapped[PaymentMethod]
    external_payment_id: Mapped[Optional[str]] = mapped_column(unique=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id"))
    tariff_id: Mapped[int] = mapped_column(ForeignKey("tariffs.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="payments_gateways")
    subscription: Mapped["Subscription"] = relationship(back_populates="payments_gateways")
    tariff: Mapped["Tariff"] = relationship(back_populates="payments_gateways")

    @classmethod
    async def create(cls, session: AsyncSession, **kwargs) -> Self:
        payment = cls(**kwargs)
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        return payment

    @classmethod
    async def get_by_id_with_relations(cls, session: AsyncSession, payment_id: int) -> Optional[Self]:
        stmt = (
            select(cls).where(cls.id == payment_id).options(
                selectinload(cls.subscription).selectinload(Subscription.user),
                selectinload(cls.tariff),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_external_id(cls, session: AsyncSession, external_id: str) -> Optional[Self]:
        stmt = select(cls).where(cls.external_payment_id == external_id).options(
            selectinload(cls.subscription),
            selectinload(cls.tariff),
            selectinload(cls.user)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


class Promocode(Base):
    __tablename__ = "promocodes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(unique=True)
    discount_percent: Mapped[int]
    usage_limit: Mapped[int] = mapped_column(default=1)
    used_count: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="promo")


class Tariff(Base):
    __tablename__ = "tariffs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]
    duration_days: Mapped[int]
    price: Mapped[int]
    currency: Mapped[str] = mapped_column(default="RUB")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="tariff")
    payments: Mapped[List["Payment"]] = relationship(back_populates="tariff")

    @classmethod
    async def get_active(cls, session: AsyncSession) -> List[Self]:
        stmt = select(cls).where(cls.is_active == True).order_by(cls.price)
        result = await session.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def get_by_id(cls, session: AsyncSession, tariff_id: int) -> Optional[Self]:
        return await session.get(cls, tariff_id)