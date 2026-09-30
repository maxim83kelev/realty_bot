import re
import httpx
from bs4 import BeautifulSoup
from parser.base import BaseScraper

BASE_URL = "https://realitymix.cz"
LIST_URL = f"{BASE_URL}/reality/byty/pronajem"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "cs-CZ,cs;q=0.9",
}


def detect_disposition(text):
    m = re.search(r'\b(\d)\s*\+\s*(kk|\d)\b', text, re.IGNORECASE)
    if m:
        return f"{m.group(1)}+{m.group(2).lower()}"
    if "garson" in text.lower():
        return "garsoniéra"
    return None


class RealitymixScraper(BaseScraper):
    source_name = "realitymix"

    def __init__(self, params: dict = None):
        self.params = params or {}

    async def fetch_listings(self) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
                r = await c.get(LIST_URL, headers=HEADERS)

            soup = BeautifulSoup(r.text, "html.parser")
            results = []
            seen = set()

            for li in soup.find_all("li", class_=lambda x: x and "advert-item" in x):
                a = li.find("a", href=lambda h: h and "/detail/" in h)
                if not a:
                    continue
                url = a.get("href", "")
                m_id = re.search(r'-(\d+)\.html', url)
                if not m_id:
                    continue
                ext_id = m_id.group(1)
                if ext_id in seen:
                    continue
                seen.add(ext_id)

                img = li.find("img", alt=True)
                alt = img.get("alt", "") if img else ""

                low = alt.lower()
                if "pokoj" in low or "spolubyd" in low:
                    prop_type = "Комната/подселение"
                elif "dům" in low or "domu" in low:
                    prop_type = "Pronájem domu"
                else:
                    prop_type = "Pronájem bytu"

                disposition = detect_disposition(alt) if prop_type == "Pronájem bytu" else None

                m_city = re.search(r'/detail/([a-z-]+)/', url)
                city = m_city.group(1).replace("-", " ") if m_city else ""

                price = 0
                pd = li.find("div", class_=lambda x: x and "font-extrabold" in x)
                if pd:
                    digits = re.sub(r'[^\d]', '', pd.get_text().split("Kč")[0])
                    if digits:
                        price = int(digits)

                results.append({
                    "external_id": f"realitymix_{ext_id}",
                    "source": self.source_name,
                    "title": alt,
                    "price": price,
                    "city": city,
                    "property_type": prop_type,
                    "disposition": disposition,
                    "url": url,
                })

            return results

        except Exception as e:
            print(f"[RealitymixScraper] Ошибка: {e}")
            return []