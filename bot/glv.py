import os

from aiogram import Bot, Dispatcher

config = {
    'BOT_TOKEN': os.environ.get('BOT_TOKEN'),
    'SHOP_NAME': os.environ.get('SHOP_NAME'),
    'PROTOCOLS': os.environ.get('PROTOCOLS', 'vless').split(),
    'PROTOCOLS_CONFIG': os.environ.get('PROTOCOLS_CONFIG', 'protocols.json'),
    'TEST_PERIOD': os.environ.get('TEST_PERIOD', 'false').lower() == 'true',
    'TEST_PERIOD_DAYS': int(os.environ.get('TEST_PERIOD_DAYS', os.environ.get('PERIOD_LIMIT', 5))),
    'ABOUT': os.environ.get('ABOUT'),
    'RULES_LINK': os.environ.get('RULES_LINK'),
    'SUPPORT_LINK': os.environ.get('SUPPORT_LINK'),
    'DB_URL': f"mysql+asyncmy://{os.environ.get('DB_USER')}:{os.environ.get('DB_PASS')}@{os.environ.get('DB_ADDRESS')}:{os.environ.get('DB_PORT')}/{os.environ.get('DB_NAME')}",
    'YOOKASSA_TOKEN': os.environ.get('YOOKASSA_TOKEN'),
    'YOOKASSA_SHOPID': os.environ.get('YOOKASSA_SHOPID'),
    'EMAIL': os.environ.get('EMAIL'),
    'CRYPTO_TOKEN': os.environ.get('CRYPTO_TOKEN'),
    'MERCHANT_UUID': os.environ.get('MERCHANT_UUID'),
    'PANEL_HOST': os.environ.get('PANEL_HOST'),
    'PANEL_GLOBAL': os.environ.get('PANEL_GLOBAL'),
    'PANEL_USER': os.environ.get('PANEL_USER'),
    'PANEL_PASS': os.environ.get('PANEL_PASS'),
    'WEBHOOK_URL': os.environ.get('WEBHOOK_URL'),
    'WEBHOOK_PORT': int(os.environ.get('WEBHOOK_PORT')),
    'RENEW_NOTIFICATION_TIME': str(os.environ.get('RENEW_NOTIFICATION_TIME')),
    'TG_INFO_CHANEL': os.environ.get('TG_INFO_CHANEL'),
    'STARS_PAYMENT_ENABLED': os.environ.get('STARS_PAYMENT_ENABLED', 'false').lower() == 'true',
    'EXPIRED_NOTIFICATION_TIME': str(os.environ.get('EXPIRED_NOTIFICATION_TIME')),
    'PAY_SBER_URL': os.environ.get('PAY_SBER_URL'),
    'PAY_TBANK_URL': os.environ.get('PAY_TBANK_URL'),
    'ADMIN_IDS': [int(x) for x in os.environ.get('ADMIN_IDS', '').split(',') if x.strip().isdigit()],
}

bot: Bot = None
storage = None
dp: Dispatcher = None