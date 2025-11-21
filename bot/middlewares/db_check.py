from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from db.methods import create_vpn_profile
from services.user_links import ensure_user_link

class DBCheck(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data["event_from_user"]
        await create_vpn_profile(user.id)
        await ensure_user_link(user)
        result = await handler(event, data)
        return result
