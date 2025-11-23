import json
import os
import time
import aiohttp
import requests

from db.methods import get_marzban_profile_db
import glv

PROTOCOLS_DEFAULT = {
    "vmess": {
        "proxies": {},
        "inbounds": ["VMess TCP"],
    },
    "vless": {
        "proxies": {
            "flow": "xtls-rprx-vision"
        },
        "inbounds": ["VLESS + TCP + REALITY"],
    },
    "trojan": {
        "proxies": {},
        "inbounds": ["Trojan Websocket TLS"],
    },
    "shadowsocks": {
        "proxies": {
            "method": "chacha20-ietf-poly1305"
        },
        "inbounds": ["Shadowsocks TCP"],
    },
}

class Marzban:
    def __init__(self, ip, login, passwd) -> None:
        self.ip = ip
        self.login = login
        self.passwd = passwd
    
    async def _send_request(self, method, path, headers=None, data=None) -> dict | list:
        async with aiohttp.ClientSession() as session:
            async with session.request(method, self.ip + path, headers=headers, json=data) as resp:
                if 200 <= resp.status < 300:
                    body = await resp.json()
                    return body
                else:
                    raise Exception(f"Error: {resp.status}; Body: {await resp.text()}; Data: {data}")
    
    def get_token(self) -> str:
        data = {
            "username": self.login,
            "password": self.passwd
        }
        resp = requests.post(self.ip + "/api/admin/token", data=data).json()
        self.token = resp["access_token"]
        return self.token
    
    async def get_user(self, username) -> dict:
        headers = {
            'Authorization': f"Bearer {self.token}"
        }
        resp = await self._send_request("GET", f"/api/user/{username}", headers=headers)
        return resp
    
    async def get_users(self) -> dict:
        headers = {
            'Authorization': f"Bearer {self.token}"
        }
        resp = await self._send_request("GET", "/api/users", headers=headers)
        return resp
    
    async def add_user(self, data) -> dict:
        headers = {
            'Authorization': f"Bearer {self.token}"
        }
        resp = await self._send_request("POST", "/api/user", headers=headers, data=data)
        return resp
    
    async def modify_user(self, username, data) -> dict:
        headers = {
            'Authorization': f"Bearer {self.token}"
        }
        resp = await self._send_request("PUT", f"/api/user/{username}", headers=headers, data=data)
        return resp

def get_protocols() -> dict:
    proxies = {}
    inbounds = {}

    config_path = glv.config.get('PROTOCOLS_CONFIG')
    protocols_config = PROTOCOLS_DEFAULT
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                protocols_config = json.load(f)
        except Exception:
            protocols_config = PROTOCOLS_DEFAULT

    for proto in glv.config['PROTOCOLS']:
        l = proto.lower()
        if l not in protocols_config:
            continue
        proto_data = protocols_config[l]
        proxies[l] = proto_data.get('proxies', {})
        inbounds[l] = proto_data.get('inbounds', [])
    return {
        "proxies": proxies,
        "inbounds": inbounds
    }

panel = Marzban(glv.config['PANEL_HOST'], glv.config['PANEL_USER'], glv.config['PANEL_PASS'])
mytoken = panel.get_token()
ps = get_protocols()

async def check_if_user_exists(name: str) -> bool:
    try:
        await panel.get_user(name)
        return True
    except Exception as e:
        return False

async def get_marzban_profile(tg_id: int):
    db_user = await get_marzban_profile_db(tg_id)
    if db_user is None:
        return None

    res = await check_if_user_exists(db_user.vpn_id)
    if not res:
        return None
    return await panel.get_user(db_user.vpn_id)

async def generate_test_subscription(username: str):
    res = await check_if_user_exists(username)
    if res:
        user = await panel.get_user(username)
        user['status'] = 'active'
        if user['expire'] < time.time():
            user['expire'] = get_test_subscription(glv.config['TEST_PERIOD_DAYS'])
        else:
            user['expire'] += get_test_subscription(glv.config['TEST_PERIOD_DAYS'], True)
        result = await panel.modify_user(username, user)
    else:
        user = {
            'username': username,
            'proxies': ps["proxies"],
            'inbounds': ps["inbounds"],
            'expire': get_test_subscription(glv.config['TEST_PERIOD_DAYS']),
            'data_limit': 0,
            'data_limit_reset_strategy': "no_reset",
        }
        result = await panel.add_user(user)
    return result

async def generate_marzban_subscription(username: str, good):
    res = await check_if_user_exists(username)
    if res:
        user = await panel.get_user(username)
        user['status'] = 'active'
        if user['expire'] < time.time():
            user['expire'] = get_subscription_end_date(good['months'])
        else:
            user['expire'] += get_subscription_end_date(good['months'], True)
        result = await panel.modify_user(username, user)
    else:
        user = {
            'username': username,
            'proxies': ps["proxies"],
            'inbounds': ps["inbounds"],
            'expire': get_subscription_end_date(good['months']),
            'data_limit': 0,
            'data_limit_reset_strategy': "no_reset",
        }
        result = await panel.add_user(user)
    return result

def get_test_subscription(days: int, additional= False) -> int:
    return (0 if additional else int(time.time())) + 60 * 60 * 24 * days

def get_subscription_end_date(months: int, additional = False) -> int:
    return (0 if additional else int(time.time())) + 60 * 60 * 24 * 30 * months
