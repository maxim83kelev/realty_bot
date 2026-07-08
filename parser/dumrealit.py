import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from parser.base import BaseScraper

BASE_URL = "https://www.dumrealit.cz"
LIST_URL = f"{BASE_URL}/nemovitosti/pronajem/byt/razeni-nejnovejsi"

class DumrealiScraper(BaseScraper):
    source_name = "dumrealit"

    def __init__(self, params: dict = None):
        self.params = params or {}

    async def fetch_listings(self) -> list[dict]:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
                page = await browser.new_page()
                await page.goto(LIST_URL)
                await page.wait_for_timeout(3000)
                content = await page.content()
                await browser.close()

            soup = BeautifulSoup(content, "html.parser")
            cards = soup.find_all("a", class_=lambda c: c and "item" in c and "hovout" in c)

            results = []
            seen_ids = set()

            for card in cards:
                href = card.get("href", "")
                if not href:
                    continue

                id_span = card.find("span", class_=lambda c: c and "id" in c and "rgt" in c)
                if id_span:
                    external_id = "".join(filter(str.isdigit, id_span.get_text(strip=True)))
                else:
                    id_match = re.search(r'(\d+)$', href.strip())
                    external_id = id_match.group(1) if id_match else ""

                if not external_id or external_id in seen_ids:
                    continue
                seen_ids.add(external_id)

                url = f"{BASE_URL}{href}" if href.startswith("/") else href

                h3 = card.find("h3")
                title = h3.get_text(strip=True) if h3 else ""

                addr_tag = card.find("p", class_=lambda c: c and "l15h1" in c)
                address = addr_tag.get_text(strip=True) if addr_tag else ""
                city = address.split(",")[0].strip() if "," in address else address
                # "Praha 2 - Vinohrady" → "Praha"
                city = re.split(r'[\d\-]', city)[0].strip()

                price_tag = card.find("span", class_=lambda c: c and "price" in c)
                price_raw = price_tag.get_text(strip=True) if price_tag else ""
                price = 0
                try:
                    price = int("".join(filter(str.isdigit, price_raw.split("Kč")[0])))
                except:
                    pass

                results.append({
                    "external_id": f"dumrealit_{external_id}",
                    "source": self.source_name,
                    "title": address or title,
                    "price": price,
                    "city": city,
                    "property_type": "Pronájem bytu",
                    "url": url,
                })

            return results

        except Exception as e:
            print(f"[DumrealiScraper] Ошибка: {e}")
            return []