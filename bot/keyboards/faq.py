from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _

import glv


def get_faq_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    links = [
        (
            glv.config.get('FAQ_PRIVACY_ENABLED'),
            glv.config.get('FAQ_PRIVACY_URL'),
            _("Privacy policy"),
        ),
        (
            glv.config.get('FAQ_TERMS_ENABLED'),
            glv.config.get('FAQ_TERMS_URL'),
            _("User agreement"),
        ),
        (
            glv.config.get('FAQ_RULES_ENABLED'),
            glv.config.get('FAQ_RULES_URL'),
            _("Rules"),
        ),
        (
            glv.config.get('FAQ_OFFER_ENABLED'),
            glv.config.get('FAQ_OFFER_URL'),
            _("Offer"),
        ),
    ]

    for enabled, url, title in links:
        if enabled and url:
            builder.row(InlineKeyboardButton(text=title, url=url))

    builder.row(
        InlineKeyboardButton(
            text=_("⬅️ Назад"),
            callback_data="back:main",
        )
    )

    return builder.as_markup()
