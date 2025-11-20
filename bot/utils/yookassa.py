from yookassa import Configuration
from yookassa import Payment

from db.methods import add_yookassa_payment
from utils import goods
import glv

if glv.config['YOOKASSA_SHOPID'] and glv.config['YOOKASSA_TOKEN']:
    Configuration.configure(glv.config['YOOKASSA_SHOPID'], glv.config['YOOKASSA_TOKEN'])

async def create_payment(tg_id: int, callback: str, chat_id: int, lang_code: str, total_amount: str | None = None) -> dict:
    good = goods.get(callback)
    amount_value = total_amount or good['price']['ru']
    resp = Payment.create({
        "amount": {
            "value": amount_value,
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": f"https://t.me/{(await glv.bot.get_me()).username}"
        },
        "capture": True,
        "description": f"Подписка на VPN {glv.config['SHOP_NAME']}",
        "save_payment_method": False,
        "receipt": {
            "customer": {
                "email": glv.config['EMAIL']
            },
            "items": [
                {
                    "description": f"Подписка на VPN сервис: кол-во месяцев - {good['months']}",
                    "quantity": "1",
                    "amount": {
                        "value": amount_value,
                        "currency": "RUB"
                    },
                    "vat_code": "1"
                },
            ]
        }
        })
    payment_db_id = await add_yookassa_payment(tg_id, callback, chat_id, lang_code, resp.id)
    return {
        "url": resp.confirmation.confirmation_url,
        "amount": resp.amount.value,
        "payment_db_id": payment_db_id,
    }