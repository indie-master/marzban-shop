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
from db.methods import (
    had_test_sub,
    update_test_subscription_state,
    get_marzban_profile_db,
    create_vpn_profile,
)
from utils import marzban_api
from utils.payments import format_expire
from utils.images import send_section_image
import glv
import html
import math
from datetime import datetime

router = Router(name="messages-router") 


def _as_quote_block(text: str) -> str:
    escaped_lines = [html.escape(line) for line in text.splitlines()]
    return "<blockquote>" + "\n".join(escaped_lines) + "</blockquote>"


def _resolve_service_link() -> str:
    return glv.config.get('SERVICE_URL') or glv.config.get('SUPPORT_LINK') or ""


def _resolve_profile_name(user: dict, tg_user) -> str:
    candidates = [
        user.get('note'),
        user.get('name'),
        user.get('username'),
        user.get('email'),
        getattr(tg_user, 'username', None),
        str(getattr(tg_user, 'id', '')) if getattr(tg_user, 'id', None) else None,
    ]
    for value in candidates:
        if value:
            return str(value)
    return "—"


def _build_subscription_instruction(sub_url: str) -> str:
    service_name = glv.config.get('SERVICE_NAME') or glv.config.get('SHOP_NAME') or "VPN Service"
    service_url = _resolve_service_link()
    support_url = glv.config.get('SUPPORT_LINK') or service_url

    client_name = glv.config.get('CLIENT_NAME') or "HAPP"
    ios_name = glv.config.get('CLIENT_IOS_NAME') or client_name
    ios_url = glv.config.get('CLIENT_IOS_URL') or glv.config.get('HAPP_IOS_URL') or ""
    android_name = glv.config.get('CLIENT_ANDROID_NAME') or client_name
    android_url = glv.config.get('CLIENT_ANDROID_URL') or glv.config.get('HAPP_ANDROID_PLAY_URL') or ""
    android_alt_name = glv.config.get('CLIENT_ANDROID_ALT_NAME') or client_name
    android_alt_url = glv.config.get('CLIENT_ANDROID_ALT_URL') or glv.config.get('HAPP_ANDROID_APK_URL') or ""
    windows_name = glv.config.get('CLIENT_WINDOWS_NAME') or client_name
    windows_url = glv.config.get('CLIENT_WINDOWS_URL') or glv.config.get('HAPP_WINDOWS_URL') or ""
    linux_name = glv.config.get('CLIENT_LINUX_NAME') or client_name
    linux_url = glv.config.get('CLIENT_LINUX_URL') or glv.config.get('HAPP_LINUX_URL') or ""

    app_links = [
        f'<a href="{html.escape(ios_url)}">{html.escape(ios_name)} (iOS)</a>' if ios_url else f'{html.escape(ios_name)} (iOS)',
        f'<a href="{html.escape(android_url)}">{html.escape(android_name)} (Android)</a>' if android_url else f'{html.escape(android_name)} (Android)',
        f'<a href="{html.escape(android_alt_url)}">{html.escape(android_alt_name)} (Android без Google Play)</a>' if android_alt_url else f'{html.escape(android_alt_name)} (Android без Google Play)',
        f'<a href="{html.escape(windows_url)}">{html.escape(windows_name)} (Windows)</a>' if windows_url else f'{html.escape(windows_name)} (Windows)',
        f'<a href="{html.escape(linux_url)}">{html.escape(linux_name)} (Linux)</a>' if linux_url else f'{html.escape(linux_name)} (Linux)',
    ]

    service_line = f'{html.escape(service_name)} (<a href="{html.escape(service_url)}">{html.escape(service_url)}</a>)' if service_url else html.escape(service_name)
    support_line = f'<a href="{html.escape(support_url)}">{html.escape(support_url)}</a>' if support_url else "—"

    return _(
        "Инструкция по установке и настройке {service}.\n\n"
        "1. Скачать и установить приложение {client}.\n"
        "Приложение доступно для скачивания по следующим ссылкам:\n"
        "{links}\n"
        "2. Скопировать ссылку подписки, далее открыть приложение {client} и нажать \"вставить из буфера обмена\".\n"
        "Ваша ссылка для подписки:\n"
        "<code>{sub_url}</code>\n"
        "3. Выбрать любой доступный сервер и нажать кнопку \"ВКЛ\".\n\n"
        "Альтернативный вариант настройки доступен при переходе по ссылке подписки напрямую, "
        "там отображается информация о самой подписке, а так же есть все необходимые инструкции.\n\n"
        "Если возникнут вопросы просим обращаться в нашу поддержку. ({support})\n\n"
        "С уважением, команда {service_name}."
    ).format(
        service=service_line,
        client=html.escape(client_name),
        links=" | ".join(app_links),
        sub_url=html.escape(sub_url),
        support=support_line,
        service_name=service_line,
    )


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
    status_text = _("🟢 Активна") if is_active else _("🔴 Не активна")
    profile_name = _resolve_profile_name(user, message.from_user)

    if data_limit:
        remaining = max(data_limit - used_traffic, 0)
        remaining_gb = remaining / (1024 ** 3)
        traffic_value = f"{remaining_gb:.2f} GB"
    else:
        traffic_value = "♾️"

    quote_block = _as_quote_block(_(
        "Имя клиента/подписки: {name}\n"
        "Доступ: {status}\n"
        "Осталось дней: {days}\n"
        "Активна до: {date}\n"
        "Остаток трафика: {traffic}"
    ).format(
        name=profile_name,
        status=status_text,
        days=days_left,
        date=expire_text,
        traffic=traffic_value,
    ))

    open_hint = _as_quote_block(_("Чтобы открыть подписку в приложении — нажмите кнопку \"Перейти\"."))
    instruction_text = _build_subscription_instruction(sub_url)

    text = f"{quote_block}\n\n{instruction_text}\n\n{open_hint}"
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

    profile = await get_marzban_profile_db(message.from_user.id)
    if profile is None:
        await create_vpn_profile(message.from_user.id)
        profile = await get_marzban_profile_db(message.from_user.id)

    if profile is None:
        await message.answer(
            _("Your profile is not active at the moment.\n\nYou can choose \"Join 🏄🏻‍♂️\"."),
            reply_markup=get_main_menu_keyboard(False),
        )
        return

    result = await marzban_api.generate_test_subscription(profile.vpn_id)
    await update_test_subscription_state(message.from_user.id)
    await message.answer(
        _(
            "Thank you for choice ❤️\n️\n<a href=\"{link}\">Subscribe</a> so you don't miss any announcements ✅\n️\nYour subscription is purchased and available in the \"My subscription 👤\" section."
        ).format(
            link=glv.config['TG_INFO_CHANEL']),
        reply_markup=get_main_menu_keyboard(True),
    )
    
@router.message(F.text.in_([__("⏪ Back"), __("⬅️ Назад")]))
async def start_text(message: Message):
    await start(message)

def register_messages(dp: Dispatcher):
    dp.include_router(router)
