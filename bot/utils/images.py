import logging
from typing import Optional

from aiogram.types import FSInputFile, Message

import glv


def _is_url(path: str) -> bool:
    return path.startswith("http://") or path.startswith("https://")


async def send_section_image(message: Message, enabled_key: str, path_key: str) -> bool:
    enabled = glv.config.get(enabled_key)
    path: Optional[str] = glv.config.get(path_key)

    if not enabled or not path:
        return False

    try:
        photo = path if _is_url(path) else FSInputFile(path)
        await message.answer_photo(photo)
        return True
    except Exception as exc:  # pragma: no cover - best-effort helper
        logging.warning("Failed to send image for %s: %s", enabled_key, exc)
        return False
