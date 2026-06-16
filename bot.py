from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from db import get_pool


import asyncio
import os
ADMIN_ID = int(os.getenv("ADMIN_ID"))

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
        await conn.execute("""
            INSERT INTO users (id, username)
            VALUES ($1, $2)
            ON CONFLICT (id) DO NOTHING
        """, message.from_user.id, message.from_user.username)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔥 Рассказать другу",
            url="https://t.me/share/url?url=t.me/realty_kelev_bot&text=Бот%20который%20находит%20квартиры%20раньше%20всех%20в%20Чехии"
        )]
    ])

    await message.answer(
        "👋 Привет! Я RealtyKelev Bot.\n\n"
        "⚡ Как я работаю:\n"
        "Каждые 10 секунд я проверяю новые объявления на чешских сайтах недвижимости "
        "и сразу отправляю тебе ссылку — ты узнаёшь раньше всех.\n\n"
        "Я не храню тексты объявлений — только ссылки на оригинал.\n\n"
        "📌 Команды:\n"
        "/filter — настроить фильтр (город, цена, тип)\n"
        "/myfilter — посмотреть текущий фильтр\n"
        "/stop — остановить уведомления\n\n"
        "Начнём? Настрой фильтр командой /filter",
        reply_markup=kb
    )

    # Напоминание через 5 минут если фильтр не настроен
    asyncio.create_task(remind_filter(message.from_user.id))


async def remind_filter(user_id: int):
    await asyncio.sleep(300)  # 5 минут
    pool = await get_pool()
    async with pool.acquire() as conn:
        f = await conn.fetchrow("SELECT id FROM user_filters WHERE user_id = $1", user_id)
    if not f:
        try:
            await bot.send_message(
                user_id,
                "👋 Эй, не забудь настроить фильтр!\n\n"
                "Без него уведомления не придут.\n"
                "Просто напиши /filter и укажи город и цену — займёт 30 секунд."
            )
        except:
            pass

# --- /filter ---
@dp.message(Command("filter"))
async def cmd_filter(message: Message, state: FSMContext):
    await state.set_state(FilterSetup.city)
    await message.answer(
        "🏙 Введи город (например: Brno, Praha)\n"
        "Или напиши «любой» чтобы получать из всех городов:"
    )

@dp.message(FilterSetup.city)
async def filter_city(message: Message, state: FSMContext):
    city = None if message.text.lower() in ["любой", "any", "vse", "vše"] else message.text.strip()
    await state.update_data(city=city)
    await state.set_state(FilterSetup.price_min)
    await message.answer("💰 Минимальная цена (Kč)?\nИли напиши «0» если без ограничений:")

@dp.message(FilterSetup.price_min)
async def filter_price_min(message: Message, state: FSMContext):
    try:
        price_min = int("".join(filter(str.isdigit, message.text)))
    except:
        price_min = 0
    await state.update_data(price_min=price_min if price_min > 0 else None)
    await state.set_state(FilterSetup.price_max)
    await message.answer("💰 Максимальная цена (Kč)?\nИли напиши «0» если без ограничений:")

@dp.message(FilterSetup.price_max)
async def filter_price_max(message: Message, state: FSMContext):
    try:
        price_max = int("".join(filter(str.isdigit, message.text)))
    except:
        price_max = 0
    await state.update_data(price_max=price_max if price_max > 0 else None)
    await state.set_state(FilterSetup.property_type)

    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🏠 Квартира")],
        [KeyboardButton(text="🛏 Комната / подселение")],
        [KeyboardButton(text="🏡 Дом")],
        [KeyboardButton(text="🔍 Всё подряд")],
    ], resize_keyboard=True, one_time_keyboard=True)

    await message.answer("🏠 Тип недвижимости:", reply_markup=kb)

@dp.message(FilterSetup.property_type)
async def filter_property_type(message: Message, state: FSMContext):
    text = message.text.strip()

    if "Квартира" in text:
        prop_type = "Pronájem bytu"
    elif "Комната" in text or "подселение" in text:
        prop_type = "Комната/подселение"
    elif "Дом" in text:
        prop_type = "Pronájem domu"
    else:
        prop_type = None  # Всё подряд

    data = await state.get_data()
    await state.clear()

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM user_filters WHERE user_id = $1", message.from_user.id)
        await conn.execute("""
            INSERT INTO user_filters (user_id, city, price_min, price_max, property_type)
            VALUES ($1, $2, $3, $4, $5)
        """, message.from_user.id, data.get("city"), data.get("price_min"), data.get("price_max"), prop_type)

    city_str = data.get("city") or "любой"
    price_min_str = data.get("price_min") or "—"
    price_max_str = data.get("price_max") or "—"
    type_str = prop_type or "всё подряд"

    await message.answer(
        f"✅ Фильтр сохранён:\n\n"
        f"🏙 Город: {city_str}\n"
        f"💰 Цена: {price_min_str} — {price_max_str} Kč\n"
        f"🏠 Тип: {type_str}\n\n"
        f"Жди уведомлений!",
        reply_markup=ReplyKeyboardRemove()
    )

# --- /myfilter ---
@dp.message(Command("myfilter"))
async def cmd_myfilter(message: Message):
    pool = await get_pool()
    async with pool.acquire() as conn:
        f = await conn.fetchrow("SELECT * FROM user_filters WHERE user_id = $1", message.from_user.id)

    if not f:
        await message.answer("У тебя нет активного фильтра. Настрой через /filter")
        return

    await message.answer(
        f"📋 Твой фильтр:\n\n"
        f"🏙 Город: {f['city'] or 'любой'}\n"
        f"💰 Цена: {f['price_min'] or '—'} — {f['price_max'] or '—'} Kč\n"
        f"🏠 Тип: {f['property_type'] or 'любой'}"
    )

# --- /stop ---
@dp.message(Command("stop"))
async def cmd_stop(message: Message):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM user_filters WHERE user_id = $1", message.from_user.id)
    await message.answer("🔕 Уведомления остановлены. Вернуться можно через /filter")
    
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