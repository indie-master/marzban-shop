from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram import Dispatcher
from aiogram.types import CallbackQuery, LabeledPrice
from aiogram.utils.i18n import gettext as _
from aiogram.utils.i18n import lazy_gettext as __

import logging

from keyboards import get_payment_keyboard, get_pay_keyboard, get_xtr_pay_keyboard, get_manual_payment_keyboard

from utils import goods, yookassa, cryptomus

router = Router(name="callbacks-router") 

@router.callback_query(F.data.startswith("pay_kassa_"))
async def callback_payment_method_select(callback: CallbackQuery):
    await callback.message.delete()
    data = callback.data.replace("pay_kassa_", "")
    if data not in goods.get_callbacks():
        await callback.answer()
        return
    result = await yookassa.create_payment(
        callback.from_user.id, 
        data, 
        callback.message.chat.id, 
        callback.from_user.language_code)
    await callback.message.answer(
        _("To be paid - {amount}₽ ⬇️").format(
            amount=int(result['amount'])
        ),
        reply_markup=get_pay_keyboard(result['url']))
    await callback.answer()


@router.callback_query(F.data.startswith("pay_stars_"))
async def callback_payment_method_select(callback: CallbackQuery):
    await callback.message.delete()
    data = callback.data.replace("pay_stars_", "")
    if data not in goods.get_callbacks():
        await callback.answer()
        return
    logging.info(f"callback.data: {data}")
    good = goods.get(data)
    logging.info(f"good: {good}")
    price = good['price']['stars']
    months = good['months']
    prices = [LabeledPrice(label="XTR", amount=price)]  
    await callback.message.answer_invoice(
        title= _("Subscription for {amount} month").format(amount=months),
        currency="XTR",
        description=_("To be paid - {amount}⭐️ ⬇️").format(
            amount=int(price)
        ),
        prices=prices,
        provider_token="",
        payload=data,
        reply_markup=get_xtr_pay_keyboard(price)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("pay_crypto_"))
async def callback_payment_method_select(callback: CallbackQuery):
    await callback.message.delete()
    data = callback.data.replace("pay_crypto_", "")
    if data not in goods.get_callbacks():
        await callback.answer()
        return
    result = await cryptomus.create_payment(
        callback.from_user.id,
        data,
        callback.message.chat.id,
        callback.from_user.language_code)
    now = datetime.now()
    expire_date = (now + timedelta(minutes=60)).strftime("%d/%m/%Y, %H:%M")
    await callback.message.answer(
        _("To be paid - {amount}$ ⬇️").format(
            amount=result['amount'],
            date=expire_date
        ),
        reply_markup=get_pay_keyboard(result['url']))
    await callback.answer()


@router.callback_query(F.data.startswith("pay_manual_"))
async def callback_payment_manual(callback: CallbackQuery):
    await callback.message.delete()
    data = callback.data.replace("pay_manual_", "")
    if data not in goods.get_callbacks():
        await callback.answer()
        return
    await callback.message.answer(
        _("To pay, use one of the links below. After payment, press «I have paid»."),
        reply_markup=get_manual_payment_keyboard(data)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("manual_paid:"))
async def callback_manual_paid(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(_("We will check your payment soon. Thank you!"))


@router.callback_query(lambda c: c.data in goods.get_callbacks())
async def callback_payment_method_select(callback: CallbackQuery):
    await callback.message.delete()
    good = goods.get(callback.data)
    await callback.message.answer(text=_("Select payment method ⬇️"), reply_markup=get_payment_keyboard(good))
    await callback.answer()

def register_callbacks(dp: Dispatcher):
    dp.include_router(router)
