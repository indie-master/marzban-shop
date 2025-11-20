from datetime import datetime, timedelta

from aiogram import Router, F, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, LabeledPrice, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.i18n import gettext as _

import logging

from keyboards import (
    get_payment_keyboard,
    get_pay_keyboard,
    get_xtr_pay_keyboard,
    get_manual_payment_keyboard,
    get_manual_admin_keyboard,
    get_buy_menu_keyboard,
    get_main_menu_keyboard,
)

from db.methods import (
    add_manual_payment,
    add_manual_payment_link,
    get_latest_manual_payment_by_status,
    get_links_by_tg_id,
    get_manual_payment,
    get_manual_payment_links,
    update_manual_payment,
)
from services.user_links import ensure_user_link
from utils import goods, yookassa, cryptomus, get_i18n_string
from utils.payments import process_successful_payment
import glv


class ManualPaymentStates(StatesGroup):
    waiting_for_proof = State()


class PaymentSelectionStates(StatesGroup):
    selecting_subscriptions = State()


router = Router(name="callbacks-router")


def _build_subscription_choice_keyboard(links) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for link in links:
        builder.button(text=link.marzban_user, callback_data=f"select_sub:{link.marzban_user}")
    builder.button(text=_("Продлить все"), callback_data="select_sub:all")
    builder.button(text=_("Отмена"), callback_data="select_sub:cancel")
    builder.adjust(1)
    return builder.as_markup()


async def _resolve_selected_users(callback: CallbackQuery, plan_callback: str, state: FSMContext) -> list[str]:
    data = await state.get_data()
    if data.get("selected_good") == plan_callback and data.get("selected_marzban_users"):
        return data.get("selected_marzban_users", [])

    links = await get_links_by_tg_id(callback.from_user.id)
    if not links:
        primary_link = await ensure_user_link(callback.from_user)
        links = [primary_link] if primary_link else []

    selected = [links[0].marzban_user] if links else []
    await state.update_data(selected_good=plan_callback, selected_marzban_users=selected)
    return selected


async def _show_payment_methods(callback: CallbackQuery, good_id: str):
    good = goods.get(good_id)
    if not good:
        await callback.answer(_("Plan not found."), show_alert=True)
        return
    text = _("Select payment method ⬇️")
    try:
        await callback.message.edit_text(text=text, reply_markup=get_payment_keyboard(good))
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text=text, reply_markup=get_payment_keyboard(good))
    await callback.answer()


def _calculate_total_amount(good: dict, quantity: int, currency_key: str) -> str:
    base_price = good.get("price", {}).get(currency_key) or 0
    try:
        base_value = float(base_price)
    except (TypeError, ValueError):
        base_value = 0.0
    total = base_value * max(quantity, 1)
    return str(int(total)) if total.is_integer() else f"{total:.2f}"


