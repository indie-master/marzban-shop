import logging
import secrets
from typing import Optional

from aiogram.types import User as TelegramUser

from db.methods import (
    add_user_link,
    get_primary_user_link,
    update_user_link_username,
)
from utils import marzban_api

logger = logging.getLogger(__name__)


def build_note(tg_id: int, tg_username: Optional[str]) -> str:
    username_text = f"@{tg_username}" if tg_username else "—"
    return f"Telegram ID: {tg_id}\nTelegram Username: {username_text}"


async def ensure_user_link(tg_user: TelegramUser):
    """Ensure that there is at least one Marzban link for the Telegram user."""
    await update_user_link_username(tg_user.id, tg_user.username)
    link = await get_primary_user_link(tg_user.id)
    if link is not None:
        return link

    username = await _generate_unique_username(tg_user)
    note = build_note(tg_user.id, tg_user.username)
    await marzban_api.create_user(username=username, note=note)
    await add_user_link(tg_id=tg_user.id, tg_username=tg_user.username, marzban_user=username)
    logger.info("Created new Marzban user %s for Telegram ID %s", username, tg_user.id)
    return await get_primary_user_link(tg_user.id)


async def _generate_unique_username(tg_user: TelegramUser) -> str:
    base = tg_user.username.lower() if tg_user.username else str(tg_user.id)
    base = f"tg_{base}"
    for _ in range(10):
        candidate = f"{base}_{secrets.token_hex(2)}"
        exists = await marzban_api.check_if_user_exists(candidate)
        if not exists:
            return candidate
    raise RuntimeError("Failed to generate unique Marzban username for Telegram user")
