from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from db import get_pool
from locales import t
from aiogram.types import CallbackQuery


import asyncio
import os
ADMIN_ID = int(os.getenv("ADMIN_ID"))

async def get_user_lang(user_id: int) -> str:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT language FROM users WHERE id = $1", user_id)
    return row["language"] if row else "ru"


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- FSM состояния для настройки фильтра ---
class FilterSetup(StatesGroup):
    city = State()
    price_min = State()
    price_max = State()
    property_type = State()
    broadcast = State()

# --- /start ---
@dp.message(CommandStart())
async def cmd_start(message: Message):
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT id FROM users WHERE id = $1", message.from_user.id)
        await conn.execute("""
            INSERT INTO users (id, username)
            VALUES ($1, $2)
            ON CONFLICT (id) DO NOTHING
        """, message.from_user.id, message.from_user.username)

    if not existing:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton(text="🇨🇿 Čeština", callback_data="lang_cs")],
        ])
        await message.answer("👋 Привет! Выбери язык / Vyber si jazyk:", reply_markup=kb)
    else:
        lang = await get_user_lang(message.from_user.id)
        share_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=t(lang, "share_button"),
                url="https://t.me/share/url?url=t.me/realty_kelev_bot&text=Бот%20который%20находит%20квартиры%20раньше%20всех%20в%20Чехии"
            )]
        ])
        await message.answer(t(lang, "welcome"), reply_markup=share_kb)
        asyncio.create_task(remind_filter(message.from_user.id))


@dp.callback_query(F.data.startswith("lang_"))
async def set_language(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET language = $1 WHERE id = $2", lang, callback.from_user.id)

    await callback.message.edit_text(t(lang, "language_set"))

    share_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=t(lang, "share_button"),
            url="https://t.me/share/url?url=t.me/realty_kelev_bot&text=Бот%20который%20находит%20квартиры%20раньше%20всех%20в%20Чехии"
        )]
    ])
    await callback.message.answer(t(lang, "welcome"), reply_markup=share_kb)
    asyncio.create_task(remind_filter(callback.from_user.id))

async def remind_filter(user_id: int):
    await asyncio.sleep(300)  # 5 минут
    pool = await get_pool()
    async with pool.acquire() as conn:
        f = await conn.fetchrow("SELECT id FROM user_filters WHERE user_id = $1", user_id)
    if not f:
        lang = await get_user_lang(user_id)
        try:
            await bot.send_message(user_id, t(lang, "remind_filter"))
        except:
            pass

# --- /filter ---
@dp.message(Command("filter"))
async def cmd_filter(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    await state.update_data(lang=lang)
    await state.set_state(FilterSetup.city)
    await message.answer(t(lang, "ask_city"))

@dp.message(FilterSetup.city)
async def filter_city(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    city = None if message.text.lower() in ["любой", "any", "vse", "vše", "libovolné"] else message.text.strip()
    await state.update_data(city=city)
    await state.set_state(FilterSetup.price_min)
    await message.answer(t(lang, "ask_price_min"))

@dp.message(FilterSetup.price_min)
async def filter_price_min(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    try:
        price_min = int("".join(filter(str.isdigit, message.text)))
    except:
        price_min = 0
    await state.update_data(price_min=price_min if price_min > 0 else None)
    await state.set_state(FilterSetup.price_max)
    await message.answer(t(lang, "ask_price_max"))

@dp.message(FilterSetup.price_max)
async def filter_price_max(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    try:
        price_max = int("".join(filter(str.isdigit, message.text)))
    except:
        price_max = 0
    await state.update_data(price_max=price_max if price_max > 0 else None)
    await state.set_state(FilterSetup.property_type)

    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=t(lang, "type_flat"))],
        [KeyboardButton(text=t(lang, "type_room"))],
        [KeyboardButton(text=t(lang, "type_house"))],
        [KeyboardButton(text=t(lang, "type_any"))],
    ], resize_keyboard=True, one_time_keyboard=True)

    await message.answer(t(lang, "ask_property_type"), reply_markup=kb)

