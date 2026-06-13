import httpx
from bs4 import BeautifulSoup
from parser.base import BaseScraper

BASE_URL = "https://www.sreality.cz"
LIST_URL = f"{BASE_URL}/hledani/pronajem/byty"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "cs-CZ,cs;q=0.9",
}

class SrealitkyScraper(BaseScraper):
    source_name = "sreality"

    def __init__(self, params: dict = None):
        self.params = params or {}

    async def fetch_listings(self) -> list[dict]:
        try:
            async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
                resp = await client.get(LIST_URL, params=self.params)
                resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            estate_list = soup.find("ul", attrs={"data-e2e": "estates-list"})

            if not estate_list:
                print("[SrealitkyScraper] Список не найден")
                return []

            items = estate_list.find_all("li", id=lambda i: i and "estate-list-item-" in i)
            results = []

            for item in items:
                # ID из атрибута li
                item_id = item.get("id", "")
                external_id = item_id.replace("estate-list-item-", "")
                if not external_id.isdigit():
                    continue

                # Ссылка
                link = item.find("a", href=lambda h: h and "/detail/" in h)
                if not link:
                    continue
                href = link.get("href", "")
                url = f"{BASE_URL}{href}" if href.startswith("/") else href

                # Параграфы с данными
                paragraphs = item.find_all("p")
                texts = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]

                title = texts[0] if len(texts) > 0 else ""
                address = texts[1] if len(texts) > 1 else ""
                price_raw = texts[2] if len(texts) > 2 else ""

                # Цена: "18 000 Kč/měsíc" → 18000
                price = 0
                try:
                    price = int("".join(filter(str.isdigit, price_raw.split("Kč")[0])))
                except:
                    pass

                # Город из адреса
                city = ""
                if "," in address:
                    city_part = address.split(",")[1].strip()
                    city = city_part.split("-")[0].strip() if "-" in city_part else city_part

                results.append({
                    "external_id": external_id,
                    "source": self.source_name,
                    "title": address,
                    "price": price,
                    "city": city,
                    "property_type": title,
                    "url": url,
                })

            return results

        except Exception as e:
            print(f"[SrealitkyScraper] Ошибка: {e}")
            return []