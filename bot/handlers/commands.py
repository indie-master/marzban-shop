from aiogram import Router
from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _
from aiogram.utils.i18n import lazy_gettext as __

from keyboards import get_main_menu_keyboard
import glv
from db.methods import had_test_sub
from utils.images import send_section_image

router = Router(name="commands-router") 

@router.message(
    Command("start")
)
async def start(message: Message):
    had_test_subscription = await had_test_sub(message.from_user.id)

    await send_section_image(message, "START_IMAGE_ENABLED", "START_IMAGE_PATH")

    trial_line = ""
    if glv.config.get('TEST_PERIOD') and not had_test_subscription:
        trial_line = _("You have access to a free period - {days} days.\n\n").format(
            days=glv.config.get('TEST_PERIOD_DAYS', 0)
        )

    text = _(
        "Welcome to Swiftless Service!\n\n"
        "This is a Telegram bot for connecting to secure internet.\n"
        "{trial_line}"
        "Our motto:\n"
        "Safe\n"
        "Unlimited\n"
        "Fast\n\n"
        "Yours\n\n"
        "Available locations:\n"
        "\ud83c\udde9\ud83c\uddea Germany\n"
        "\ud83c\uddf8\ud83c\uddf0 Slovakia\n"
        "\ud83c\uddf8\ud83c\uddea Sweden\n\n"
        "And we also have YouTube without ads!"
    ).format(trial_line=trial_line)
    await message.answer(text, reply_markup=get_main_menu_keyboard(had_test_subscription))

def register_commands(dp: Dispatcher):
    dp.include_router(router)