@dp.message(FilterSetup.property_type)
async def filter_property_type(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    text = message.text.strip()

    if "Квартира" in text or "Byt" in text:
        prop_type = "Pronájem bytu"
    elif "Комната" in text or "подселение" in text or "Pokoj" in text or "spolubydlení" in text:
        prop_type = "Комната/подселение"
    elif "Дом" in text or "Dům" in text:
        prop_type = "Pronájem domu"
    else:
        prop_type = None

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM user_filters WHERE user_id = $1", message.from_user.id)
        await conn.execute("""
            INSERT INTO user_filters (user_id, city, price_min, price_max, property_type)
            VALUES ($1, $2, $3, $4, $5)
        """, message.from_user.id, data.get("city"), data.get("price_min"), data.get("price_max"), prop_type)

    await state.clear()

    city_str = data.get("city") or t(lang, "any")
    price_min_str = data.get("price_min") or "—"
    price_max_str = data.get("price_max") or "—"
    type_str = prop_type or t(lang, "any_type")

    await message.answer(
        t(lang, "filter_saved", city=city_str, price_min=price_min_str, price_max=price_max_str, type=type_str),
        reply_markup=ReplyKeyboardRemove()
    )

# --- /myfilter ---
@dp.message(Command("myfilter"))
async def cmd_myfilter(message: Message):
    lang = await get_user_lang(message.from_user.id)
    pool = await get_pool()
    async with pool.acquire() as conn:
        f = await conn.fetchrow("SELECT * FROM user_filters WHERE user_id = $1", message.from_user.id)

    if not f:
        await message.answer(t(lang, "no_filter"))
        return

    await message.answer(
        t(lang, "your_filter",
          city=f['city'] or t(lang, "any"),
          price_min=f['price_min'] or '—',
          price_max=f['price_max'] or '—',
          type=f['property_type'] or t(lang, "any_type"))
    )
# --- /stop ---
@dp.message(Command("stop"))
async def cmd_stop(message: Message):
    lang = await get_user_lang(message.from_user.id)
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM user_filters WHERE user_id = $1", message.from_user.id)
    await message.answer(t(lang, "stopped"))
    

# --- admin ---
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        filters_count = await conn.fetchval("SELECT COUNT(*) FROM user_filters")
        listings_count = await conn.fetchval("SELECT COUNT(*) FROM listings")

        top_cities = await conn.fetch("""
            SELECT city, COUNT(*) as cnt 
            FROM user_filters 
            WHERE city IS NOT NULL 
            GROUP BY city 
            ORDER BY cnt DESC 
            LIMIT 5
        """)

    cities_text = "\n".join([f"  {r['city']}: {r['cnt']}" for r in top_cities]) or "  —"

    await message.answer(
        f"📊 Статистика RealtyKelev Bot\n\n"
        f"👥 Пользователей: {users_count}\n"
        f"🔔 Активных фильтров: {filters_count}\n"
        f"🏠 Объявлений в базе: {listings_count}\n\n"
        f"🏙 Топ городов:\n{cities_text}"
    )

@dp.message(Command("ausers"))
async def cmd_admin_users(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        users = await conn.fetch("""
            SELECT u.id, u.username, f.city, f.price_min, f.price_max
            FROM users u
            LEFT JOIN user_filters f ON f.user_id = u.id
            ORDER BY u.created_at DESC
            LIMIT 20
        """)

    if not users:
        await message.answer("Пользователей нет.")
        return

    text = "👥 Пользователи:\n\n"
    for u in users:
        city = u['city'] or '—'
        price_min = u['price_min'] or '—'
        price_max = u['price_max'] or '—'
        username = f"@{u['username']}" if u['username'] else str(u['id'])
        text += f"{username} | {city} | {price_min}–{price_max} Kč\n"

    await message.answer(text)


@dp.message(Command("abroadcast"))
async def cmd_broadcast(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return
    await state.set_state(FilterSetup.broadcast)
    await message.answer("📢 Введи текст рассылки:")

@dp.message(FilterSetup.broadcast)
async def do_broadcast(message: Message, state: FSMContext):
    await state.clear()
    pool = await get_pool()
    async with pool.acquire() as conn:
        users = await conn.fetch("SELECT id FROM users")

    sent = 0
    for u in users:
        try:
            await bot.send_message(u['id'], f"📢 {message.text}")
            sent += 1
        except:
            pass

    await message.answer(f"✅ Отправлено {sent} пользователям.")


@dp.message(Command("aclear"))
async def cmd_clear_listings(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        deleted = await conn.fetchval("""
            WITH deleted AS (
                DELETE FROM listings 
                WHERE created_at < NOW() - INTERVAL '7 days'
                RETURNING id
            )
            SELECT COUNT(*) FROM deleted
        """)
    await message.answer(f"🗑 Удалено старых объявлений: {deleted or 0}")