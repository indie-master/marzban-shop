from aiogram import Router, F
from aiogram import Dispatcher
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _
from aiogram.utils.i18n import lazy_gettext as __
from datetime import datetime

from .commands import start
from keyboards import (
    get_buy_menu_keyboard,
    get_back_keyboard,
    get_main_menu_keyboard,
    get_instructions_menu_keyboard,
)
from db.methods import had_test_sub, update_test_subscription_state, get_primary_user_link
from services.user_links import (
    UserSubscription,
    ensure_user_link,
    build_note,
    get_subscriptions_for_tg,
)
from utils import marzban_api
import glv

router = Router(name="messages-router") 

@router.message(F.text == __("Join 🏄🏻‍♂️"))
async def buy(message: Message):
    await message.answer(_("Choose the appropriate tariff ⬇️"), reply_markup=get_buy_menu_keyboard())

@router.message(F.text == __("My subscription 👤"))
async def profile(message: Message):
    subscriptions = await get_subscriptions_for_tg(message.from_user.id)
    if not subscriptions:
        await message.answer(
            _("Your profile is not active at the moment.\n️\nYou can choose \"5 days free 🆓\" or \"Join 🏄🏻‍♂️\"."),
            reply_markup=get_main_menu_keyboard(False),
        )
        return

    blocks = [_format_subscription_block(sub) for sub in subscriptions]
    await message.answer(
        "\n\n".join(blocks),
        reply_markup=get_main_menu_keyboard(True),
        parse_mode="HTML",
    )

@router.message(F.text == __("Frequent questions ℹ️"))
async def information(message: Message):
    await message.answer(
        _("Follow the <a href=\"{link}\">link</a> 🔗").format(
            link=glv.config['ABOUT']),
        reply_markup=get_back_keyboard())

@router.message(F.text == __("Support ❤️"))
async def support(message: Message):
    await message.answer(
        _("Follow the <a href=\"{link}\">link</a> and ask us a question. We are always happy to help 🤗").format(
            link=glv.config['SUPPORT_LINK']),
        reply_markup=get_back_keyboard())

@router.message(F.text == __("5 days free 🆓"))
async def test_subscription(message: Message):
    result = await had_test_sub(message.from_user.id)
    if result:
        await message.answer(
            _("Your subscription is available in the \"My subscription 👤\" section."),
            reply_markup=get_main_menu_keyboard(True))
        return
    link = await get_primary_user_link(message.from_user.id)
    if link is None:
        link = await ensure_user_link(message.from_user)
    note = build_note(message.from_user.id, message.from_user.username)
    await marzban_api.generate_test_subscription(link.marzban_user, note)
    await update_test_subscription_state(message.from_user.id)
    await message.answer(
        _("Thank you for choice ❤️\n️\n<a href=\"{link}\">Subscribe</a> so you don't miss any announcements ✅\n️\nYour subscription is purchased and available in the \"My subscription 👤\" section.").format(
            link=glv.config['TG_INFO_CHANEL']),
        reply_markup=get_main_menu_keyboard(True)
    )
    
@router.message(F.text.in_([__("⏪ Back"), __("⬅️ Назад")]))
async def start_text(message: Message):
    await start(message)


def _format_status(status: str, expire: int | None) -> tuple[str, str]:
    status_lower = (status or "").lower()
    if status_lower == "active":
        return "🟢", _("active")
    if status_lower == "on_hold":
        return "🟣", "on hold"
    if status_lower in {"disabled", "limited"}:
        label = _("inactive")
        if expire is not None and expire < int(datetime.now().timestamp()):
            label = _("expired")
        return "🔴", label
    if status_lower == "expired":
        return "🔴", _("expired")
    return "🔴", status or _("unknown")


def _format_expire_text(expire: int | None) -> str:
    if not expire:
        return _("without limitation (∞)")
    expire_dt = datetime.fromtimestamp(expire)
    days_left = (expire_dt.date() - datetime.now().date()).days
    if days_left >= 0:
        return _("until {date} (remaining {days} days)").format(
            date=expire_dt.strftime("%d.%m.%Y"), days=days_left
        )
    return _("expired on {date}").format(date=expire_dt.strftime("%d.%m.%Y"))


def _format_traffic(used: int | None, limit: int | None) -> str:
    used_gb = (used or 0) / (1024 ** 3)
    if not limit:
        return _("{used} GB of ∞").format(used=f"{used_gb:.1f}")
    limit_gb = limit / (1024 ** 3)
    return _("{used} GB of {limit} GB").format(
        used=f"{used_gb:.1f}", limit=f"{limit_gb:.1f}"
    )


def _format_subscription_block(sub: UserSubscription) -> str:
    status_emoji, status_label = _format_status(sub.status, sub.expire)
    expire_text = _format_expire_text(sub.expire)
    traffic_text = _format_traffic(sub.used_traffic, sub.data_limit)
    link_text = sub.subscription_url or "—"
    return (
        f"🌐 {sub.username}\n"
        f"Статус: {status_emoji} {status_label}\n"
        f"Срок: {expire_text}\n"
        f"Трафик: {traffic_text}\n"
        f"Ссылка:\n<code>{link_text}</code>"
    )

def register_messages(dp: Dispatcher):
    dp.include_router(router)
