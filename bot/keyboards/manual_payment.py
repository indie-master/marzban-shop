from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _

import glv


def get_manual_payment_keyboard(payment_id) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()

    if glv.config.get('PAY_SBER_URL'):
        builder.button(
            text=_('Pay via Sber'),
            url=glv.config['PAY_SBER_URL']
        )

    if glv.config.get('PAY_TBANK_URL'):
        builder.button(
            text=_('Pay via T-Bank'),
            url=glv.config['PAY_TBANK_URL']
        )

    builder.button(
        text=_('I have paid'),
        callback_data=f"manual_paid:{payment_id}"
    )

    builder.adjust(2, 1)
    return builder.as_markup()
