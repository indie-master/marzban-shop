import logging
import secrets
from dataclasses import dataclass
from typing import Optional

from aiogram.types import User as TelegramUser

from db.methods import (
    add_user_link,
    get_links_by_tg_id,
    get_primary_user_link,
    update_user_link_username,
)
from utils import marzban_api
import glv

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


@dataclass
class UserSubscription:
    username: str
    status: str
    expire: int | None
    used_traffic: int | None
    data_limit: int | None
    subscription_url: str | None
    note: str | None


async def get_subscriptions_for_tg(tg_id: int) -> list[UserSubscription]:
    links = await get_links_by_tg_id(tg_id)
    if not links:
        return []

    subscriptions: list[UserSubscription] = []
    for link in links:
        marzban_username = getattr(link, "marzban_user", None)
        if not marzban_username:
            logger.error("Invalid link object for tg %s: %s", tg_id, link)
            continue
        try:
            user = await marzban_api.panel.get_user(marzban_username)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to fetch Marzban user %s for tg %s: %s", marzban_username, tg_id, exc)
            continue

        subscription_url = user.get('subscription_url') or None
        links_field = user.get('links') or []
        if not subscription_url and links_field:
            subscription_url = links_field[0]
        if subscription_url and subscription_url.startswith('/'):
            subscription_url = f"{glv.config['PANEL_GLOBAL']}{subscription_url}"

        subscriptions.append(
            UserSubscription(
                username=user.get('username') or marzban_username,
                status=user.get('status') or "unknown",
                expire=user.get('expire'),
                used_traffic=user.get('used_traffic'),
                data_limit=user.get('data_limit'),
                subscription_url=subscription_url,
                note=user.get('note'),
            )
        )
    return subscriptions
