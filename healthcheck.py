import asyncio
import importlib
import os

from parser.base import BaseScraper

SKIP = {"base.py", "telegram_channel.py", "healthcheck.py"}
TIMEOUT = 90  # сек на один парсер


def discover():
    classes = {}
    errors = []
    for fn in sorted(os.listdir("parser")):
        if not fn.endswith(".py") or fn in SKIP or fn.startswith("_"):
            continue
        try:
            m = importlib.import_module("parser." + fn[:-3])
        except Exception as e:
            errors.append((fn[:-3], repr(e)))
            continue
        for attr in dir(m):
            obj = getattr(m, attr)
            if isinstance(obj, type) and issubclass(obj, BaseScraper) and obj is not BaseScraper:
                src = getattr(obj, "source_name", attr)
                classes[src] = obj
    return classes, errors


async def check(name, cls):
    try:
        listings = await asyncio.wait_for(cls().fetch_listings(), timeout=TIMEOUT)
        n = len(listings)
        if n == 0:
            return f"[ПУСТО]  {name:18} найдено=0  (жив, но ничего не отдал)"
        s = listings[0]
        photos = len(s.get("image_urls") or [])
        return (f"[OK]     {name:18} найдено={n:<4} "
                f"пример: {s.get('city', '?')} / {s.get('price', '?')} Kč / "
                f"{s.get('disposition') or '-'} / фото={photos}")
    except asyncio.TimeoutError:
        return f"[ТАЙМАУТ]{name:18} завис дольше {TIMEOUT}с"
    except Exception as e:
        return f"[ОШИБКА] {name:18} {e!r}"


async def main():
    classes, errors = discover()
    print(f"Нашёл {len(classes)} парсеров, проверяю по очереди (таймаут {TIMEOUT}с)...\n")
    for name, err in errors:
        print(f"[ИМПОРТ] {name:18} {err}")
    for name in sorted(classes):
        print(await check(name, classes[name]))


asyncio.run(main())