@router.callback_query(F.data.startswith("pay_kassa_"))
async def callback_payment_method_select(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    data = callback.data.replace("pay_kassa_", "")
    if data not in goods.get_callbacks():
        await callback.answer()
        return
    good = goods.get(data)
    selected_users = await _resolve_selected_users(callback, data, state)
    if not selected_users:
        await callback.message.answer(
            _("Не удалось найти привязанные подписки. Попробуйте ещё раз."),
            reply_markup=get_main_menu_keyboard(False),
        )
        await callback.answer()
        return
    total_amount = _calculate_total_amount(good, len(selected_users), "ru")
    result = await yookassa.create_payment(
        callback.from_user.id,
        data,
        callback.message.chat.id,
        callback.from_user.language_code,
        total_amount=total_amount,
    )
    if result.get('payment_db_id'):
        for username in selected_users:
            await add_manual_payment_link(payment_id=result['payment_db_id'], marzban_user=username)
    await callback.message.answer(
        _("To be paid - {amount}₽ ⬇️").format(
            amount=int(float(result['amount']))
        ),
        reply_markup=get_pay_keyboard(result['url']))
    await callback.answer()


@router.callback_query(F.data.startswith("pay_stars_"))
async def callback_payment_method_select(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    data = callback.data.replace("pay_stars_", "")
    if data not in goods.get_callbacks():
        await callback.answer()
        return
    logging.info(f"callback.data: {data}")
    good = goods.get(data)
    logging.info(f"good: {good}")
    selected_users = await _resolve_selected_users(callback, data, state)
    if not selected_users:
        await callback.message.answer(
            _("Не удалось найти привязанные подписки. Попробуйте ещё раз."),
            reply_markup=get_main_menu_keyboard(False),
        )
        await callback.answer()
        return
    price = int(float(good['price']['stars']) * max(len(selected_users), 1))
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
async def callback_payment_method_select(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    data = callback.data.replace("pay_crypto_", "")
    if data not in goods.get_callbacks():
        await callback.answer()
        return
    good = goods.get(data)
    selected_users = await _resolve_selected_users(callback, data, state)
    if not selected_users:
        await callback.message.answer(
            _("Не удалось найти привязанные подписки. Попробуйте ещё раз."),
            reply_markup=get_main_menu_keyboard(False),
        )
        await callback.answer()
        return
    total_amount = _calculate_total_amount(good, len(selected_users), "en")
    result = await cryptomus.create_payment(
        callback.from_user.id,
        data,
        callback.message.chat.id,
        callback.from_user.language_code,
        total_amount=total_amount,
    )
    if result.get('payment_db_id'):
        for username in selected_users:
            await add_manual_payment_link(payment_id=result['payment_db_id'], marzban_user=username)
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
    selected_users = await _resolve_selected_users(callback, data, state)
    if not selected_users:
        await callback.message.answer(
            _("Не удалось найти привязанные подписки. Попробуйте ещё раз."),
            reply_markup=get_main_menu_keyboard(False),
        )
        await callback.answer()
        return
    total_amount = _calculate_total_amount(good, len(selected_users), "ru")
    payment_id = await add_manual_payment(
        callback.from_user.id,
        data,
        callback.message.chat.id,
        callback.from_user.language_code,
        callback.from_user.username,
        plan_name=good.get('title') or good.get('name'),
        amount=total_amount,
    )
    for username in selected_users:
        await add_manual_payment_link(payment_id=payment_id, marzban_user=username)
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
    marzban_usernames = await get_manual_payment_links(payment.id)
    if admin_chat_id:
        try:
            await glv.bot.copy_message(
                chat_id=admin_chat_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )
            username = payment.username if payment.username else message.from_user.full_name
            info_text = _(
                "Manual payment #{payment_id}\nUser: <a href=\"tg://user?id={user_id}\">{username}</a> (@{username_tag})\nPlan: {plan}\nSubscriptions: {subs}\nAmount: {amount}"
            ).format(
                payment_id=payment.id,
                user_id=payment.tg_id,
                username=username,
                username_tag=payment.username or "—",
                plan=payment.plan_name or good.get('name', '') or good.get('title', ''),
                subs=", ".join(marzban_usernames) if marzban_usernames else "—",
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

    marzban_usernames = await get_manual_payment_links(payment.id)
    if not marzban_usernames:
        links = await get_links_by_tg_id(payment.tg_id)
        marzban_usernames = [links[0].marzban_user] if links else []

    try:
        result = await process_successful_payment(
            payment,
            marzban_usernames,
            send_user_message=False,
        )
    except Exception as e:  # noqa: BLE001
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

    successes = result.get('successes', [])
    errors = result.get('errors', [])
    status_value = "manual_confirmed" if successes else "manual_error"
    await update_manual_payment(payment.id, status=status_value)

    good = goods.get(payment.callback)
    months = good.get('months') if good else None
    success_users = ", ".join([item.get('username', '') for item in successes]) if successes else ""
    error_text = ", ".join([
        f"{err.get('username', '')}: {err.get('error', '')}" for err in errors
    ])

    if successes:
        if len(successes) == 1:
            user_message = _("✅ Subscription {username} has been extended for {months} months.").format(
                username=successes[0].get('username', ''), months=months or ""
            )
        else:
            user_message = _("✅ Subscriptions {subs} extended for {months} months. Updated data is available in \"My subscription 👤\".").format(
                subs=success_users,
                months=months or "",
            )
    else:
        user_message = _("⚠️ Failed to activate subscription. Please contact support.")

    if errors:
        user_message += "\n" + _("Issues: {details}").format(details=error_text)

    await glv.bot.send_message(payment.chat_id, user_message)

    if glv.config.get('TG_INFO_CHANEL'):
        admin_parts = []
        if successes:
            admin_parts.append(_("Extended: {subs}").format(subs=success_users))
        if errors:
            admin_parts.append(_("Errors: {details}").format(details=error_text))
        admin_text = _("✅ Payment {payment_id} processed. {details}").format(
            payment_id=payment.id,
            details="; ".join(admin_parts) if admin_parts else "",
        )
        await glv.bot.send_message(glv.config['TG_INFO_CHANEL'], admin_text)

    logging.info("Manual payment %s %s by admin %s", payment.id, status_value, callback.from_user.id)
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
async def callback_payment_method_select(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    good_id = callback.data

    links = await get_links_by_tg_id(callback.from_user.id)
    if not links:
        primary_link = await ensure_user_link(callback.from_user)
        links = [primary_link] if primary_link else []

    if len(links) <= 1:
        await state.update_data(
            selected_good=good_id,
            selected_marzban_users=[links[0].marzban_user] if links else [],
        )
        await _show_payment_methods(callback, good_id)
        return

    await state.set_state(PaymentSelectionStates.selecting_subscriptions)
    await state.update_data(selected_good=good_id)
    keyboard = _build_subscription_choice_keyboard(links)
    await callback.message.answer(
        _("Выберите подписки для продления ⬇️"),
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(PaymentSelectionStates.selecting_subscriptions, F.data.startswith("select_sub:"))
async def callback_select_subscription(callback: CallbackQuery, state: FSMContext):
    selection = callback.data.replace("select_sub:", "")
    state_data = await state.get_data()
    good_id = state_data.get("selected_good")
    links = await get_links_by_tg_id(callback.from_user.id)

    if selection == "cancel":
        await state.clear()
        await callback.message.answer(_("Choose the appropriate tariff ⬇️"), reply_markup=get_buy_menu_keyboard())
        await callback.answer()
        return

    if selection == "all":
        selected_users = [link.marzban_user for link in links]
    else:
        selected_users = [link.marzban_user for link in links if link.marzban_user == selection]

    if not selected_users:
        await callback.answer(_("Subscription not found."), show_alert=True)
        return

    await state.update_data(selected_marzban_users=selected_users, selected_good=good_id)
    await _show_payment_methods(callback, good_id)


@router.callback_query(F.data == "back:buy_menu")
async def callback_back_to_buy_menu(callback: CallbackQuery):
    keyboard = get_buy_menu_keyboard()
    text = _("Choose the appropriate tariff ⬇️")
    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard)
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text=text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "back:main")
async def callback_back_to_main(callback: CallbackQuery):
    had_test_subscription = await had_test_sub(callback.from_user.id)
    text = _("Hello, {name} 👋🏻\n\nSelect an action ⬇️").format(
        name=callback.from_user.first_name,
        title=glv.config.get('SHOP_NAME', 'VPN Shop'),
    )
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(text, reply_markup=get_main_menu_keyboard(had_test_subscription))
    await callback.answer()


def register_callbacks(dp: Dispatcher):
    dp.include_router(router)
