from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _

def get_xtr_pay_keyboard(price) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text=_('Pay'), pay = True)
    return builder.as_markup()