import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from parser.base import BaseScraper

BASE_URL = "https://www.studentreality.cz"

CITIES = {
    "brno": "https://www.studentreality.cz/s/Brno?latLng=49.141185%2C16.51311%2C49.248876%2C16.700564",
    "praha": "https://www.studentreality.cz/s/Praha?latLng=49.969631%2C14.250346%2C50.181154%2C14.625255&zoom=10",
}

class StudentrealityScraper(BaseScraper):
    source_name = "studentreality"

    def __init__(self, params: dict = None):
        self.params = params or {}

    async def fetch_listings(self) -> list[dict]:
        try:
            results = []
            seen_ids = set()

            async with async_playwright() as p:
                browser = await p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])

                for city, url in CITIES.items():
                    page = await browser.new_page()
                    await page.goto(url)
                    await page.wait_for_timeout(5000)
                    content = await page.content()
                    await page.close()

                    soup = BeautifulSoup(content, "html.parser")
                    cards = soup.find_all("div", class_=lambda c: c and "offer" in c.split())

                    for card in cards:
                        span = card.find("span", class_=lambda c: c and "js-marker" in c)
                        if not span:
                            continue

                        data_url = span.get("data-url", "")
                        id_match = re.search(r'/redirect/(\d+)', data_url)
                        if not id_match:
                            continue
                        external_id = id_match.group(1)
                        if external_id in seen_ids:
                            continue
                        seen_ids.add(external_id)

                        h2 = card.find("h2")
                        title_link = h2.find("a") if h2 else None
                        title = title_link.get_text(strip=True) if title_link else ""

                        price_div = card.find("div", class_="price")
                        price_raw = price_div.get_text(strip=True) if price_div else ""
                        price = 0
                        try:
                            price = int("".join(filter(str.isdigit, price_raw.split("Kč")[0])))
                        except:
                            pass

                        results.append({
                            "external_id": f"studentreality_{external_id}",
                            "source": self.source_name,
                            "title": title,
                            "price": price,
                            "city": city,
                            "property_type": "Pronájem bytu",
                            "url": data_url,
                        })

                await browser.close()
            return results

        except Exception as e:
            print(f"[StudentrealityScraper] Ошибка: {e}")
            return []