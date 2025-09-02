# app/bot/handlers/language.py

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.bot.keyboards.inlines import language_selection_buttons
from aiogram.utils.i18n import gettext as _, I18n
from database.models import User
from database.session import get_session

router = Router(name=__name__)


@router.message(Command("language"))
async def language_command(message: Message, state: FSMContext):
    """Отправляет сообщение с предложением сменить язык."""
    await state.clear()
    await message.answer(
        _("language-selection-message"),
        reply_markup=language_selection_buttons()
    )


@router.callback_query(F.data.startswith("set_lang:"))
async def set_language_callback(call: CallbackQuery, i18n: I18n):
    """Обрабатывает нажатие на кнопку выбора языка."""
    lang_code = call.data.split(":")[1]

    if lang_code not in i18n.available_locales:
        return await call.answer("This language is not supported.", show_alert=True)

    async with get_session() as session:
        user = await User.get_by_telegram_id(session, call.from_user.id)
        if user:
            await user.update(session, language_code=lang_code)

    # Устанавливаем новую локаль для текущего запроса, чтобы ответ пришел на новом языке
    i18n.current_locale = lang_code

    await call.message.edit_text(_("language-changed-message"))
    await call.answer()  # Показываем "часики", чтобы кнопка перестала грузиться