import asyncpg
from db import get_pool

CITY_ALIASES = {
    # Русский → чешский
    "брно": "brno",
    "прага": "praha",
    "острава": "ostrava",
    "оломоуц": "olomouc",
    "злин": "zlín",
    "пльзень": "plzeň",
    "либерец": "liberec",
    "пардубице": "pardubice",
    "градец кралове": "hradec králové",
    "усти над лабем": "ústí nad labem",
    "усти": "ústí nad labem",
    "чески будейовице": "české budějovice",
    "будейовице": "české budějovice",
    "гавиржов": "havířov",
    "кладно": "kladno",
    "мост": "most",
    "опава": "opava",
    "фридек мистек": "frýdek-místek",
    "карвина": "karviná",
    "йиглава": "jihlava",
    "теплице": "teplice",
    "дечин": "děčín",
    "зноймо": "znojmo",
    "годонин": "hodonín",
    "простейов": "prostějov",
    "пршеров": "přerov",
    "тршебич": "třebíč",
    "шлапаниче": "šlapanice",
    "куржим": "kuřim",
    "бланско": "blansko",
    "вышков": "vyškov",
    "бржецлав": "břeclav",
    "кромержиж": "kroměříž",
    "угерске градиште": "uherské hradiště",
    "валашске мезиржичи": "valašské meziříčí",
    "новы йичин": "nový jičín",
    "чески крумлов": "český krumlov",
    "пршибрам": "příbram",
    "млада болеслав": "mladá boleslav",
    "коллин": "kolín",
    "пардубице": "pardubice",
    "хрудим": "chrudim",
    "табор": "tábor",
    "писек": "písek",
    "страконице": "strakonice",
    "йиндржихув градец": "jindřichův hradec",
    "пелгржимов": "pelhřimov",
    # Украинский → чешский
    "брно": "brno",
    "прага": "praha",
    "острава": "ostrava",
    "оломоуць": "olomouc",
    "злін": "zlín",
    "пльзень": "plzeň",
    "ліберець": "liberec",
    "пардубіце": "pardubice",
    "градець кралове": "hradec králové",
}

def normalize_city(city: str) -> str:
    if not city:
        return ""
    return CITY_ALIASES.get(city.lower(), city.lower())


async def save_and_match(listings: list[dict]) -> list[tuple[dict, list[int]]]:
    """
    Принимает список объявлений.
    Возвращает список (объявление, [user_id, user_id, ...]) только для новых.
    """
    pool = await get_pool()
    result = []

    async with pool.acquire() as conn:
        for listing in listings:
            # Защита от объявлений с нераспарсенной ценой (0 = ошибка парсинга, не реальная цена)
            if not listing.get("price") or listing["price"] <= 0:
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