import asyncpg
from config import DATABASE_URL

pool = None

async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    await create_tables()

async def create_tables():
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                username TEXT,
                language TEXT DEFAULT 'ru',
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS user_filters (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                city TEXT,
                price_min INTEGER,
                price_max INTEGER,
                property_type TEXT
            );

            CREATE TABLE IF NOT EXISTS listings (
                id SERIAL PRIMARY KEY,
                source TEXT NOT NULL,
                external_id TEXT UNIQUE NOT NULL,
                title TEXT,
                price INTEGER,
                city TEXT,
                property_type TEXT,
                url TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
            
            CREATE TABLE IF NOT EXISTS banned_users (
                user_id BIGINT PRIMARY KEY,
                reason TEXT,
                banned_at TIMESTAMP DEFAULT NOW()
            );
        """)

async def get_pool():
    return pool