import asyncio
import importlib
import os

from parser.base import BaseScraper

SKIP = {"base.py", "telegram_channel.py", "healthcheck.py"}
TIMEOUT = 60  # сек на один парсер


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
                classes[getattr(obj, "source_name", attr)] = obj
    return classes, errors


async def check(name, cls):
    try:
        listings = await asyncio.wait_for(cls().fetch_listings(), timeout=TIMEOUT)
        n = len(listings)
        if n == 0:
            return f"⚠️ {name}: ПУСТО (0 объявлений)"
        return f"✅ {name}: {n}"
    except asyncio.TimeoutError:
        return f"❌ {name}: ТАЙМАУТ (>{TIMEOUT}с)"
    except Exception as e:
        return f"❌ {name}: ОШИБКА — {e!r}"


async def run_healthcheck() -> str:
    """Проверяет все парсеры, возвращает готовый текст для отправки в бот."""
    classes, errors = discover()
    lines = [f"🩺 Проверка парсеров ({len(classes)} шт)\n"]
    for name, err in errors:
        lines.append(f"❌ {name}: НЕ ИМПОРТИРУЕТСЯ — {err}")
    for name in sorted(classes):
        lines.append(await check(name, classes[name]))
    dead = len([l for l in lines if l.startswith("❌")])
    empty = len([l for l in lines if l.startswith("⚠️")])
    lines.append(f"\nИтог: живых {len(classes) - dead}, проблемных {dead + empty}")
    return "\n".join(lines)


async def _main():
    print(await run_healthcheck())


if __name__ == "__main__":
    asyncio.run(_main())
