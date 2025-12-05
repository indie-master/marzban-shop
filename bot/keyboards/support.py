from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _

import glv


def get_support_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    support_link = glv.config.get('SUPPORT_LINK')
    if support_link:
        builder.row(InlineKeyboardButton(text=_("✍️ Write to support"), url=support_link))

    builder.row(
        InlineKeyboardButton(
            text=_("⬅️ Назад"),
            callback_data="back:main",
        )
    )
    return builder.as_markup()
