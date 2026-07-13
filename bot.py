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
from matcher import normalize_city
from matcher import normalize_city, validate_city


import asyncio
import os
ADMIN_ID = int(os.getenv("ADMIN_ID"))

async def get_user_lang(user_id: int) -> str:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT language FROM users WHERE id = $1", user_id)
    return row["language"] if row else "ru"

async def is_banned(user_id: int) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT user_id FROM banned_users WHERE user_id = $1", user_id)
    return row is not None

PROP_TYPE_KEYS = {
    "Pronájem bytu": "type_flat",
    "Комната/подселение": "type_room",
    "Pronájem domu": "type_house",
}

def format_price(lang: str, pmin, pmax) -> str:
    if pmin and pmax:
        return t(lang, "price_range", min=pmin, max=pmax)
    if pmin:
        return t(lang, "price_from", min=pmin)
    if pmax:
        return t(lang, "price_to", max=pmax)
    return t(lang, "price_any")

def format_city(lang: str, city) -> str:
    return city.title() if city else t(lang, "any")

def format_type(lang: str, prop_type) -> str:
    if not prop_type:
        return t(lang, "any_type")
    key = PROP_TYPE_KEYS.get(prop_type)
    return t(lang, key) if key else prop_type

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- FSM состояния для настройки фильтра ---
class FilterSetup(StatesGroup):
    city = State()
    price_min = State()
    price_max = State()
    property_type = State()
    broadcast = State()
    feedback = State()
    reply = State()

@dp.message.outer_middleware()
async def ban_check_middleware(handler, event, data):
    user_id = event.from_user.id
    if user_id != ADMIN_ID and await is_banned(user_id):
        return  # молча игнорируем, даже не отвечаем
    return await handler(event, data)

@dp.callback_query.outer_middleware()
async def ban_check_callback_middleware(handler, event, data):
    user_id = event.from_user.id
    if user_id != ADMIN_ID and await is_banned(user_id):
        return
    return await handler(event, data)


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
            )],
            [InlineKeyboardButton(text=t(lang, "feedback_button"), callback_data="open_feedback")]
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
        )],
        [InlineKeyboardButton(text=t(lang, "feedback_button"), callback_data="open_feedback")]
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
        
@dp.callback_query(F.data == "open_feedback")
async def open_feedback(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    await state.set_state(FilterSetup.feedback)
    text = "✍️ Напиши свой отзыв или сообщи о проблеме — я прочитаю лично:" if lang == "ru" else "✍️ Napiš svůj feedback nebo nahlas problém — přečtu si to osobně:"
    await callback.message.answer(text)
    await callback.answer()               

# --- /help ---
@dp.message(Command("help"))
async def cmd_help(message: Message):
    lang = await get_user_lang(message.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "feedback_button"), callback_data="open_feedback")]
    ])
    await message.answer(t(lang, "help"), reply_markup=kb)


# --- /cancel ---
@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    if await state.get_state() is None:
        await message.answer(t(lang, "nothing_to_cancel"))
        return
    await state.clear()
    await message.answer(t(lang, "cancelled"), reply_markup=ReplyKeyboardRemove())

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

    status, value = await validate_city(message.text)

    if status == "invalid":
        await message.answer(t(lang, "city_not_valid"))
        return
    if status == "suggest":
        await message.answer(t(lang, "city_did_you_mean", suggestion=value))
        return
    if status == "unknown":
        await message.answer(t(lang, "city_unknown", city=value))
        return

    city = None if status == "any" else value

    await state.update_data(city=city)
    await state.set_state(FilterSetup.price_min)
    await message.answer(t(lang, "ask_price_min"))

MIN_PRICE = 500    # ниже этого аренды не бывает, только развод
MAX_PRICE = 150_000  # выше — это уже вилла, а не байт

@dp.message(FilterSetup.price_min)
async def filter_price_min(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    raw = "".join(filter(str.isdigit, message.text or ""))

    if not raw:
        await message.answer(t(lang, "price_not_a_number"))
        return

    price_min = int(raw)

    if price_min > MAX_PRICE:
        await message.answer(t(lang, "price_too_high", price=price_min, max=MAX_PRICE))
        return

    if 0 < price_min < MIN_PRICE:
        await message.answer(t(lang, "price_too_low", price=price_min, min=MIN_PRICE))
        return

    await state.update_data(price_min=price_min if price_min > 0 else None)
    await state.set_state(FilterSetup.price_max)
    await message.answer(t(lang, "ask_price_max"))


@dp.message(FilterSetup.price_max)
async def filter_price_max(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    raw = "".join(filter(str.isdigit, message.text or ""))

    if not raw:
        await message.answer(t(lang, "price_not_a_number"))
        return

    price_max = int(raw)

    if price_max > MAX_PRICE:
        await message.answer(t(lang, "price_too_high", price=price_max, max=MAX_PRICE))
        return

    if 0 < price_max < MIN_PRICE:
        await message.answer(t(lang, "price_too_low", price=price_max, min=MIN_PRICE))
        return

    price_min = data.get("price_min")
    if price_max > 0 and price_min and price_max < price_min:
        await message.answer(t(lang, "price_max_less_than_min", price_min=price_min))
        return

    await state.update_data(price_max=price_max if price_max > 0 else None)
    await state.set_state(FilterSetup.property_type)

    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=t(lang, "type_flat"))],
        [KeyboardButton(text=t(lang, "type_room"))],
        [KeyboardButton(text=t(lang, "type_house"))],
        [KeyboardButton(text=t(lang, "type_any"))],
    ], resize_keyboard=True, one_time_keyboard=True)

    await message.answer(t(lang, "ask_property_type"), reply_markup=kb)

