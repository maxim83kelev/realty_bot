import httpx
import re
from bs4 import BeautifulSoup
from parser.base import BaseScraper

BASE_URL = "https://www.realcity.cz"
LIST_URL = f"{BASE_URL}/pronajem-bytu?list-perPage=100&list-sort=updated-desc"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "cs-CZ,cs;q=0.9",
}

class RealcityScraper(BaseScraper):
    source_name = "realcity"

    def __init__(self, params: dict = None):
        self.params = params or {}

    async def fetch_listings(self) -> list[dict]:
        try:
            async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
                resp = await client.get(LIST_URL)
                resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("div", class_=lambda c: c and "advertise" in c and "item" in c)

            results = []
            seen_ids = set()

            for card in cards:
                external_id = card.get("data-advertise", "")
                if not external_id or external_id in seen_ids:
                    continue
                seen_ids.add(external_id)

                link = card.find("a", href=lambda h: h and "/nemovitost/" in h)
                if not link:
                    continue
                href = link.get("href", "")
                url = f"{BASE_URL}{href}" if href.startswith("/") else href
                title = link.get_text(strip=True)

                addr_tag = card.find("div", class_="address")
                address = addr_tag.get_text(strip=True) if addr_tag else ""
                city = re.split(r'[\d,]', address)[0].strip() if address else ""

                price_tag = card.find("span", class_="highlight")
                price_raw = price_tag.get_text(strip=True) if price_tag else ""
                price = 0
                try:
                    price = int("".join(filter(str.isdigit, price_raw.split("Kč")[0])))
                except:
                    pass

                results.append({
                    "external_id": f"realcity_{external_id}",
                    "source": self.source_name,
                    "title": address or title,
                    "price": price,
                    "city": city.lower(),
                    "property_type": "Pronájem bytu",
                    "url": url,
                })

            return results

        except Exception as e:
            print(f"[RealcityScraper] Ошибка: {e}")
            return []