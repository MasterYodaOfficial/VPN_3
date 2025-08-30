from aiogram.types import Message, CallbackQuery
from app.bot.keyboards.inlines import help_menu_buttons, install_menu_buttons

from aiogram.utils.i18n import gettext as _


async def help_command(message: Message):
    """Обработчик команды /help"""
    await message.answer(
        text=_("help_main_message"),
        reply_markup=help_menu_buttons()
    )


async def navigate_help_menu(call: CallbackQuery):
    action = call.data.split(":")[1]

    if action == "install":
        await call.message.edit_text(
            # "Выберите вашу операционную систему:"
            text=_("choose_sys"),
            reply_markup=install_menu_buttons()
        )
    elif action == "faq":
        await call.message.edit_text(
            text=_("help_faq_message"),
            reply_markup=install_menu_buttons()
        )
    await call.answer()


async def show_install_guide(call: CallbackQuery):
    platform = call.data.split(":")[1]

    guides = {
        "android": _("help_android_vless"),
        "ios": _("help_ios_vless"),
        "desktop": _("help_desktop_vless")
    }

    if platform in guides:
        await call.message.edit_text(
            text=guides[platform],
            reply_markup=install_menu_buttons(),
            disable_web_page_preview=True
        )
    elif platform == "back_to_help":
        await call.message.edit_text(
            text=_("help_main_message"),
            reply_markup=help_menu_buttons(),
            disable_web_page_preview=True
        )
    await call.answer()