import logging
from datetime import datetime

from db.methods import get_marzban_profile_db
from keyboards import get_main_menu_keyboard
from utils import goods, marzban_api
from utils.lang import get_i18n_string
import glv


async def process_successful_payment(tg_id: int, callback: str, chat_id: int, lang_code: str, send_user_message: bool = True):
    good = goods.get(callback)
    user = await get_marzban_profile_db(tg_id)
    marzban_result = await marzban_api.generate_marzban_subscription(user.vpn_id, good)

    if send_user_message:
        text = get_i18n_string(
            "Thank you for choice ❤️\n️\n<a href=\"{link}\">Subscribe</a> so you don't miss any announcements ✅\n️\nYour subscription is purchased and available in the \"My subscription 👤\" section.",
            lang_code,
        )
        await glv.bot.send_message(
            chat_id,
            text.format(link=glv.config['TG_INFO_CHANEL']),
            reply_markup=get_main_menu_keyboard(True, lang_code),
        )

    expire_ts = None
    try:
        updated_user = await marzban_api.panel.get_user(user.vpn_id)
        expire_ts = updated_user.get('expire')
    except Exception as e:
        logging.warning("Failed to fetch expire date for user %s: %s", user.vpn_id, e)

    return {
        "marzban_result": marzban_result,
        "expire": expire_ts
    }


def format_expire(expire_ts: int | None) -> str:
    if not expire_ts:
        return "—"
    return datetime.fromtimestamp(expire_ts).strftime("%d.%m.%Y %H:%M")
