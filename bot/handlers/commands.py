from aiogram import Router
from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _
from aiogram.utils.i18n import lazy_gettext as __

from keyboards import get_main_menu_keyboard
import glv
from db.methods import had_test_sub, create_vpn_profile
from utils.images import send_section_image

router = Router(name="commands-router") 

@router.message(
    Command("start")
)
async def start(message: Message):
    await create_vpn_profile(message.from_user.id)
    had_test_subscription = await had_test_sub(message.from_user.id)

    await send_section_image(message, "START_IMAGE_ENABLED", "START_IMAGE_PATH")

    trial_line = ""
    if glv.config.get('TEST_PERIOD') and not had_test_subscription:
        trial_line = _("You have access to a free period - {days} days.\n\n").format(
            days=glv.config.get('TEST_PERIOD_DAYS', 0)
        )

    start_override = glv.config.get('START_TEXT')
    if start_override:
        text = start_override.format(
            service_name=glv.config.get('SERVICE_NAME') or glv.config.get('SHOP_NAME') or "VPN Service",
            trial_line=trial_line,
        )
    else:
        text = _(
            "Добро пожаловать в {service_name}!\n\n"
            "Этот бот помогает подключиться к безопасному и быстрому интернету.\n\n"
            "{trial_line}"
            "Наши принципы:\n"
            "— Безопасно\n"
            "— Безлимитно\n"
            "— Быстро"
        ).format(
            service_name=glv.config.get('SERVICE_NAME') or glv.config.get('SHOP_NAME') or "VPN Service",
            trial_line=trial_line,
        )
    await message.answer(text, reply_markup=get_main_menu_keyboard(had_test_subscription))

def register_commands(dp: Dispatcher):
    dp.include_router(router)
