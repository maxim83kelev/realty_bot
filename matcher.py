import asyncpg
from db import get_pool
import difflib
import time

CITY_ALIASES = {
    # Русский → ASCII
    "брно": "brno",
    "прага": "praha",
    "острава": "ostrava",
    "оломоуц": "olomouc",
    "злин": "zlin",
    "злін": "zlin",
    "пльзень": "plzen",
    "либерец": "liberec",
    "пардубице": "pardubice",
    "градец кралове": "hradec kralove",
    "усти над лабем": "usti nad labem",
    "усти": "usti nad labem",
    "чески будейовице": "ceske budejovice",
    "будейовице": "ceske budejovice",
    "гавиржов": "havirov",
    "кладно": "kladno",
    "мост": "most",
    "опава": "opava",
    "фридек мистек": "frydek mistek",
    "карвина": "karvina",
    "йиглава": "jihlava",
    "теплице": "teplice",
    "дечин": "decin",
    "зноймо": "znojmo",
    "годонин": "hodonin",
    "простейов": "prostejov",
    "пршеров": "prerov",
    "тршебич": "trebic",
    "шлапаниче": "slapanice",
    "куржим": "kurim",
    "бланско": "blansko",
    "вышков": "vyskov",
    "бржецлав": "breclav",
    "кромержиж": "kromeriz",
    "угерске градиште": "uherske hradiste",
    "валашске мезиржичи": "valasske mezirici",
    "новы йичин": "novy jicin",
    "чески крумлов": "cesky krumlov",
    "пршибрам": "pribram",
    "млада болеслав": "mlada boleslav",
    "коллин": "kolin",
    "хрудим": "chrudim",
    "табор": "tabor",
    "писек": "pisek",
    "страконице": "strakonice",
    "йиндржихув градец": "jindrichuv hradec",
    "пелгржимов": "pelhrimov",
    # Украинский → ASCII
    "злін": "zlin",
    "оломоуць": "olomouc",
    "ліберець": "liberec",
    "пардубіце": "pardubice",
    "градець кралове": "hradec kralove",
    # Чешский с háček → ASCII
    "zlín": "zlin",
    "plzeň": "plzen",
    "hradec králové": "hradec kralove",
    "ústí nad labem": "usti nad labem",
    "české budějovice": "ceske budejovice",
    "havířov": "havirov",
    "karviná": "karvina",
    "frýdek-místek": "frydek mistek",
    "děčín": "decin",
    "hodonín": "hodonin",
    "prostějov": "prostejov",
    "přerov": "prerov",
    "třebíč": "trebic",
    "šlapanice": "slapanice",
    "kuřim": "kurim",
    "vyškov": "vyskov",
    "břeclav": "breclav",
    "kroměříž": "kromeriz",
    "uherské hradiště": "uherske hradiste",
    "valašské meziříčí": "valasske mezirici",
    "nový jičín": "novy jicin",
    "český krumlov": "cesky krumlov",
    "příbram": "pribram",
    "mladá boleslav": "mlada boleslav",
    "jindřichův hradec": "jindrichuv hradec",
}

def normalize_city(city: str) -> str:
    if not city:
        return ""
    return CITY_ALIASES.get(city.lower(), city.lower())

SEEKER_KEYWORDS = [
    # Русский
    "ищу", "ищем", "сниму", "снимем", "нужна квартира", "нужна комната","рассмотрим",
    # Украинский
    "шукаю", "шукаємо", "зніму", "знімемо", "потрібна квартира", "підселюся", "розглянемо",
    # Чешский
    "hledám", "hledáme", "sháním", "hledám byt", "hledám pokoj",
    # Английский
    "looking for", "searching for", "need a flat", "need a room",
]

def is_seeker(listing: dict) -> bool:
    title = (listing.get("title") or "").lower()
    return any(kw.lower() in title for kw in SEEKER_KEYWORDS)

