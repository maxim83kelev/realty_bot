import asyncpg
from db import get_pool

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
    "ищу", "ищем", "сниму", "снимем", "нужна квартира", "нужна комната",
    # Украинский
    "шукаю", "шукаємо", "зніму", "знімемо", "потрібна квартира", "підселюся",
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
            # Защита от объявлений с нераспарсенной ценой (0 = ошибка парсинга, не реальная цена)
            if not listing.get("price") or listing["price"] <= 0:
                print(f"[ZeroPrice] source={listing.get('source')} city={listing.get('city')} title={listing.get('title')[:80]} url={listing.get('url')}")
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