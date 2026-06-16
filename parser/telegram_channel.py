import os
import re
from telethon import TelegramClient
from telethon.sessions import StringSession
from parser.base import BaseScraper

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION = os.getenv("TELEGRAM_SESSION", "")

CHANNELS = [
    "sosedi_brno",
    "arendakomnatPraha",
]

ROOM_KEYWORDS = [
    "комната", "комнату", "комнаты",
    "койко-место", "койкоместо", "койко место",
    "место в комнате", "одно место", "два места", "три места",
    "1 место", "2 места", "3 места",
    "подселение", "подсел", "подселюсь",
    "сосед", "соседа", "соседку", "соседей", "соседка",
    "подруга по комнате", "подруга по квартире",
    "свободное место",
    "кімната", "кімнату", "кімнати",
    "місце в кімнаті", "одне місце",
    "сусід", "сусідка", "сусідів",
    "підселення",
    "spolubydlení", "spolubydlící", "pokoj", "pokoje",
    "volné místo", "jedno místo",
]

FLAT_KEYWORDS = [
    "квартира", "квартиру", "квартиры", "квартирка",
    "апартаменты", "апартаменти", "апартамент",
    "гарсонка", "гарсоньєрка",
    "студия", "студию",
    "квартири", "студія",
    "byt", "bytu", "byty", "garsoniéra", "garsoniera",
    "flat", "apartment",
    "1+kk", "2+kk", "3+kk", "4+kk", "5+kk",
    "1+1", "2+1", "3+1", "4+1",
    "1кк", "2кк", "3кк",
]

KNOWN_CITIES = [
    "Brno", "Praha", "Ostrava", "Olomouc", "Zlín", "Plzeň",
    "Liberec", "Hradec Králové", "České Budějovice", "Pardubice",
    "Ústí nad Labem", "Havířov", "Kladno", "Most", "Opava",
    "Frýdek-Místek", "Karviná", "Jihlava", "Teplice", "Děčín",
    "Znojmo", "Hodonín", "Prostějov", "Přerov", "Třebíč",
    "Šlapanice", "Kuřim", "Blansko", "Vyškov", "Břeclav",
    "Брно", "Прага", "Острава", "Оломоуц", "Злин", "Пльзень",
    "Либерец", "Градец Кралове", "Пардубице",
]

SKIP_WORDS = {
    "квартира", "комната", "аренда", "сдам", "ищу",
    "центре", "районе", "улице", "рядом", "недалеко",
    "пригород", "окраина",
}


def detect_type(text):
    text_lower = text.lower()
    for kw in ROOM_KEYWORDS:
        if kw.lower() in text_lower:
            return "Комната/подселение"
    for kw in FLAT_KEYWORDS:
        if kw.lower() in text_lower:
            return "Pronájem bytu"
    return "Недвижимость"


def extract_price(text):
    matches = re.findall(r'(\d[\d\s]{2,6})\s*(?:kč|крон|czk|кч|кц)', text.lower())
    if matches:
        try:
            return int("".join(filter(str.isdigit, matches[0])))
        except:
            pass
    return 0


def extract_city(text):
    for city in KNOWN_CITIES:
        if city.lower() in text.lower():
            return city
    patterns = [
        r'[вВ]\s+([А-ЯЁA-Z][а-яёa-z]+(?:-[А-ЯЁA-Z][а-яёa-z]+)?)',
        r'г\.\s*([А-ЯЁA-Z][а-яёa-z]+)',
        r'город\s+([А-ЯЁA-Z][а-яёa-z]+)',
        r'в\s+районе\s+([А-ЯЁ][а-яё]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            candidate = match.group(1)
            if candidate.lower() not in SKIP_WORDS:
                return candidate
    return ""


class TelegramChannelScraper(BaseScraper):
    source_name = "telegram"

    def __init__(self, params=None):
        self.params = params or {}

    async def fetch_listings(self):
        if not SESSION:
            print("[TelegramScraper] TELEGRAM_SESSION не задан")
            return []
        try:
            client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
            await client.connect()
            results = []
            for channel in CHANNELS:
                messages = await client.get_messages(channel, limit=20)
                for msg in messages:
                    if not msg.text or len(msg.text) < 20:
                        continue
                    external_id = f"tg_{channel}_{msg.id}"
                    url = f"https://t.me/{channel}/{msg.id}"
                    prop_type = detect_type(msg.text)
                    price = extract_price(msg.text)
                    city = extract_city(msg.text)
                    title = msg.text[:100].replace("\n", " ")
                    results.append({
                        "external_id": external_id,
                        "source": self.source_name,
                        "title": title,
                        "price": price,
                        "city": city,
                        "property_type": prop_type,
                        "url": url,
                    })
            await client.disconnect()
            return results
        except Exception as e:
            print(f"[TelegramScraper] Ошибка: {e}")
            return []