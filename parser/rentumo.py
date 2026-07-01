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
            results = []
            seen_ids = set()

            async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
                for page in range(1, 5):  # берём 4 страницы = ~96 объявлений
                    if page == 1:
                        url = LIST_URL
                        params = self.params
                    else:
                        url = LIST_URL
                        params = {"format": "turbo_stream", "page": page, **self.params}

                    resp = await client.get(url, params=params)
                    if resp.status_code == 304:
                        break
                    resp.raise_for_status()

                    soup = BeautifulSoup(resp.text, "html.parser")
                    cards = soup.find_all("div", class_=lambda c: c and "listing-item" in c)

                    if not cards:
                        break

                    for card in cards:
                        external_id = card.get("data-listing-id", "")
                        if not external_id or external_id in seen_ids:
                            continue
                        seen_ids.add(external_id)

                        link = card.find("a", href=lambda h: h and "/nabidky/" in h)
                        if not link:
                            continue
                        href = link.get("href", "")
                        url_listing = f"{BASE_URL}{href}" if href.startswith("/") else href

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
                            "url": url_listing,
                        })

            return results

        except Exception as e:
            print(f"[RentumoScraper] Ошибка: {e}")
            return []