async def save_and_match(listings: list[dict]) -> list[tuple[dict, list[int]]]:
    """
    Принимает список объявлений.
    Возвращает список (объявление, [user_id, user_id, ...]) только для новых.
    """
    pool = await get_pool()
    result = []

    async with pool.acquire() as conn:
        for listing in listings:
            # Защита от объявлений с нераспарсенной ценой
            if not listing.get("price") or listing["price"] <= 0:
                print(f"[ZeroPrice] source={listing.get('source')} ...")
                continue

            # Защита от объявлений без города — иначе матчатся под любой фильтр
            if not (listing.get("city") or "").strip():
                print(f"[NoCity] source={listing.get('source')} url={listing.get('url')}")
                continue

            if is_seeker(listing):
                print(f"[Seeker] Пропускаем ищущего: {listing.get('title', '')[:60]}")
                continue     

            # Пробуем вставить — если external_id уже есть, пропускаем
            inserted = await conn.fetchrow("""
                INSERT INTO listings (source, external_id, title, price, city, property_type, url)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (external_id) DO NOTHING
                RETURNING id
            """,
                listing["source"],
                listing["external_id"],
                listing["title"],
                listing["price"],
                normalize_city(listing["city"]),
                listing["property_type"],
                listing["url"],
            )

            if not inserted:
                continue  # уже видели это объявление

            # Новое объявление — ищем кому слать
            users = await conn.fetch("""
                SELECT u.id FROM users u
                JOIN user_filters f ON f.user_id = u.id
                WHERE
                    (f.city IS NULL OR LOWER($1) LIKE '%' || LOWER(f.city) || '%' OR LOWER(f.city) LIKE '%' || LOWER($1) || '%')
                    AND (f.price_min IS NULL OR $2 >= f.price_min)
                    AND (f.price_max IS NULL OR $2 <= f.price_max)
                    AND (f.property_type IS NULL OR LOWER(f.property_type) = LOWER($3))
            """, normalize_city(listing["city"]), listing["price"], listing["property_type"])

            if users:
                result.append((listing, [u["id"] for u in users]))

    return result

CITY_ANY = {
    "любой", "любая", "все", "всё", "любой город",
    "будь-який", "усі", "any", "all",
    "vse", "vše", "libovolné", "libovolne", "všechna",
}

_cities_cache = {"data": set(), "ts": 0.0}

async def get_price_median(city: str | None, prop_type: str | None) -> int | None:
    """Медиана цены по городу и типу. None, если данных мало (<5 объявлений)."""
    if not city:
        return None

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                percentile_cont(0.5) WITHIN GROUP (ORDER BY price) AS median,
                COUNT(*) AS n
            FROM listings
            WHERE city = $1
              AND price > 0
              AND ($2::text IS NULL OR property_type = $2)
            """,
            city, prop_type,
        )

    if not row or row["n"] < 5:
        return None
    return int(row["median"])

async def get_known_cities() -> set[str]:
    """Города, по которым в базе реально есть объявления. Кэш на час."""
    now = time.time()
    if _cities_cache["data"] and now - _cities_cache["ts"] < 3600:
        return _cities_cache["data"]

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT DISTINCT city FROM listings WHERE city IS NOT NULL AND city <> ''"
        )

    cities = {r["city"].lower().strip() for r in rows}
    cities |= set(CITY_ALIASES.values())  # чтобы новые города не проваливались на пустой базе

    _cities_cache["data"] = cities
    _cities_cache["ts"] = now
    return cities


async def validate_city(text: str) -> tuple[str, str | None]:
    """
    Возвращает (status, value):
      ("any", None)          — пользователь хочет все города
      ("invalid", None)      — мусор: цифры, символы, команда
      ("ok", city)           — город найден
      ("suggest", city)      — не найден, но есть похожий
      ("unknown", raw)       — не найден и похожих нет
    """
    raw = (text or "").strip()

    if not raw or raw.startswith("/"):
        return ("invalid", None)
    if raw.lower() in CITY_ANY:
        return ("any", None)
    if raw.isdigit() or len(raw) < 2 or not any(ch.isalpha() for ch in raw):
        return ("invalid", None)

    city = normalize_city(raw)
    known = await get_known_cities()

    # Brno совпадает с "brno - řečkovice", "brno-střed" и т.д.
    for k in known:
        if city == k or city in k or k in city:
            return ("ok", city)

    # Похожий город: brnoo → brno, prga → praha
    base = {k.split(" - ")[0].split(",")[0].strip() for k in known}
    match = difflib.get_close_matches(city, base, n=1, cutoff=0.72)
    if match:
        return ("suggest", match[0].title())

    return ("unknown", raw)