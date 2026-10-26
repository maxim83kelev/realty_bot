import re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from parser.base import BaseScraper

BASE_URL = "https://www.reality-proradost.cz"
LIST_URL = f"{BASE_URL}/pronajem/byty/?hideFilter=1"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

DISPOSITION_RE = re.compile(r'\b(\d)\s*\+\s*(kk|\d)\b', re.IGNORECASE)


def detect_disposition(text):
    t = text or ""
    m = DISPOSITION_RE.search(t)
    if m:
        return f"{m.group(1)}+{m.group(2).lower()}"
    if "garson" in t.lower():
        return "garsoniéra"
    return None


class ProradostScraper(BaseScraper):
    source_name = "proradost"

    def __init__(self, params: dict = None):
        self.params = params or {}

    async def fetch_listings(self) -> list[dict]:
        try:
            async with async_playwright() as p:
                b = await p.chromium.launch(args=["--disable-blink-features=AutomationControlled"])
                ctx = await b.new_context(user_agent=UA, locale="cs-CZ")
                pg = await ctx.new_page()
                await pg.goto(LIST_URL, wait_until="networkidle", timeout=60000)
                await pg.wait_for_timeout(12000)   # Anubis proof-of-work
                await pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await pg.wait_for_timeout(2500)     # подгрузка ленивых фото
                html = await pg.content()
                await b.close()

            soup = BeautifulSoup(html, "html.parser")
            results = []

            for card in soup.select("article.estateListItem"):
                link = card.select_one("h2.estateListItem-title a[href*='/reality/']")
                if not link:
                    continue
                href = link.get("href", "")
                m_id = re.search(r'-(\d+)/?$', href.rstrip("/"))
                if not m_id:
                    continue
                ext_id = m_id.group(1)
                title = link.get_text(strip=True)

                # цена
                price = 0
                pr = card.select_one(".estateListItem-price")
                if pr:
                    raw = pr.get_text(" ", strip=True).split("Kč")[0]
                    digits = re.sub(r'[^\d]', '', raw)
                    if digits:
                        price = int(digits)
                if price <= 0 or price > 1_000_000:
                    continue

                # город
                city = ""
                loc = card.select_one(".estateListItem-locality")
                if loc:
                    city = loc.get_text(strip=True)

                disposition = detect_disposition(title)

                # фото объекта (/zs/foto/), аватар маклера (/uzivatele/) пропускаем
                images = []
                for img in card.select("figure img"):
                    src = img.get("src") or img.get("data-src") or ""
                    if "/zs/foto/" in src:
                        full = src if src.startswith("http") else f"{BASE_URL}{src}"
                        if full not in images:
                            images.append(full)
                    if len(images) >= 3:
                        break

                url = href if href.startswith("http") else f"{BASE_URL}{href}"

                results.append({
                    "external_id": f"proradost_{ext_id}",
                    "source": self.source_name,
                    "title": title,
                    "price": price,
                    "city": city,
                    "property_type": "Pronájem bytu",
                    "disposition": disposition,
                    "url": url,
                    "image_urls": images,
                })

            return results

        except Exception as e:
            print(f"[ProradostScraper] Ошибка: {e}")
            return []