import httpx
from bs4 import BeautifulSoup
from parser.base import BaseScraper

BASE_URL = "https://jiho.moravskereality.cz"
LIST_URL = f"{BASE_URL}/pronajem/byty/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "cs-CZ,cs;q=0.9",
}

class JihomoravskerealityScraper(BaseScraper):
    source_name = "jihomoravskereality"

    def __init__(self, params: dict = None):
        self.params = params or {}

    async def fetch_listings(self) -> list[dict]:
        try:
            async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
                resp = await client.get(LIST_URL, params=self.params)
                resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            articles = soup.find_all("article", class_=lambda c: c and "i-estate" in c.split())

            results = []

            for article in articles:
                link = article.find("a", class_=lambda c: c and "i-estate__title-link" in c)
                if not link:
                    continue

                href = link.get("href", "")
                title = link.get_text(strip=True)

                # ID из конца URL: ...-3754549.html
                external_id = href.rstrip("/").split("-")[-1].replace(".html", "")
                if not external_id.isdigit():
                    continue

                url = href if href.startswith("http") else f"{BASE_URL}{href}"

                price_tag = article.find("h3", class_=lambda c: c and "footer-price-value" in c)
                price_raw = price_tag.get_text(strip=True) if price_tag else ""
                price = 0
                try:
                    price = int("".join(filter(str.isdigit, price_raw.split("Kč")[0])))
                except:
                    pass

                # Город из заголовка: "Pronájem bytu 3+kk 75 m² Luhačovice, Výsluní"
                city = ""
                if "," in title:
                    parts = title.split(",")[0].split()
                    if parts:
                        city = parts[-1]

                results.append({
                    "external_id": external_id,
                    "source": self.source_name,
                    "title": title,
                    "price": price,
                    "city": city,
                    "property_type": "Pronájem bytu",
                    "url": url,
                })

            return results

        except Exception as e:
            print(f"[JihomoravskerealityScraper] Ошибка: {e}")
            return []