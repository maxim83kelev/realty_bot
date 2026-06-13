import asyncpg
from db import get_pool

async def save_and_match(listings: list[dict]) -> list[tuple[dict, list[int]]]:
    """
    Принимает список объявлений.
    Возвращает список (объявление, [user_id, user_id, ...]) только для новых.
    """
    pool = await get_pool()
    result = []

    async with pool.acquire() as conn:
        for listing in listings:
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
                listing["city"],
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
            """, listing["city"], listing["price"], listing["property_type"])

            if users:
                result.append((listing, [u["id"] for u in users]))

    return result