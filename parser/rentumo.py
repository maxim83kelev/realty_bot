import httpx
from bs4 import BeautifulSoup
from parser.base import BaseScraper

BASE_URL = "https://rentumo.cz"
LIST_URL = f"{BASE_URL}/pronajmy"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "cs-CZ,cs;q=0.9",
}

class RentumoScraper(BaseScraper):
    source_name = "rentumo"

    def __init__(self, params: dict = None):
        self.params = params or {}

    async def fetch_listings(self) -> list[dict]:
        try:
            async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
                resp = await client.get(LIST_URL, params=self.params)
                resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            listings_div = soup.find("div", id="listings")

            if not listings_div:
                print("[RentumoScraper] #listings не найден")
                return []

            cards = listings_div.find_all("div", class_=lambda c: c and "listing-item" in c)
            results = []

            for card in cards:
                external_id = card.get("data-listing-id", "")
                if not external_id:
                    continue

                link = card.find("a", href=lambda h: h and "/nabidky/" in h)
                if not link:
                    continue
                href = link.get("href", "")
                url = f"{BASE_URL}{href}" if href.startswith("/") else href

                city_tag = card.find("p", class_=lambda c: c and "font-semibold" in c)
                city_raw = city_tag.get_text(strip=True) if city_tag else ""

                price_tag = card.find("strong", class_=lambda c: c and "text-2xl" in c)
                price_raw = price_tag.get_text(strip=True) if price_tag else ""
                price = 0
                try:
                    price = int("".join(filter(str.isdigit, price_raw)))
                except:
                    pass

                results.append({
                    "external_id": f"rentumo_{external_id}",
                    "source": self.source_name,
                    "title": city_raw,
                    "price": price,
                    "city": city_raw.split(",")[0].strip() if "," in city_raw else city_raw,
                    "property_type": "Pronájem bytu",
                    "url": url,
                })

            return results

        except Exception as e:
            print(f"[RentumoScraper] Ошибка: {e}")
            return []