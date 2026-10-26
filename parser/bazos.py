import re
import httpx
from bs4 import BeautifulSoup
from parser.base import BaseScraper

BASE_URL = "https://reality.bazos.cz"
LIST_URL = f"{BASE_URL}/pronajmu/byt/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "cs-CZ,cs;q=0.9",
}

DISPOSITION_RE = re.compile(r'\b(\d)\s*\+\s*(kk|\d)\b', re.IGNORECASE)


def detect_disposition(text):
    t = text or ""
    m = DISPOSITION_RE.search(t)
    if m:
        return f"{m.group(1)}+{m.group(2).lower()}"
    if "garson" in t.lower():
        return "garsoniéra"
    return None


class BazosScraper(BaseScraper):
    source_name = "bazos"

    def __init__(self, params: dict = None):
        self.params = params or {}

    async def fetch_listings(self) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
                r = await c.get(LIST_URL, headers=HEADERS)
                r.raise_for_status()

            soup = BeautifulSoup(r.text, "html.parser")
            results = []

            for block in soup.select("div.inzeraty"):
                link = block.select_one("h2.nadpis a[href*='/inzerat/']")
                if not link:
                    continue
                href = link.get("href", "")
                m_id = re.search(r'/inzerat/(\d+)/', href)
                if not m_id:
                    continue
                ext_id = m_id.group(1)

                title = link.get_text(strip=True)

                # цена
                price = 0
                cena = block.select_one("div.inzeratycena")
                if cena:
                    digits = re.sub(r'[^\d]', '', cena.get_text())
                    if digits:
                        price = int(digits)
                if price <= 0 or price > 1_000_000:
                    continue

                # город: первая строка div.inzeratylok (до почтового индекса)
                city = ""
                lok = block.select_one("div.inzeratylok")
                if lok:
                    city = lok.get_text("\n", strip=True).split("\n")[0].strip()

                # диспозиция: из заголовка, запасной — из описания
                disposition = detect_disposition(title)
                if not disposition:
                    popis = block.select_one("div.popis")
                    if popis:
                        disposition = detect_disposition(popis.get_text())

                url = href if href.startswith("http") else f"{BASE_URL}{href}"

                results.append({
                    "external_id": f"bazos_{ext_id}",
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
            print(f"[BazosScraper] Ошибка: {e}")
            return []