import re
import httpx
from parser.base import BaseScraper

API_URL = "https://ud.api.ulovdomov.cz/v1/offer/find?page=1&perPage=20&sorting=latest"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": "Bearer",           # API так и ходит — пустой Bearer, не трогаем
    "Origin": "https://www.ulovdomov.cz",
    "Referer": "https://www.ulovdomov.cz/",
}

# тело запроса: bounds — рамка на всю Чехию; без него API отдаёт 400/500
BODY = {
    "bounds": {
        "northEast": {"lat": 51.06, "lng": 18.87},
        "southWest": {"lat": 48.55, "lng": 12.09},
    },
    "offerType": "rent",
    "propertyType": "flat",
}

NUM = {"one": "1", "two": "2", "three": "3", "four": "4",
       "five": "5", "six": "6", "seven": "7"}


def map_disposition(d):
    """UlovDomov отдаёт enum: onePlusKk → 1+kk, twoPlusOne → 2+1."""
    if not d:
        return None
    low = d.strip().lower()
    if "garson" in low or low == "studio":
        return "garsoniéra"
    m = re.match(r'([a-z]+)plus([a-z]+)$', low)
    if m:
        a = NUM.get(m.group(1))
        b = "kk" if m.group(2) == "kk" else NUM.get(m.group(2), m.group(2))
        if a:
            return f"{a}+{b}"
    return None


class UlovDomovScraper(BaseScraper):
    source_name = "ulovdomov"

    def __init__(self, params: dict = None):
        self.params = params or {}

    async def fetch_listings(self) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=20) as c:
                r = await c.post(API_URL, headers=HEADERS, json=BODY)
                r.raise_for_status()
            offers = (r.json().get("data") or {}).get("offers") or []

            results = []
            for o in offers:
                ext_id = o.get("id")
                if not ext_id:
                    continue

                # цена
                rp = o.get("rentalPrice") or {}
                price = rp.get("value") or 0 if isinstance(rp, dict) else 0
                if price <= 0 or price > 1_000_000:
                    continue

                # город: village.title, запасные — villagePart/street
                city = ""
                for key in ("village", "villagePart", "street"):
                    node = o.get(key) or {}
                    if isinstance(node, dict) and node.get("title"):
                        city = node["title"].strip()
                        break

                # адрес в title (как у sreality/bezrealitky): "Harrachov, Nový Svět"
                v = (o.get("village") or {}).get("title") or ""
                extra = (o.get("villagePart") or {}).get("title") or (o.get("street") or {}).get("title") or ""
                if extra and extra != v:
                    title = f"{v}, {extra}" if v else extra
                else:
                    title = v or (o.get("title") or "")

                prop_type = "Pronájem domu" if o.get("propertyType") == "house" else "Pronájem bytu"
                disposition = map_disposition(o.get("disposition")) if prop_type == "Pronájem bytu" else None

                images = [ph["path"] for ph in (o.get("photos") or [])
                          if isinstance(ph, dict) and ph.get("path")]

                results.append({
                    "external_id": f"ulovdomov_{ext_id}",
                    "source": self.source_name,
                    "title": title,
                    "price": price,
                    "city": city,
                    "property_type": prop_type,
                    "disposition": disposition,
                    "url": o.get("absoluteUrl") or "",
                    "image_urls": images,
                })

            return results

        except Exception as e:
            print(f"[UlovDomovScraper] Ошибка: {e}")
            return []