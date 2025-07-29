from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.utils.messages import (profile_message, choose_subscription_text, choose_payment_message,
                                choose_tariff_message, payment_message, subscription_renewed_message,
                                subscription_purchased_with_config_message, trial_message)
from bot.utils.logger import logger
from bot.services.user_service import register_user_service
from bot.keyboards.inlines import (profile_buttons, active_subscriptions_buttons, payments_buttons,
                                   tariff_buttons, make_pay_link_button, tariff_buttons_buy)
from bot.utils.statesforms import StepForm
from bot.services.generator_subscriptions import (create_trial_sub, get_active_user_subscription,
                                                  activate_subscription, deactivate_only_subscription)
from database.crud.crud_tariff import get_active_tariffs
from bot.services.payment_service import (create_payment_service, get_payment_status, confirm_payment_service,
                                          error_payment_service)
from core.config import settings
import time
import asyncio



async def profile_command(message: Message, state: FSMContext):
    logger.info(f"{message.from_user.id} {message.from_user.first_name}")
    user_db = await register_user_service(message)
    await message.answer(
        text=profile_message.format(
            referral_earnings=user_db.balance,
            active_subscriptions_count=user_db.active_subscriptions_count
        ),
        reply_markup=profile_buttons(
            active_subscriptions_count=user_db.active_subscriptions_count,
            has_trial=user_db.has_trial
        )
    )
    await state.set_state(StepForm.CHOOSE_ACTION_PROFILE)

async def get_action_profile(call: CallbackQuery, state: FSMContext):

    """Принимает кнопки после команды профайл. Продлить подписку, купить подписку, пробная версия и так далее"""

    logger.info(f"{call.from_user.id}, {call.from_user.first_name}")
    if call.data.startswith("profile"):
        _, profile_action = call.data.split(":")
        if profile_action == "trial": # sub_name, hiddify_url, happ_url, logo_name
            await call.message.edit_text("Генерируем...")
            subscription = await create_trial_sub(call.from_user)
            if subscription:
                # Формируем две разные ссылки
                base_url = f"https://{settings.DOMAIN_API}/api/v1/subscription/{subscription.service_name}"
                hiddify_url = f"{base_url}?client=hiddify"
                happ_url = f"{base_url}?client=happ"

                await call.message.edit_text(
                    text=trial_message.format(
                        hiddify_url=hiddify_url,
                        happ_url=happ_url,
                        logo_name=settings.LOGO_NAME
                    ),
                    disable_web_page_preview=True
                )
            else:
                await call.message.edit_text("❌ Не удалось создать подписку. Попробуйте позже.")
            await state.clear()
        if profile_action == "new_sub":
            tariffs = await get_active_tariffs()
            await call.message.edit_text(
                text=choose_tariff_message,
                reply_markup=tariff_buttons_buy(tariffs)
            )
            await state.set_state(StepForm.SELECT_TARIFF_BUY)
        if profile_action == "extend":
            subs_list = await get_active_user_subscription(call.from_user)
            await call.message.edit_text(
                text=choose_subscription_text,
                reply_markup=active_subscriptions_buttons(subs_list)
            )
            await state.set_state(StepForm.CHOOSE_EXTEND_SUBSCRIPTION)
        if profile_action == "get_conf":
            pass
    else:
        await call.message.delete()

async def get_subscription_extend(call: CallbackQuery, state: FSMContext):
    """Получает кнопку с выбранным конфигом для продления предоставляет вариант тарифа"""
    if call.data.startswith("renew"):
        _, sub_id = call.data.split(":")
        await state.update_data(sub_id=int(sub_id))
        tariffs = await get_active_tariffs()
        await call.message.edit_text(
            text=choose_tariff_message,
            reply_markup=tariff_buttons(tariffs)
        )
        await state.set_state(StepForm.SELECT_TARIFF_EXTEND)
    else:
        await call.message.delete()

async def get_tariff_extend(call: CallbackQuery, state: FSMContext):
    """Принимает тариф для продления и предоставляет вариант оплаты"""
    if call.data.startswith("choose_tariff"):
        _, tariff_id = call.data.split(":")
        await state.update_data(tariff_id=int(tariff_id))
        await call.message.edit_text(
            text=choose_payment_message,
            reply_markup=payments_buttons()
        )
        await state.set_state(StepForm.PAYMENT_METHOD_EXTEND)
    else:
        await call.message.delete()