async def send_initial_digest(user_id: int, city: str, price_min, price_max, prop_type: str, lang: str):
    await asyncio.sleep(2)  # небольшая пауза чтобы фильтр точно сохранился
    pool = await get_pool()
    async with pool.acquire() as conn:
        listings = await conn.fetch("""
            SELECT title, price, city, property_type, url
            FROM listings
            WHERE
                ($1::text IS NULL OR LOWER(city) LIKE '%' || LOWER($1) || '%' OR LOWER($1) LIKE '%' || LOWER(city) || '%')
                AND ($2::int IS NULL OR price >= $2)
                AND ($3::int IS NULL OR price <= $3)
                AND ($4::text IS NULL OR LOWER(property_type) = LOWER($4))
                AND price > 0
                AND city IS NOT NULL AND city <> ''
            ORDER BY created_at DESC
            LIMIT 5
        """, normalize_city(city or ""), price_min, price_max, prop_type)

    if not listings:
        return

    warning = "📦 Вот что уже есть в базе по твоему фильтру. Свежесть не гарантирую:\n\n" if lang == "ru" else "📦 Toto je již v databázi podle tvého filtru. Aktuálnost neručím:\n\n"
    text = warning
    for l in listings:
        text += f"🏠 {l['property_type']}\n📍 {l['title']}\n💰 {l['price']:,} Kč\n🔗 {l['url']}\n\n"

    try:
        await bot.send_message(user_id, text)
    except Exception as e:
        print(f"[InitialDigest] Ошибка: {e}")


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
        """, message.from_user.id, normalize_city(data.get("city") or ""), data.get("price_min"), data.get("price_max"), prop_type)

    await state.clear()

    await message.answer(
        t(lang, "filter_saved",
          city=format_city(lang, data.get("city")),
          price=format_price(lang, data.get("price_min"), data.get("price_max")),
          type=format_type(lang, prop_type)),
        reply_markup=ReplyKeyboardRemove()
    )
    # Сразу после сохранения фильтра — шлём дайджест из базы
    asyncio.create_task(send_initial_digest(message.from_user.id, data.get("city"), data.get("price_min"), data.get("price_max"), prop_type, lang))

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
          city=format_city(lang, f['city']),
          price=format_price(lang, f['price_min'], f['price_max']),
          type=format_type(lang, f['property_type']))
    )

#--- Объявления из базы по моему фильтру
@dp.message(Command("digest"))
async def cmd_digest(message: Message):
    lang = await get_user_lang(message.from_user.id)
    pool = await get_pool()
    async with pool.acquire() as conn:
        f = await conn.fetchrow("SELECT * FROM user_filters WHERE user_id = $1", message.from_user.id)

    if not f:
        await message.answer(t(lang, "no_filter"))
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        listings = await conn.fetch("""
            SELECT title, price, city, property_type, url, source, created_at
            FROM listings
            WHERE
                ($1::text IS NULL OR LOWER(city) LIKE '%' || LOWER($1) || '%' OR LOWER($1) LIKE '%' || LOWER(city) || '%')
                AND ($2::int IS NULL OR price >= $2)
                AND ($3::int IS NULL OR price <= $3)
                AND ($4::text IS NULL OR LOWER(property_type) = LOWER($4))
                AND price > 0
                AND city IS NOT NULL AND city <> ''
            ORDER BY created_at DESC
            LIMIT 10
        """, f['city'], f['price_min'], f['price_max'], f['property_type'])

    if not listings:
        text = "🔍 В базе ничего по твоему фильтру. Либо ещё не появлялось, либо всё уже сдано — кто знает." if lang == "ru" else "🔍 V databázi nic podle tvého filtru. Možná ještě nepřišlo, možná už je vše pronajato."
        await message.answer(text)
        return

    warning = "⚠️ Это объявления из базы. За свежесть не ручаюсь — проверяй сам на свой страх и риск.\n\n" if lang == "ru" else "⚠️ Toto jsou inzeráty z databáze. Za aktuálnost neručím — ověř si sám na vlastní riziko.\n\n"

    text = warning
    for l in listings:
        text += f"🏠 {l['property_type']}\n📍 {l['title']}\n💰 {l['price']:,} Kč\n🔗 {l['url']}\n\n"

    await message.answer(text)    

# --- /stop ---
@dp.message(Command("stop"))
async def cmd_stop(message: Message):
    lang = await get_user_lang(message.from_user.id)
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM user_filters WHERE user_id = $1", message.from_user.id)
    await message.answer(t(lang, "stopped"))
    

# --- /feedback ---
@dp.message(Command("feedback"))
async def cmd_feedback(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    await state.set_state(FilterSetup.feedback)
    text = "✍️ Напиши свой отзыв или сообщи о проблеме — я прочитаю лично:" if lang == "ru" else "✍️ Napiš svůj feedback nebo nahlas problém — přečtu si to osobně:"
    await message.answer(text)

@dp.message(FilterSetup.feedback)
async def receive_feedback(message: Message, state: FSMContext):
    await state.clear()
    lang = await get_user_lang(message.from_user.id)

    username = f"@{message.from_user.username}" if message.from_user.username else str(message.from_user.id)
    user_id = message.from_user.id

    # Кнопка "Ответить" для админа
    reply_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Ответить", callback_data=f"reply_{user_id}")]
    ])

    forward_text = f"📩 Фидбэк от {username} [ID:{user_id}]:\n\n{message.text}"

    try:
        await bot.send_message(ADMIN_ID, forward_text, reply_markup=reply_kb)
    except Exception as e:
        print(f"[Feedback] Не удалось отправить админу: {e}")

    text = "✅ Спасибо! Сообщение отправлено." if lang == "ru" else "✅ Děkuji! Zpráva byla odeslána."
    await message.answer(text)

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
        users = await conn.fetch("SELECT id, language FROM users")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔥 Рассказать другу",
            url="https://t.me/share/url?url=t.me/realty_kelev_bot&text=Бот%20который%20находит%20квартиры%20раньше%20всех%20в%20Чехии"
        )],
        [InlineKeyboardButton(text="💬 Связь с автором", callback_data="open_feedback")]
    ])

    sent = 0
    for u in users:
        try:
            await bot.send_message(u['id'], f"📢 {message.text}", reply_markup=kb)
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


@dp.message(Command("aban"))
async def cmd_ban(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("Использование: /aban <user_id> [причина]")
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("Ошибка: user_id должен быть числом.")
        return

    reason = parts[2] if len(parts) > 2 else "без причины"

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO banned_users (user_id, reason)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET reason = $2, banned_at = NOW()
        """, target_id, reason)
        await conn.execute("DELETE FROM user_filters WHERE user_id = $1", target_id)

    await message.answer(f"🔨 Пользователь {target_id} забанен. Причина: {reason}")

