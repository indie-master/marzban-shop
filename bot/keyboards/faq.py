from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _

import glv


def get_faq_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    links = [
        (glv.config.get('FAQ_RULES_URL'), _("Правила")),
        (glv.config.get('FAQ_PRIVACY_URL'), _("Политика конфиденциальности")),
        (glv.config.get('FAQ_TERMS_URL'), _("Пользовательское соглашение")),
    ]
    for url, title in links:
        if url:
            builder.row(InlineKeyboardButton(text=title, url=url))
    builder.row(InlineKeyboardButton(text=_("О сервисе"), callback_data="faq:about"))

    builder.row(
        InlineKeyboardButton(
            text=_("⬅️ Назад"),
            callback_data="back:main",
        )
    )

    return builder.as_markup()
