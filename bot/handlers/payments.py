from aiogram import Router, Dispatcher, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, PreCheckoutQuery
from aiogram.utils.i18n import gettext as _
from types import SimpleNamespace

from db.methods import get_links_by_tg_id
from services.user_links import ensure_user_link
from utils import goods
from utils.payments import process_successful_payment

router = Router(name="payment-router")

@router.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery):
    if goods.get(query.invoice_payload) is None:
        return await query.answer(_("Error: Invalid product type.\nPlease contact the support team."), ok = False)
    await query.answer(ok=True)

@router.message(F.successful_payment)
async def success_payment(message: Message, state: FSMContext):
    payload = message.successful_payment.invoice_payload
    state_data = await state.get_data()
    if state_data.get("selected_good") == payload:
        marzban_usernames = state_data.get("selected_marzban_users", [])
    else:
        links = await get_links_by_tg_id(message.from_user.id)
        if not links:
            primary_link = await ensure_user_link(message.from_user)
            links = [primary_link] if primary_link else []
        marzban_usernames = [links[0].marzban_user] if links else []

    payment_ctx = SimpleNamespace(
        id=None,
        tg_id=message.from_user.id,
        username=message.from_user.username,
        callback=payload,
        chat_id=message.chat.id,
        lang=message.from_user.language_code,
    )
    await process_successful_payment(payment_ctx, marzban_usernames)
    await state.update_data(selected_good=None, selected_marzban_users=[])
    
def register_payments(dp: Dispatcher):
    dp.include_router(router)