@dp.message(Command("aunban"))
async def cmd_unban(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /aunban <user_id>")
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("Ошибка: user_id должен быть числом.")
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        deleted = await conn.fetchval(
            "DELETE FROM banned_users WHERE user_id = $1 RETURNING user_id", target_id
        )

    if deleted:
        await message.answer(f"✅ Пользователь {target_id} разбанен.")
    else:
        await message.answer(f"Пользователь {target_id} не был в бане. Может он просто тихий идиот.")
        
@dp.message(Command("abandlist"))
async def cmd_ban_list(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        banned = await conn.fetch("""
            SELECT user_id, reason, banned_at 
            FROM banned_users 
            ORDER BY banned_at DESC
        """)

    if not banned:
        await message.answer("🕊 Список чист. Либо все адекватные, либо ты ещё не успел никого забанить.")
        return

    text = "🔨 Зал позора:\n\n"
    for b in banned:
        text += f"ID: {b['user_id']} | {b['reason']} | {b['banned_at'].strftime('%d.%m.%Y')}\n"

    await message.answer(text)

@dp.message(Command("areply"))
async def cmd_areply(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return

    # Формат: /areply 630712203 Привет, вот ответ...
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Использование: /areply <user_id> <текст>")
        return

    try:
        target_id = int(parts[1])
        reply_text = parts[2]
    except ValueError:
        await message.answer("Ошибка: user_id должен быть числом.")
        return

    try:
        await bot.send_message(target_id, f"💬 Ответ от администратора:\n\n{reply_text}")
        await message.answer(f"✅ Сообщение отправлено пользователю {target_id}.")
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить: {e}")
        
@dp.callback_query(F.data.startswith("reply_"))
async def start_reply(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа.")
        return
    target_id = int(callback.data.split("_")[1])
    await state.update_data(reply_target=target_id)
    await state.set_state(FilterSetup.reply)
    username_line = callback.message.text.split("\n")[0]
    await callback.message.answer(f"✍️ Пишешь ответ для: {username_line}\n\nВведи текст:")
    await callback.answer()

@dp.message(FilterSetup.reply)
async def send_reply(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await state.clear()
        return
    data = await state.get_data()
    target_id = data.get("reply_target")
    await state.clear()

    try:
        await bot.send_message(target_id, f"💬 Ответ от администратора:\n\n{message.text}")
        await message.answer(f"✅ Ответ отправлен пользователю {target_id}.")
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить: {e}")