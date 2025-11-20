import logging
from datetime import datetime

from services.user_links import build_note
from keyboards import get_main_menu_keyboard
from utils import goods, marzban_api
from utils.lang import get_i18n_string
import glv


async def process_successful_payment(payment, marzban_usernames: list[str], send_user_message: bool = True):
    good = goods.get(payment.callback)
    if not good:
        logging.error("Good %s not found for payment %s", payment.callback, getattr(payment, 'id', None))
        return {"successes": [], "errors": [{"error": "good_not_found"}]}

    note = build_note(payment.tg_id, getattr(payment, "username", None))
    successes: list[dict] = []
    errors: list[dict] = []

    for marzban_username in marzban_usernames:
        try:
            await marzban_api.panel.get_user(marzban_username)
        except Exception as exc:  # noqa: BLE001
            logging.exception(
                "Failed to fetch Marzban user %s for payment %s", marzban_username, getattr(payment, 'id', None)
            )
            errors.append({"username": marzban_username, "error": str(exc)})
            continue

        try:
            marzban_result = await marzban_api.generate_marzban_subscription(marzban_username, good, note)
            await marzban_api.update_user_note(marzban_username, note)
            expire_ts = None
            try:
                updated_user = await marzban_api.panel.get_user(marzban_username)
                expire_ts = updated_user.get('expire')
            except Exception as fetch_exc:  # noqa: BLE001
                logging.warning(
                    "Failed to fetch expire date for user %s: %s", marzban_username, fetch_exc
                )

            successes.append(
                {
                    "username": marzban_username,
                    "expire": expire_ts,
                    "result": marzban_result,
                }
            )
        except Exception as exc:  # noqa: BLE001
            logging.exception(
                "Failed to process subscription for payment %s and user %s",
                getattr(payment, 'id', None),
                marzban_username,
            )
            errors.append({"username": marzban_username, "error": str(exc)})

    if send_user_message and successes:
        text = get_i18n_string(
            "Thank you for choice ❤️\n️\n<a href=\"{link}\">Subscribe</a> so you don't miss any announcements ✅\n️\nYour subscription is purchased and available in the \"My subscription 👤\" section.",
            payment.lang,
        )
        await glv.bot.send_message(
            payment.chat_id,
            text.format(link=glv.config['TG_INFO_CHANEL']),
            reply_markup=get_main_menu_keyboard(True, payment.lang),
        )

    return {
        "successes": successes,
        "errors": errors,
    }


def format_expire(expire_ts: int | None) -> str:
    if not expire_ts:
        return "—"
    return datetime.fromtimestamp(expire_ts).strftime("%d.%m.%Y %H:%M")
