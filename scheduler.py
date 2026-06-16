from apscheduler.schedulers.asyncio import AsyncIOScheduler
from parser.bezrealitky import BezrealitkyScraper
from parser.sreality import SrealitkyScraper
from parser.bravis import BravisScraper
from parser.telegram_channel import TelegramChannelScraper
from matcher import save_and_match
from bot import bot

scheduler = AsyncIOScheduler()

async def parse_and_notify(scrapers=None):
    if scrapers is None:
        return

    for scraper in scrapers:
        listings = await scraper.fetch_listings()
        print(f"[{scraper.source_name}] Найдено: {len(listings)}")

        if not listings:
            continue

        matches = await save_and_match(listings)
        print(f"[{scraper.source_name}] Новых для рассылки: {len(matches)}")

        for listing, user_ids in matches:
            text = (
                f"🏠 {listing['property_type'].replace(chr(160), ' ')}\n"
                f"📍 {listing['title']}\n"
                f"💰 {listing['price']:,} Kč\n"
                f"🔗 {listing['url']}"
            )
            for user_id in user_ids:
                try:
                    await bot.send_message(user_id, text)
                except Exception as e:
                    print(f"[Notify] Не удалось отправить {user_id}: {e}")

def start_scheduler():
    scheduler.add_job(parse_and_notify, "interval", seconds=10, args=[[BezrealitkyScraper(), SrealitkyScraper()]])
    scheduler.add_job(parse_and_notify, "interval", seconds=60, args=[[BravisScraper()]])
    scheduler.add_job(parse_and_notify, "interval", seconds=30, args=[[
        TelegramChannelScraper("sosedi_brno"),
        TelegramChannelScraper("arendakomnatPraha"),
    ]])
    scheduler.start()