async def get_payment_method_extend(call: CallbackQuery, state: FSMContext):
    """Принимаем вариант оплаты формируем ссылку на оплату и ждем..."""
    if call.data.startswith("pay"):
        _, payment_method = call.data.split(":")
        data = await state.get_data()
        tariff_id = data["tariff_id"]
        sub_id = data["sub_id"]
        payment, tariff, subscription, pay_url = await create_payment_service(
            user=call.from_user,
            tariff_id=tariff_id,
            sub_id=sub_id,
            method=payment_method
        )
        await call.message.edit_text(
            text=payment_message.format(
                tariff_name=tariff.name,
                amount=tariff.price
            ),
            reply_markup=make_pay_link_button(pay_url)
        )
        await state.set_state(StepForm.CONFIRM_PAYMENT_EXTEND)
        timeout = time.time() + 7 * 60  # 7 минут ожидания
        while time.time() < timeout:
            status = await get_payment_status(payment)
            if status == "paid":
                await call.message.delete()
                await call.message.answer(subscription_renewed_message.format(
                    sub_name=subscription.service_name,
                    duration_days=tariff.duration_days
                ))
                await confirm_payment_service(payment.id)
                await state.clear()
                return
            current_state = await state.get_state()
            if current_state != StepForm.CONFIRM_PAYMENT_EXTEND:
                await call.message.delete()
                await call.message.answer("Оплата отменена")
                logger.info(f"cancel {call.from_user.id}, {call.from_user.first_name}")
                await error_payment_service(payment.id)
                return
            await asyncio.sleep(5)
    else:
        await call.message.delete()

async def get_tariff_buy(call: CallbackQuery, state: FSMContext):
    """Принимает тариф для оформления новой подписки"""
    if call.data.startswith("buy_tariff"):
        _, tariff_id = call.data.split(":")
        await state.update_data(tariff_id=int(tariff_id))
        await call.message.edit_text(
            text=choose_payment_message,
            reply_markup=payments_buttons()
        )
        await state.set_state(StepForm.PAYMENT_METHOD_BUY)
    else:
        await call.message.delete()

async def get_payment_method_buy(call: CallbackQuery, state: FSMContext):
    """Принимаем вариант оплаты для новой подписки формируем ссылку на оплату и ждем..."""
    if call.data.startswith("pay"):
        _, payment_method = call.data.split(":")
        data = await state.get_data()
        tariff_id = data["tariff_id"]
        payment, tariff, subscription, payment_url = await create_payment_service(
            user=call.from_user,
            tariff_id=tariff_id,
            method=payment_method
        )
        await call.message.edit_text(
            text=payment_message.format(
                tariff_name=tariff.name,
                amount=tariff.price
            ),
            reply_markup=make_pay_link_button(payment_url)
        )
        await state.set_state(StepForm.CONFIRM_PAYMENT_EXTEND)
        timeout = time.time() + 7 * 60  # 7 минут ожидания
        while time.time() < timeout:
            status = await get_payment_status(payment)
            if status == "paid":
                # В этом блоке:
                await activate_subscription(subscription.id)  # Эта функция должна возвращать объект подписки
                await confirm_payment_service(payment.id)
                await call.message.delete()

                # Формируем две разные ссылки
                base_url = f"https://{settings.DOMAIN_API}/api/v1/subscription/{subscription.service_name}"
                hiddify_url = f"{base_url}?client=hiddify"
                happ_url = f"{base_url}?client=happ"

                await call.message.answer(  # tariff_name, sub_name, hiddify_url, happ_url, logo_name
                    text=subscription_purchased_with_config_message.format(
                        tariff_name=tariff.name,
                        sub_name=subscription.service_name,
                        hiddify_url=hiddify_url,
                        happ_url=happ_url,
                        logo_name=settings.LOGO_NAME
                    ),
                    disable_web_page_preview=True
                )
                await state.clear()
                return
            current_state = await state.get_state()
            if current_state != StepForm.CONFIRM_PAYMENT_EXTEND:
                await deactivate_only_subscription(subscription.id)
                await call.message.delete()
                await call.message.answer("Оплата отменена")
                logger.info(f"cancel {call.from_user.id}, {call.from_user.first_name}")
                await error_payment_service(payment.id)
                return
            await asyncio.sleep(5)
    else:
        await call.message.delete()
