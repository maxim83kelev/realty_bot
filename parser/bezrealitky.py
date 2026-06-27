import httpx
from bs4 import BeautifulSoup
from parser.base import BaseScraper

BASE_URL = "https://www.bezrealitky.cz"
LIST_URL = f"{BASE_URL}/vyhledat"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "cs-CZ,cs;q=0.9",
}

class BezrealitkyScraper(BaseScraper):
    source_name = "bezrealitky"

    def __init__(self, params: dict = None):
        self.params = params or {}

    async def fetch_listings(self) -> list[dict]:
        try:
            async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
                resp = await client.get(LIST_URL, params={
                    "estateType": "BYT",
                    "offerType": "PRONAJEM",
                    "country": "ceska-republika",
                    "locale": "CS",
                    **self.params
                })
                resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("article", class_=lambda c: c and "PropertyCard_propertyCard__" in c)

            results = []
            seen_ids = set()

            for card in cards:
                # URL и external_id
                link = card.find("a", href=lambda h: h and "/nemovitosti-byty-domy/" in h)
                if not link:
                    continue
                href = link["href"]
                parts = href.split("/nemovitosti-byty-domy/")
                if len(parts) < 2:
                    continue
                external_id = parts[1].split("-")[0]
                if not external_id.isdigit() or external_id in seen_ids:
                    continue
                seen_ids.add(external_id)

                # Текстовые спаны
                spans = [s.get_text(strip=True) for s in card.find_all("span") if s.get_text(strip=True) and len(s.get_text(strip=True)) < 100]
                unique_spans = list(dict.fromkeys(spans))  # убираем дубли сохраняя порядок

                # Тип: "Pronájem bytu", "Prodej bytu" и т.д.
                prop_type = ""
                for s in unique_spans:
                    if "nájem" in s or "rodej" in s or "Pron" in s or "Prod" in s:
                        prop_type = s
                        break

                # Адрес: содержит запятую и город
                address = ""
                for s in unique_spans:
                    if "," in s and len(s) > 5:
                        address = s
                        break

                # Цена: содержит "Kč" и нет "/"
                price_raw = ""
                for s in unique_spans:
                    if "Kč" in s and "/" not in s and "+" not in s:
                        price_raw = s
                        break

                # Парсим цену
                price = 0
                try:
                    price = int("".join(filter(str.isdigit, price_raw)))
                except:
                    pass

                # Город из адреса: "Jeřabinová, Praha - Smíchov" → "Praha"
                city = ""
                if "," in address:
                    city_part = address.split(",")[1].strip()
                    city = city_part.split("-")[0].strip() if "-" in city_part else city_part
                    
                # Фильтр не-чешских объявлений (Германия и т.д.)
                NON_CZECH_MARKERS = [
                    "Germany", "Deutschland", "Berlin", "Frankfurt", "Hamburg",
                    "München", "Munich", "Dresden", "Leipzig", "Chemnitz",
                    "Hessen", "Bayern", "Sachsen",
                ]
                full_text = f"{address} {city}".lower()
                if any(marker.lower() in full_text for marker in NON_CZECH_MARKERS):
                    continue    

                results.append({
                    "external_id": external_id,
                    "source": self.source_name,
                    "title": address,
                    "price": price,
                    "city": city,
                    "property_type": prop_type,
                    "url": href if href.startswith("http") else f"{BASE_URL}{href}",
                })

            return results

        except Exception as e:
            print(f"[BezrealitkyScraper] Ошибка: {e}")
            return []