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


# Правила извлечения фото по сайтам (regex по HTML страницы).
# Чтобы добавить новый сайт с открытыми фото — допиши запись: домен → (регулярка пути, префикс).
PHOTO_RULES = [
    ("realingo.cz", r'/static/images/offer/[^\s"\'?]+\.webp', "https://www.realingo.cz"),
    ("realcity.cz", r'//media\.realcity\.cz/files/resized/[^\s"\'?]+\.jpe?g', "https:"),
]

# sreality отдаёт фото не в HTML, а через API, и ссылки требуют параметров ?fl=...
SREALITY_IMG_SUFFIX = "?fl=res,800,800,1|shr,,20|webp,60"


async def fetch_sreality_photos(url: str, limit: int = 3) -> list[str]:
    """Фото sreality — через официальный API по ID объявления."""
    m = re.search(r'(\d{6,})', url)  # ID sreality — длинное число (9-10 цифр)
    if not m:
        return []
    eid = m.group(1)
    try:
        api = f"https://www.sreality.cz/api/v1/estates/{eid}"
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(api, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        await asyncio.sleep(0.3)
        imgs = r.json().get("result", {}).get("advert_images", [])
        out = []
        for im in imgs[:limit]:
            u = im.get("url", "")
            if u:
                out.append(f"https:{u}{SREALITY_IMG_SUFFIX}")
        return out
    except Exception as e:
        print(f"[fetch_photos sreality] {url}: {e}")
        return []


async def fetch_photos(url: str, limit: int = 3) -> list[str]:
    """Первые N уникальных фото объявления. sreality — через API, остальные — regex по HTML."""
    if not url:
        return []

    if "sreality.cz" in url:
        return await fetch_sreality_photos(url, limit)

    rule = next((r for r in PHOTO_RULES if r[0] in url), None)
    if rule is None:
        return []  # для этого сайта фото пока не поддерживаем — уйдёт текстом
    _, pattern, prefix = rule

    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url, headers={"User-Agent": "Mozilla/5.0"})
        await asyncio.sleep(0.3)  # пауза после запроса страницы

        found = re.findall(pattern, r.text)
        seen, out = set(), []
        for p in found:
            full = f"{prefix}{p}"
            if full not in seen:
                seen.add(full)
                out.append(full)
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