from aiogram import Router
from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _
from aiogram.utils.i18n import lazy_gettext as __

from keyboards import get_main_menu_keyboard
import glv
from db.methods import had_test_sub, add_user_link, get_link_by_marzban_user, update_user_link_username
from services.user_links import build_note
from utils.marzban_api import panel, update_user_note

router = Router(name="commands-router")


class LinkStates(StatesGroup):
    waiting_for_username = State()

@router.message(
    Command("start")
)
async def start(message: Message):
    text = _("Hello, {name} 👋🏻\n\nSelect an action ⬇️").format(
        name=message.from_user.first_name,
        title=glv.config.get('SHOP_NAME', 'VPN Shop')
    )
    had_test_subscription = await had_test_sub(message.from_user.id)
    await message.answer(text, reply_markup=get_main_menu_keyboard(had_test_subscription))


@router.message(Command("link"))
async def link_command(message: Message, state: FSMContext):
    await state.set_state(LinkStates.waiting_for_username)
    await message.answer(_("Send your Marzban username to link it with your Telegram account."))


@router.message(LinkStates.waiting_for_username)
async def process_link_username(message: Message, state: FSMContext):
    username = (message.text or "").strip()
    if not username:
        await message.answer(_("Please enter a valid username."))
        return
    try:
        await panel.get_user(username)
    except Exception:
        await message.answer(_("User not found in Marzban."))
        return
    existing = await get_link_by_marzban_user(username)
    if existing:
        if existing.tg_id != message.from_user.id:
            await message.answer(
                _("This Marzban user is already linked to another Telegram account.")
            )
            await state.clear()
            return
        await update_user_link_username(message.from_user.id, message.from_user.username)
    else:
        await add_user_link(
            tg_id=message.from_user.id,
            tg_username=message.from_user.username,
            marzban_user=username,
        )
    note = build_note(message.from_user.id, message.from_user.username)
    await update_user_note(username, note)
    await state.clear()
    await message.answer(_("Account {username} has been linked to your Telegram.").format(username=username))


def register_commands(dp: Dispatcher):
    dp.include_router(router)
