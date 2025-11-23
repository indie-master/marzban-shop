from aiogram import Router, Dispatcher, F
from aiogram.types import Message, PreCheckoutQuery
from aiogram.utils.i18n import gettext as _

from utils import goods
from utils.payments import process_successful_payment

router = Router(name="payment-router")

@router.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery):
    if goods.get(query.invoice_payload) is None:
        return await query.answer(_("Error: Invalid product type.\nPlease contact the support team."), ok = False)
    await query.answer(ok=True)

@router.message(F.successful_payment)
async def success_payment(message: Message):
    await process_successful_payment(
        message.from_user.id,
        message.successful_payment.invoice_payload,
        message.chat.id,
        message.from_user.language_code,
    )
    
def register_payments(dp: Dispatcher):
    dp.include_router(router)