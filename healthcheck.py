"""
Health-check всех парсеров: по очереди дёргает fetch_listings у каждого,
показывает, сколько нашёл и пример. Запуск: venv/bin/python3 healthcheck.py
telegram-каналы пропускаются (нужен .env и имя канала) — их проверяй отдельно.
"""
import asyncio
import importlib
import pkgutil
import inspect

import parser as parser_pkg
from parser.base import BaseScraper

SKIP_MODULES = {"base", "telegram_channel"}
TIMEOUT = 90  # сек на один парсер


def discover():
    found = []
    for mod in pkgutil.iter_modules(parser_pkg.path):
        if mod.name in SKIP_MODULES:
            continue
        try:
            m = importlib.import_module(f"parser.{mod.name}")
        except Exception as e:
            found.append((mod.name, None, f"import failed: {e}"))
            continue
        for _, obj in inspect.getmembers(m, inspect.isclass):
            if (issubclass(obj, BaseScraper) and obj is not BaseScraper
                    and obj.module == m.name):
                found.append((mod.name, obj, None))
    return found


async def check(name, cls):
    try:
        listings = await asyncio.wait_for(cls().fetch_listings(), timeout=TIMEOUT)
        n = len(listings)
        if n == 0:
            return f"[ПУСТО]  {name:18} найдено=0  (парсер жив, но ничего не отдал)"
        s = listings[0]
        photos = len(s.get("image_urls") or [])
        return (f"[OK]     {name:18} найдено={n:<4} "
                f"пример: {s.get('city', '?')} / {s.get('price', '?')} Kč / "
                f"{s.get('disposition') or '-'} / фото={photos}")
    except asyncio.TimeoutError:
        return f"[ТАЙМАУТ]{name:18} завис дольше {TIMEOUT}с"
    except Exception as e:
        return f"[ОШИБКА] {name:18} {type(e).name}: {e}"


async def main():
    items = discover()
    alive = sum(1 for _, c, _ in items if c)
    print(f"Нашёл {alive} парсеров, проверяю по очереди (таймаут {TIMEOUT}с)...\n")
    for name, cls, err in items:
        if cls is None:
            print(f"[ИМПОРТ] {name:18} {err}")
        else:
            print(await check(name, cls))

asyncio.run(main())