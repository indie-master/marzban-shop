from datetime import datetime, timedelta

from aiogram import Router, F, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, LabeledPrice, Message
from aiogram.utils.i18n import gettext as _

import logging

from keyboards import (
    get_payment_keyboard,
    get_pay_keyboard,
    get_xtr_pay_keyboard,
    get_manual_payment_keyboard,
    get_manual_admin_keyboard,
)

    from db.methods import (
        add_manual_payment,
        get_latest_manual_payment_by_status,
        get_manual_payment,
        update_manual_payment,
    )
from utils import goods, yookassa, cryptomus, get_i18n_string
from utils.payments import process_successful_payment, format_expire
import glv


class ManualPaymentStates(StatesGroup):
    waiting_for_proof = State()


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
async def callback_payment_manual(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    data = callback.data.replace("pay_manual_", "")
    if data not in goods.get_callbacks():
        await callback.answer()
        return
    good = goods.get(data)
    payment_id = await add_manual_payment(
        callback.from_user.id,
        data,
        callback.message.chat.id,
        callback.from_user.language_code,
        callback.from_user.username,
        plan_name=good.get('title') or good.get('name'),
        amount=str(good.get('price', {}).get('ru') or good.get('price', {}).get('en') or ""),
    )
    logging.info("Manual payment %s created for user %s", payment_id, callback.from_user.id)
    await callback.message.answer(
        _("To pay, use one of the links below. After payment, press «I have paid»."),
        reply_markup=get_manual_payment_keyboard(payment_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("manual_paid_"))
async def callback_manual_paid(callback: CallbackQuery, state: FSMContext):
    payment_raw = callback.data.replace("manual_paid_", "")
    try:
        payment_id = int(payment_raw)
    except ValueError:
        await callback.answer()
        return
    payment = await get_manual_payment(payment_id)
    if payment is None or payment.status not in ["manual_pending"]:
        await callback.message.answer(_("This payment has already been processed. Please start a new payment if necessary."))
        await callback.answer()
        return
    await update_manual_payment(payment.id, status="manual_waiting_proof")
    logging.info("Manual payment %s awaiting proof from user %s", payment.id, callback.from_user.id)
    await state.set_state(ManualPaymentStates.waiting_for_proof)
    await state.update_data(payment_id=payment_id)
    await callback.message.answer(_("Please send a screenshot or receipt of your payment in reply to this message."))
    await callback.answer()


@router.message(ManualPaymentStates.waiting_for_proof)
async def handle_manual_proof(message: Message, state: FSMContext):
    data = await state.get_data()
    payment_raw = data.get("payment_id")
    payment = None
    if payment_raw is not None:
        try:
            payment_id = int(payment_raw)
            payment = await get_manual_payment(payment_id)
        except (TypeError, ValueError):
            payment = None
    if payment is None:
        payment = await get_latest_manual_payment_by_status(message.from_user.id, ["manual_waiting_proof", "manual_pending"])
    if payment is None or payment.status not in ["manual_pending", "manual_waiting_proof", "manual_review"]:
        await message.answer(_("This payment has already been processed. Please start a new payment if necessary."))
        await state.clear()
        return

    await update_manual_payment(
        payment.id,
        proof_message_id=message.message_id,
        proof_chat_id=message.chat.id,
        status="manual_review",
    )
    logging.info("Manual payment %s proof received from user %s", payment.id, message.from_user.id)

    admin_chat_id_raw = glv.config.get('TG_INFO_CHANEL')
    try:
        admin_chat_id = int(admin_chat_id_raw)
    except (TypeError, ValueError):
        admin_chat_id = admin_chat_id_raw
    admin_chat_id_db = admin_chat_id if isinstance(admin_chat_id, int) else None
    good = goods.get(payment.callback)
    if admin_chat_id:
        try:
            await glv.bot.copy_message(
                chat_id=admin_chat_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )
            username = payment.username if payment.username else message.from_user.full_name
            info_text = _(
                "Manual payment #{payment_id}\nUser: <a href=\"tg://user?id={user_id}\">{username}</a> (@{username_tag})\nPlan: {plan}\nAmount: {amount}"
            ).format(
                payment_id=payment.id,
                user_id=payment.tg_id,
                username=username,
                username_tag=payment.username or "—",
                plan=payment.plan_name or good.get('name', '') or good.get('title', ''),
                amount=payment.amount or good.get('price', {}).get('ru', ''),
            )
            admin_message = await glv.bot.send_message(
                admin_chat_id,
                info_text,
                reply_markup=get_manual_admin_keyboard(payment.id),
            )
            await update_manual_payment(
                payment.id,
                admin_message_id=admin_message.message_id,
                admin_chat_id=admin_chat_id_db,
            )
        except Exception as e:
            logging.warning("Failed to notify admins about manual payment %s: %s", payment.id, e)

    await message.answer(_("Thank you! We will check your payment soon."))
    await state.clear()


def _is_admin(user_id: int) -> bool:
    return not glv.config.get('ADMIN_IDS') or user_id in glv.config['ADMIN_IDS']


@router.callback_query(F.data.startswith("manual_confirm_"))
async def callback_manual_confirm(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer(_("You are not allowed to perform this action."), show_alert=True)
        return
    payment_raw = callback.data.replace("manual_confirm_", "")
    try:
        payment_id = int(payment_raw)
    except ValueError:
        await callback.answer()
        return
    payment = await get_manual_payment(payment_id)
    if payment is None:
        await callback.answer(_("Payment not found."), show_alert=True)
        return
    if payment.status in ["manual_confirmed", "manual_rejected"]:
        await callback.answer(_("This payment has already been processed."), show_alert=True)
        return
    if payment.status not in ["manual_review", "manual_waiting_proof", "manual_pending"]:
        await callback.answer(_("This payment has already been processed."), show_alert=True)
        return

    try:
        result = await process_successful_payment(
            payment.tg_id,
            payment.callback,
            payment.chat_id,
            payment.lang,
            send_user_message=False,
        )
        await update_manual_payment(payment.id, status="manual_confirmed")
    except Exception as e:
        logging.exception("Failed to process manual payment %s", payment_id)
        await update_manual_payment(payment.id, status="manual_error")
        logging.info("Manual payment %s manual_error by admin %s", payment.id, callback.from_user.id)
        if glv.config.get('TG_INFO_CHANEL'):
            await glv.bot.send_message(
                glv.config['TG_INFO_CHANEL'],
                _("⚠️ Failed to activate subscription for payment {payment_id}. Error: {error}").format(
                    payment_id=payment.id,
                    error=str(e),
                ),
            )
        await callback.answer(_("Failed to activate subscription."), show_alert=True)
        return

    logging.info("Manual payment %s manual_confirmed by admin %s", payment.id, callback.from_user.id)
    expire_text = format_expire(result.get('expire'))
    await glv.bot.send_message(
        payment.chat_id,
        get_i18n_string(
            "Payment confirmed ✅\nYour subscription is active until {date}.",
            payment.lang,
        ).format(date=expire_text),
    )
    if glv.config.get('TG_INFO_CHANEL'):
        await glv.bot.send_message(
            glv.config['TG_INFO_CHANEL'],
            _("✅ Payment {payment_id} confirmed, subscription active until {date}.").format(
                payment_id=payment.id,
                date=expire_text,
            ),
        )
    await callback.answer(_("Payment confirmed."), show_alert=True)


@router.callback_query(F.data.startswith("manual_reject_"))
async def callback_manual_reject(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer(_("You are not allowed to perform this action."), show_alert=True)
        return
    payment_raw = callback.data.replace("manual_reject_", "")
    try:
        payment_id = int(payment_raw)
    except ValueError:
        await callback.answer()
        return
    payment = await get_manual_payment(payment_id)
    if payment is None:
        await callback.answer(_("Payment not found."), show_alert=True)
        return
    if payment.status in ["manual_confirmed", "manual_rejected"]:
        await callback.answer(_("This payment has already been processed."), show_alert=True)
        return
    if payment.status not in ["manual_review", "manual_waiting_proof", "manual_pending"]:
        await callback.answer(_("This payment has already been processed."), show_alert=True)
        return

    await update_manual_payment(payment.id, status="manual_rejected")
    logging.info("Manual payment %s manual_rejected by admin %s", payment.id, callback.from_user.id)
    if glv.config.get('TG_INFO_CHANEL'):
        await glv.bot.send_message(
            glv.config['TG_INFO_CHANEL'],
            _("❌ Payment {payment_id} was rejected by administrator.").format(payment_id=payment.id),
        )

    user_text = get_i18n_string(
        "Payment not confirmed ❌\nPlease pay via the link in the bot and send a correct confirmation (screenshot or receipt).",
        payment.lang,
    )
    reply_markup = None
    good = goods.get(payment.callback)
    if good:
        reply_markup = get_payment_keyboard(good)
    await glv.bot.send_message(
        payment.chat_id,
        user_text,
        reply_markup=reply_markup,
    )
    await callback.answer(_("Payment rejected."), show_alert=True)


@router.callback_query(lambda c: c.data in goods.get_callbacks())
async def callback_payment_method_select(callback: CallbackQuery):
    await callback.message.delete()
    good = goods.get(callback.data)
    await callback.message.answer(text=_("Select payment method ⬇️"), reply_markup=get_payment_keyboard(good))
    await callback.answer()


def register_callbacks(dp: Dispatcher):
    dp.include_router(router)
