"""
Вечерний отчёт админу + счётчик отправленных объявлений.
Прикручивается к scheduler.py через add_daily_report(scheduler).
"""
import os
from datetime import datetime
from db import get_pool
from bot import bot

ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Счётчик отправленных объявлений за текущий день (в памяти).
# Обнуляется при перезапуске бота и после отправки отчёта.
_sent_today = {"count": 0, "date": datetime.now().date()}


def count_sent():
    """Вызывать из рассылки при каждой успешной отправке объявления юзеру."""
    today = datetime.now().date()
    if _sent_today["date"] != today:
        _sent_today["count"] = 0
        _sent_today["date"] = today
    _sent_today["count"] += 1


async def build_report() -> str:
    pool = await get_pool()
    async with pool.acquire() as conn:
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
        new_users = await conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE created_at::date = CURRENT_DATE"
        )
        active_filters = await conn.fetchval("SELECT COUNT(*) FROM user_filters")
        total_listings = await conn.fetchval("SELECT COUNT(*) FROM listings")
        new_listings = await conn.fetchval(
            "SELECT COUNT(*) FROM listings WHERE created_at::date = CURRENT_DATE"
        )
        # топ-5 городов по фильтрам
        cities = await conn.fetch("""
            SELECT city, COUNT(*) AS n FROM user_filters
            WHERE city IS NOT NULL AND city <> ''
            GROUP BY city ORDER BY n DESC LIMIT 5
        """)
        no_city = await conn.fetchval(
            "SELECT COUNT(*) FROM user_filters WHERE city IS NULL"
        )

    cities_text = "\n".join(f"  {r['city']}: {r['n']}" for r in cities) or "  —"

    report = (
        f"📊 Отчёт за {datetime.now():%d.%m.%Y}\n\n"
        f"👥 Пользователей: {total_users} (+{new_users} сегодня)\n"
        f"🔔 Активных фильтров: {active_filters}\n"
        f"📤 Отправлено объявлений сегодня: {_sent_today['count']}\n"
        f"🏠 Объявлений в базе: {total_listings} (+{new_listings} сегодня)\n\n"
        f"🏙 Топ городов (фильтры):\n{cities_text}\n"
        f"🌍 Без фильтра города: {no_city}"
    )
    return report


async def send_daily_report():
    try:
        report = await build_report()
        await bot.send_message(ADMIN_ID, report)
        # обнуляем счётчик отправленных после отчёта
        _sent_today["count"] = 0
        _sent_today["date"] = datetime.now().date()
    except Exception as e:
        print(f"[Report] не удалось отправить отчёт: {e}")


# --- критические уведомления с троттлингом ---
_last_alert = {}  # ключ ошибки -> время последней отправки

async def notify_admin(key: str, text: str, throttle_min: int = 30):
    """Шлёт админу критическое уведомление, но не чаще раза в throttle_min для данного key."""
    now = datetime.now()
    last = _last_alert.get(key)
    if last and (now - last).total_seconds() < throttle_min * 60:
        return  # уже недавно слали такое — молчим, чтобы не спамить
    _last_alert[key] = now
    try:
        await bot.send_message(ADMIN_ID, f"⚠️ {text}")
    except Exception as e:
        print(f"[notify_admin] {e}")


def add_daily_report(scheduler):
    """Регистрирует ежедневный отчёт в 18:00. Вызвать из start_scheduler()."""
    scheduler.add_job(send_daily_report, "cron", hour=20, minute=10, timezone="Europe/Prague")