import logging
from typing import List

from db.methods import (
    add_user_link,
    delete_user_link,
    get_all_linked_usernames,
    get_link_by_marzban_user,
)
from services.user_links import build_note
from utils import marzban_api

logger = logging.getLogger(__name__)


async def sync_existing_users() -> tuple[int, int]:
    users = await marzban_api.get_all_users()
    if not users:
        logger.warning("No users returned from Marzban. Skipping sync statistics update.")
        return 0, 0
    linked = 0
    unlinked = 0
    for user in users:
        username = user.get('username')
        if not username:
            continue
        link = await get_link_by_marzban_user(username)
        if link:
            linked += 1
        else:
            unlinked += 1
    logger.info("Sync complete. Linked: %s, Unlinked: %s", linked, unlinked)
    return linked, unlinked


async def get_unlinked_marzban_users() -> List[dict]:
    users = await marzban_api.get_all_users()
    linked_usernames = await get_all_linked_usernames()
    return [user for user in users if user.get('username') and user.get('username') not in linked_usernames]


async def link_existing_user(tg_id: int, tg_username: str | None, marzban_username: str):
    marzban_username = marzban_username.strip()
    if not marzban_username:
        raise ValueError("Username cannot be empty")
    marzban_user = await marzban_api.get_user(marzban_username)
    if marzban_user is None:
        raise ValueError(f"User {marzban_username} was not found in Marzban")
    existing_link = await get_link_by_marzban_user(marzban_username)
    if existing_link is not None:
        raise ValueError(f"User {marzban_username} is already linked to Telegram ID {existing_link.tg_id}")
    await add_user_link(
        tg_id=tg_id,
        tg_username=_normalize_username(tg_username),
        marzban_user=marzban_username,
    )
    note = build_note(tg_id, tg_username)
    await marzban_api.update_user_note(marzban_username, note)
    logger.info("Linked Marzban user %s to Telegram ID %s", marzban_username, tg_id)


async def unlink_user(marzban_username: str):
    await delete_user_link(marzban_username)
    logger.info("Removed link for Marzban user %s", marzban_username)


def _normalize_username(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if value.startswith('@'):
        value = value[1:]
    return value or None
