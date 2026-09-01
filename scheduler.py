from apscheduler.schedulers.asyncio import AsyncIOScheduler
import re
import asyncio
import httpx
from aiogram.types import InputMediaPhoto
from parser.bezrealitky import BezrealitkyScraper
from parser.jihomoravskereality import JihomoravskerealityScraper
from parser.sreality import SrealitkyScraper
from parser.bravis import BravisScraper
from parser.telegram_channel import TelegramChannelScraper
from matcher import save_and_match
from bot import bot
from parser.rentumo import RentumoScraper
from parser.marimaxi import MarimaxiScraper
from parser.espolubydleni import EspolubydleniScraper
from parser.dumrealit import DumrealiScraper
from parser.studentreality import StudentrealityScraper
from parser.realingo import RealingScraper
from parser.realcity import RealcityScraper

scheduler = AsyncIOScheduler()


async def fetch_photos(url: str, limit: int = 3) -> list[str]:
    """Тянет первые N фото со страницы объявления. Пауза между запросами — чтобы сайт не принял за скрейпера."""
    if not url:
        return []
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url, headers={"User-Agent": "Mozilla/5.0"})
        await asyncio.sleep(0.3)  # пауза после запроса страницы
        # ссылки вида /static/images/offer/xxx/yyy-900x1200xd0d0d0.webp
        found = re.findall(r'/static/images/offer/[^\s"\'?]+\.webp', r.text)
        seen, out = set(), []
        for p in found:
            if p not in seen:
                seen.add(p)
                out.append(f"https://www.realingo.cz{p}")
            if len(out) >= limit:
                break
        return out
    except Exception as e:
        print(f"[fetch_photos] {url}: {e}")
        return []


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
            try:
                text = (
                    f"🏠 {(listing.get('property_type') or '').replace(chr(160), ' ')}\n"
                    f"📍 {listing.get('title') or ''}\n"
                    f"💰 {listing.get('price') or 0:,} Kč\n"
                    f"🔗 {listing.get('url') or ''}"
                )

                # Фото: сначала то, что дал парсер; если нет — тянем со страницы объявления
                images = listing.get("image_urls") or []
                if not images and listing.get("url"):
                    images = await fetch_photos(listing["url"], limit=3)
                images = images[:3]

                for user_id in user_ids:
                    try:
                        if images:
                            media = [
                                InputMediaPhoto(media=img, caption=text if i == 0 else None)
                                for i, img in enumerate(images)
                            ]
                            await bot.send_media_group(user_id, media)
                        else:
                            await bot.send_message(user_id, text)
                    except Exception as e:
                        # альбом не ушёл (битые фото / лимит) — шлём текстом, объявление не теряем
                        print(f"[Notify] альбом не ушёл {user_id}: {e}")
                        try:
                            await bot.send_message(user_id, text)
                        except Exception as e2:
                            print(f"[Notify] и текст не ушёл {user_id}: {e2}")
            except Exception as e:
                # одно битое объявление не должно ронять всю рассылку
                print(f"[Notify] объявление пропущено ({listing.get('url', '?')}): {e}")
                continue
def start_scheduler():
    scheduler.add_job(parse_and_notify, "interval", seconds=10, args=[[BezrealitkyScraper(), SrealitkyScraper(), JihomoravskerealityScraper(), RentumoScraper(), MarimaxiScraper(), EspolubydleniScraper(), RealingScraper(), RealcityScraper()]])
    scheduler.add_job(parse_and_notify, "interval", minutes=5, args=[[BravisScraper(), DumrealiScraper(), StudentrealityScraper()]])
    scheduler.add_job(parse_and_notify, "interval", seconds=30, args=[[
        TelegramChannelScraper("sosedi_brno"),
        TelegramChannelScraper("arendakomnatPraha"),
        TelegramChannelScraper("superhome_czechia"),
    ]])
    scheduler.start()