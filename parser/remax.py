import re
import httpx
from bs4 import BeautifulSoup
from parser.base import BaseScraper

BASE_URL = "https://www.remax-czech.cz"
LIST_URL = f"{BASE_URL}/reality/byty/pronajem/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "cs-CZ,cs;q=0.9",
}

CITY_KEYWORDS = ["Praha", "Brno", "Ostrava", "Plzeň", "Olomouc", "Liberec", "Zlín",
                 "České Budějovice", "Hradec Králové", "Pardubice", "Ústí nad Labem",
                 "Karlovy Vary", "Jihlava", "Teplice", "Děčín", "Most", "Opava",
                 "Kladno", "Frýdek", "Havířov", "Karviná", "Chomutov", "Znojmo",
                 "Příbram", "Trutnov", "Tábor", "Prostějov", "Přerov", "Mladá Boleslav"]


def detect_disposition(text):
    m = re.search(r'\b(\d)\s*\+\s*(kk|\d)\b', text, re.IGNORECASE)
    if m:
        return f"{m.group(1)}+{m.group(2).lower()}"
    if "garson" in text.lower():
        return "garsoniéra"
    return None


class RemaxScraper(BaseScraper):
    source_name = "remax"

    def __init__(self, params: dict = None):
        self.params = params or {}

    async def fetch_listings(self) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
                r = await c.get(LIST_URL, headers=HEADERS)

            soup = BeautifulSoup(r.text, "html.parser")
            results = []
            seen = set()

            for a in soup.find_all("a", href=lambda h: h and "/reality/detail/" in h):
                href = a["href"]
                m_id = re.search(r'/reality/detail/(\d+)/', href)
                if not m_id:
                    continue
                ext_id = m_id.group(1)
                if ext_id in seen:
                    continue

                card = a
                for _ in range(6):
                    card = card.parent
                    if card is None:
                        break
                    if "Kč" in card.get_text():
                        break
                if card is None:
                    continue

                txt = card.get_text(" ", strip=True)

                m_title = re.search(r'(Pron[aá]jem[^\d]*\d[^|]{0,80})', txt)
                title = m_title.group(1).strip() if m_title else txt[:80]

                price = 0
                m_price = re.search(r'([\d\s\xa0]{4,})\s*Kč', txt)
                if m_price:
                    digits = re.sub(r'[^\d]', '', m_price.group(1))
                    if digits:
                        price = int(digits)
                # потолок: мусорную цену не пускаем (урок ceskereality)
                if price <= 0 or price > 1_000_000:
                    continue

                seen.add(ext_id)

                low = title.lower()
                if "pokoj" in low or "spolubyd" in low:
                    prop_type = "Комната/подселение"
                elif "dům" in low or "domu" in low:
                    prop_type = "Pronájem domu"
                else:
                    prop_type = "Pronájem bytu"

                disposition = detect_disposition(title) if prop_type == "Pronájem bytu" else None

                city = ""
                for kw in CITY_KEYWORDS:
                    if kw in title:
                        city = kw
                        break

                url = href if href.startswith("http") else f"{BASE_URL}{href}"

                results.append({
                    "external_id": f"remax_{ext_id}",
                    "source": self.source_name,
                    "title": title,
                    "price": price,
                    "city": city,
                    "property_type": prop_type,
                    "disposition": disposition,
                    "url": url,
                })

            return results

        except Exception as e:
            print(f"[RemaxScraper] Ошибка: {e}")
            return []