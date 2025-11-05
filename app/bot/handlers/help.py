from aiogram.types import Message, CallbackQuery
from app.bot.keyboards.inlines import help_menu_buttons, install_menu_buttons
from aiogram.fsm.context import FSMContext
from aiogram.utils.i18n import gettext as _
from app.core.config import settings
from app.logger import logger

async def help_command(message: Message, state: FSMContext):
    """Обработчик команды /help"""
    await state.clear()
    await message.answer(
        text=_("help_main_message"),
        reply_markup=help_menu_buttons()
    )


async def navigate_help_menu(call: CallbackQuery):
    action = call.data.split(":")[1]
    try:
        if action == "install":
            await call.message.edit_text(
                text=_("choose_sys"),
                reply_markup=install_menu_buttons()
            )
        elif action == "faq":
            await call.message.edit_text(
                text=_("help_faq_message").format(
                    owner=settings.OWNER_NAME
                ),
                reply_markup=install_menu_buttons()
            )
    except Exception as ex:
        logger.debug(ex)
    await call.answer()


async def show_install_guide(call: CallbackQuery):
    platform = call.data.split(":")[1]

    guides = {
        "android": _("help_android_vless"),
        "ios": _("help_ios_vless"),
        "desktop": _("help_desktop_vless")
    }
    try:
        if platform in guides:
            await call.message.edit_text(
                text=guides[platform].format(
                    video=settings.INSTRUCTION_LINK
                ),
                reply_markup=install_menu_buttons(),
                disable_web_page_preview=True
            )
        elif platform == "back_to_help":
            await call.message.edit_text(
                text=_("help_main_message"),
                reply_markup=help_menu_buttons(),
                disable_web_page_preview=True
            )
    except Exception as ex:
        logger.debug(ex)
    await call.answer()