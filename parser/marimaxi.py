import httpx
from bs4 import BeautifulSoup
from parser.base import BaseScraper

BASE_URL = "https://marimaxi.cz"
LIST_URL = f"{BASE_URL}/o/PR00"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

class MarimaxiScraper(BaseScraper):
    source_name = "marimaxi"

    def __init__(self, params: dict = None):
        self.params = params or {}

    async def fetch_listings(self) -> list[dict]:
        try:
            async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
                resp = await client.get(LIST_URL, params=self.params)
                resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("div", class_=lambda c: c and "card" in c and "bg-base-300" in c)

            results = []

            for card in cards:
                # ID объявления
                id_tag = card.find("span", class_=lambda c: c and "text-secondary" in c)
                if not id_tag:
                    continue
                id_text = id_tag.get_text(strip=True).replace("ID: ", "")
                if not id_text:
                    continue

                # Ссылка и заголовок
                link = card.find("a", class_=lambda c: c and "card-title" in c)
                if not link:
                    continue
                href = link.get("href", "")
                title = link.get_text(strip=True)
                url = f"{BASE_URL}{href}" if href.startswith("/") else href

                # Цена
                price_tag = card.find("span", class_=lambda c: c and "font-extrabold" in c and "text-primary" in c)
                price_raw = price_tag.get_text(strip=True) if price_tag else ""
                price = 0
                try:
                    price = int("".join(filter(str.isdigit, price_raw)))
                except:
                    pass

                results.append({
                    "external_id": f"marimaxi_{id_text}",
                    "source": self.source_name,
                    "title": title,
                    "price": price,
                    "city": "Praha",
                    "property_type": "Pronájem bytu",
                    "url": url,
                })

            return results

        except Exception as e:
            print(f"[MarimaxiScraper] Ошибка: {e}")
            return []