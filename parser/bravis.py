from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from parser.base import BaseScraper

import re

BASE_URL = "https://www.bravis.cz"
LIST_URL = f"{BASE_URL}/pronajem-bytu"

DISPOSITION_RE = re.compile(r'\b(\d\s*\+\s*(?:kk|\d))\b', re.IGNORECASE)

class BravisScraper(BaseScraper):
    source_name = "bravis"

    def __init__(self, params: dict = None):
        self.params = params or {}

    async def fetch_listings(self) -> list[dict]:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
                page = await browser.new_page()
                await page.goto(LIST_URL)
                await page.wait_for_timeout(2000)
                content = await page.content()
                await browser.close()

            soup = BeautifulSoup(content, "html.parser")
            results = []
            seen_ids = set()

            items = soup.find_all("div", class_="item")

            for item in items:
                h1 = item.find("h1")
                if not h1:
                    continue

                link = item.find("a", href=lambda h: h and "/pronajem-bytu-" in h and len(h) > 20)
                if not link:
                    continue

                href = link.get("href", "")
                external_id = href.rstrip("/").split("-")[-1]
                if not external_id or external_id in seen_ids:
                    continue
                seen_ids.add(external_id)

                url = f"{BASE_URL}{href}" if href.startswith("/") else href
                title = h1.get_text(strip=True)

                price_tag = item.find("strong", class_="price")
                price_raw = price_tag.get_text(strip=True) if price_tag else ""
                price = 0
                try:
                    price = int("".join(filter(str.isdigit, price_raw.split("Kč")[0])))
                except:
                    pass

                location_tag = item.find("span", class_=lambda c: c and "location" in c)
                location = location_tag.get_text(strip=True) if location_tag else ""
                city = location.split(",")[0].strip() if "," in location else location

                # Город из заголовка
                city = ""
                for keyword in ["Brno", "Praha", "Ostrava", "Olomouc", "Zlín", "Plzeň"]:
                    if keyword in title:
                        city = keyword
                        break

                # Диспозиция из заголовка: "Pronájem bytu 2+kk, 55 m²" → "2+kk"
                disposition = None
                m = DISPOSITION_RE.search(title)
                if m:
                    disposition = m.group(1).replace(" ", "").lower()
                elif "garson" in title.lower():
                    disposition = "garsoniéra"

                results.append({
                    "external_id": f"bravis_{external_id}",
                    "source": self.source_name,
                    "title": title,
                    "price": price,
                    "city": city,
                    "property_type": "Pronájem bytu",
                    "disposition": disposition,
                    "url": url,
                })

            return results

        except Exception as e:
            print(f"[BravisScraper] Ошибка: {e}")
            return []