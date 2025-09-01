from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.logger import logger
from app.bot.keyboards.inlines import (profile_buttons, active_subscriptions_buttons, payments_buttons,
                                       tariff_buttons, make_pay_link_button, tariff_buttons_buy,
                                       get_config_webapp_button, user_subscriptions_webapp_buttons)
from app.bot.utils.statesforms import StepForm
from app.core.config import settings
from app.services.subscription_service import subscription_service
from app.services.tariff_service import tariff_service
from app.services.user_service import user_service
from app.services.payment_service import payment_service
from aiogram.utils.i18n import gettext as _


async def profile_command(message: Message, state: FSMContext):
    logger.bind(source="bot").info(f"{message.from_user.id} {message.from_user.first_name}")
    user_db = await user_service.register_or_update_user(message)
    await message.answer(
        text=_("profile_message").format(
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

    logger.bind(source="bot").info(f"{call.from_user.id}, {call.from_user.first_name}")
    if call.data.startswith("profile"):
        _pass, profile_action = call.data.split(":")
        if profile_action == "trial":
            await call.message.edit_text(_("generating_subs"))
            subscription = await subscription_service.create_trial_subscription(call.from_user)
            if subscription is None:
                await call.message.edit_text(_("error_subs_create"))
                await state.clear()
                return
            subscription_url = subscription.subscription_url
            await call.message.edit_text(
                text=_("trial_message").format(
                    logo_name=settings.LOGO_NAME
                ),
                reply_markup=get_config_webapp_button(subscription_url)
            )
            await state.clear()
        if profile_action == "new_sub":
            tariffs = await tariff_service.get_active_tariffs()
            await call.message.edit_text(
                text=_("choose_tariff_message"),
                reply_markup=tariff_buttons_buy(tariffs)
            )
            await state.set_state(StepForm.SELECT_TARIFF_BUY)
        if profile_action == "extend":
            subs_list = await subscription_service.get_active_user_subscriptions(call.from_user)
            if not subs_list:
                await call.message.edit_text(
                    #
                    text=_("not_subs")
                )
                await state.clear()
                return
            await call.message.edit_text(
                text=_("choose_subscription_text_extend"),
                reply_markup=active_subscriptions_buttons(subs_list)
            )
            await state.set_state(StepForm.CHOOSE_EXTEND_SUBSCRIPTION)
        if profile_action == "get_conf":
            subs_list = await subscription_service.get_active_user_subscriptions(call.from_user)
            if not subs_list:
                await call.message.edit_text(
                    text=_("not_subs")
                )
                await state.clear()
                return
            await call.message.edit_text(
                text=_("active_configs_list_message"),
                reply_markup=user_subscriptions_webapp_buttons(subs_list)
            )
            await state.clear()
            return
    else:
        await call.message.delete()

async def get_subscription_extend(call: CallbackQuery, state: FSMContext):
    """Получает кнопку с выбранным конфигом для продления предоставляет вариант тарифа"""
    if call.data.startswith("renew"):
        _pass, sub_id = call.data.split(":")
        await state.update_data(sub_id=int(sub_id))
        tariffs = await tariff_service.get_active_tariffs()
        await call.message.edit_text(
            text=_("choose_tariff_message"),
            reply_markup=tariff_buttons(tariffs)
        )
        await state.set_state(StepForm.SELECT_TARIFF_EXTEND)
    else:
        await call.message.delete()

async def get_tariff_extend(call: CallbackQuery, state: FSMContext):
    """Принимает тариф для продления и предоставляет вариант оплаты"""
    if call.data.startswith("choose_tariff"):
        _pass, tariff_id = call.data.split(":")
        await state.update_data(tariff_id=int(tariff_id))
        await call.message.edit_text(
            text=_("choose_payment_message"),
            reply_markup=payments_buttons()
        )
        await state.set_state(StepForm.PAYMENT_METHOD_EXTEND)
    else:
        await call.message.delete()

async def get_payment_method_extend(call: CallbackQuery, state: FSMContext):
    """Принимаем вариант оплаты формируем ссылку на оплату и ждем..."""
    if call.data.startswith("pay"):
        _pass, payment_method = call.data.split(":")
        data = await state.get_data()
        tariff_id = data["tariff_id"]
        sub_id = data["sub_id"]
        payment_data = await payment_service.create_payment_link(
            user_tg=call.from_user,
            tariff_id=tariff_id,
            method_str=payment_method,
            sub_id_to_extend=sub_id
        )
        if not payment_data:
            await call.answer(_("error_payment"), show_alert=True)
            await state.clear()
            return
        payment, tariff, subscription, payment_url = payment_data
        await call.message.edit_text(
            text=_("payment_message").format(
                tariff_name=tariff.name,
                amount=tariff.price
            ),
            reply_markup=make_pay_link_button(payment_url)
        )
        await state.clear()
    else:
        await call.message.delete()

async def get_tariff_buy(call: CallbackQuery, state: FSMContext):
    """Принимает тариф для оформления новой подписки"""
    if call.data.startswith("buy_tariff"):
        _pass, tariff_id = call.data.split(":")
        await state.update_data(tariff_id=int(tariff_id))
        await call.message.edit_text(
            text=_("choose_payment_message"),
            reply_markup=payments_buttons()
        )
        await state.set_state(StepForm.PAYMENT_METHOD_BUY)
    else:
        await call.message.delete()

async def get_payment_method_buy(call: CallbackQuery, state: FSMContext):
    """Принимаем вариант оплаты для новой подписки формируем ссылку на оплату и ждем..."""
    if call.data.startswith("pay"):
        _pass, payment_method = call.data.split(":")
        data = await state.get_data()
        tariff_id = data["tariff_id"]
        payment_data = await payment_service.create_payment_link(
            user_tg=call.from_user,
            tariff_id=tariff_id,
            method_str=payment_method
        )
        if not payment_data:
            await call.answer(_("error_payment"), show_alert=True)
            await state.clear()
            return
        payment, tariff, subscription, payment_url = payment_data
        await call.message.edit_text(
            text=_("payment_message").format(
                tariff_name=tariff.name,
                amount=tariff.price
            ),
            reply_markup=make_pay_link_button(payment_url)
        )
        await state.clear()
    else:
        await call.message.delete()
