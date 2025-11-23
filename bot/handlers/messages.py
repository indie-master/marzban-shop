from aiogram import Router, F
from aiogram import Dispatcher
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _
from aiogram.utils.i18n import lazy_gettext as __

from .commands import start
from keyboards import (
    get_buy_menu_keyboard,
    get_main_menu_keyboard,
    get_subscription_keyboard,
    get_instructions_menu_keyboard,
    get_faq_keyboard,
    get_support_keyboard,
)
from keyboards.main_menu import get_trial_text
from db.methods import had_test_sub, update_test_subscription_state, get_marzban_profile_db
from utils import marzban_api
from utils.payments import format_expire
from utils.images import send_section_image
import glv
import html
import math
from datetime import datetime

router = Router(name="messages-router") 

@router.message(F.text == __("Join 🏄🏻‍♂️"))
async def buy(message: Message):
    await message.answer(_("Choose the appropriate tariff ⬇️"), reply_markup=get_buy_menu_keyboard())

@router.message(F.text == __("My subscription 👤"))
async def profile(message: Message):
    user = await marzban_api.get_marzban_profile(message.from_user.id)
    if user is None:
        had_trial = await had_test_sub(message.from_user.id)
        trial_available = glv.config['TEST_PERIOD'] and not had_trial
        if trial_available:
            trial_text = get_trial_text(message.from_user.language_code)
            text = _(
                "Your profile is not active at the moment.\n\nYou can choose \"{trial}\" or \"Join 🏄🏻‍♂️\"."
            ).format(trial=trial_text)
        else:
            text = _(
                "Your profile is not active at the moment.\n\nYou can choose \"Join 🏄🏻‍♂️\"."
            )
        await message.answer(text, reply_markup=get_main_menu_keyboard(not trial_available))
        return
    await send_section_image(message, "SUBSCRIPTION_IMAGE_ENABLED", "SUBSCRIPTION_IMAGE_PATH")

    expire_ts = user.get('expire')
    now_ts = datetime.now().timestamp()
    is_active = bool(expire_ts and expire_ts > now_ts)

    expire_text = format_expire(expire_ts).split()[0] if expire_ts else "—"
    days_left = 0
    if expire_ts:
        days_left = max(int(math.ceil((expire_ts - now_ts) / 86400)), 0)

    data_limit = user.get('data_limit') or 0
    used_traffic = user.get('used_traffic') or 0
    remaining_text = _("Remaining traffic: ♾️")
    if data_limit:
        remaining = max(data_limit - used_traffic, 0)
        remaining_gb = remaining / (1024 ** 3)
        remaining_text = _("Remaining traffic: {gb} GB").format(gb=f"{remaining_gb:.2f}")

    sub_url = glv.config['PANEL_GLOBAL'] + user['subscription_url']
    status_text = _("Access: 🟢 Active") if is_active else _("Access: 🔴 Not active")
    text = _(
        "{status}\n"
        "Days left: {days}\n"
        "Active until: {date}\n"
        "{traffic}\n\n"
        "Subscription link:\n"
        "<code>{sub_url}</code>\n\n"
        "To open the subscription in the app — tap the \"Open\" button."
    ).format(
        status=status_text,
        days=days_left,
        date=expire_text,
        traffic=remaining_text,
        sub_url=html.escape(sub_url),
    )
    await message.answer(text, reply_markup=get_subscription_keyboard(sub_url))

@router.message(F.text == __("Frequent questions ℹ️"))
async def information(message: Message):
    await send_section_image(message, "FAQ_IMAGE_ENABLED", "FAQ_IMAGE_PATH")
    await message.answer(
        _("Select a document ⬇️"),
        reply_markup=get_faq_keyboard(),
    )

@router.message(F.text == __("Support ❤️"))
async def support(message: Message):
    await send_section_image(message, "SUPPORT_IMAGE_ENABLED", "SUPPORT_IMAGE_PATH")
    support_link = glv.config.get('SUPPORT_LINK') or ""
    await message.answer(
        _("Follow the <a href=\"{link}\">link</a> and ask us a question. We are always happy to help 🤗").format(
            link=support_link),
        reply_markup=get_support_keyboard(),
    )


@router.message(F.text == __("Instructions 📚"))
async def instructions(message: Message):
    await send_section_image(message, "INSTRUCTIONS_IMAGE_ENABLED", "INSTRUCTIONS_IMAGE_PATH")
    await message.answer(
        _("Choose your platform ⬇️"),
        reply_markup=get_instructions_menu_keyboard(),
    )

@router.message(F.text == __("5 days free 🆓"))
async def test_subscription(message: Message):
    result = await had_test_sub(message.from_user.id)
    if result:
        await message.answer(
            _("Your subscription is available in the \"My subscription 👤\" section."),
            reply_markup=get_main_menu_keyboard(True))
        return
    result = await get_marzban_profile_db(message.from_user.id)
    result = await marzban_api.generate_test_subscription(result.vpn_id)
    await update_test_subscription_state(message.from_user.id)
    await message.answer(
        _("Thank you for choice ❤️\n️\n<a href=\"{link}\">Subscribe</a> so you don't miss any announcements ✅\n️\nYour subscription is purchased and available in the \"My subscription 👤\" section.").format(
            link=glv.config['TG_INFO_CHANEL']),
        reply_markup=get_main_menu_keyboard(True)
    )
    
@router.message(F.text.in_([__("⏪ Back"), __("⬅️ Назад")]))
async def start_text(message: Message):
    await start(message)

def register_messages(dp: Dispatcher):
    dp.include_router(router)
