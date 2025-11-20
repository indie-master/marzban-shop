import asyncio
import time

from db.methods import get_marzban_profile_by_vpn_id
from utils import marzban_api, get_i18n_string

import glv

async def notify_users_to_renew_sub():
    marzban_users_to_notify = await get_marzban_users_to_notify()
    if marzban_users_to_notify is None:
        return None
    
    for marzban_user in marzban_users_to_notify:
        vpn_id = marzban_user['username']
        user = await get_marzban_profile_by_vpn_id(vpn_id)
        if user is None:
            continue
        chat_member = await glv.bot.get_chat_member(user.tg_id, user.tg_id)
        if chat_member is None:
            continue
        message = get_i18n_string("Hello, {name} 👋🏻\n\nThank you for using our service ❤️\n️\nYour VPN subscription expires {day}, at the end of the day.\n️\nTo renew it, just go to the \"Join 🏄🏻‍♂️\" section and make a payment.", chat_member.user.language_code).format(
            name=chat_member.user.first_name,
            day=get_expiration_day_str(marzban_user, chat_member.user.language_code))
        await glv.bot.send_message(user.tg_id, message)

async def get_marzban_users_to_notify():
    res = await marzban_api.panel.get_users()
    if res is None:
        return None
    users = res['users']
    return filter(filter_users_to_notify, users)

def filter_users_to_notify(user):
    user_expire_date = user['expire']
    if user_expire_date is None:
        return False
    
    now = int(time.time())
    after_tomorrow = now + 60 * 60 * 36
    return now < user_expire_date < after_tomorrow

def get_expiration_day_str(user, lang):
    if user['expire'] < int(time.time()) + 60 * 60 * 12:
        return get_i18n_string("today", lang)
    return get_i18n_string("tomorrow", lang)
