import json
from pathlib import Path


GOODS_FILE = Path("goods.json")


def _load_goods() -> list:
    data = []
    if GOODS_FILE.exists():
        with GOODS_FILE.open(encoding="utf-8") as file:
            data = json.load(file)
    return data


def get(callback=None) -> list | dict:
    data = _load_goods()
    if callback is None:
        return data
    for item in data:
        if item.get("callback") == callback:
            return item
    return {}


def get_callbacks() -> list:
    data = _load_goods()
    return [x.get("callback") for x in data if "callback" in x]