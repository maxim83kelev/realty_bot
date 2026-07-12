import httpx
from parser.base import BaseScraper

BASE_URL = "https://www.realingo.cz"
GRAPHQL_URL = f"{BASE_URL}/graphql"

QUERY = """
query SearchOffer($purpose: OfferPurpose, $property: PropertyType, $sort: OfferSort, $first: Int, $skip: Int) {
  searchOffer(
    filter: {purpose: $purpose, property: $property}
    sort: $sort
    first: $first
    skip: $skip
    save: true
  ) {
    items {
      id
      url
      purpose
      property
      createdAt
      price {
        total
        currency
      }
      location {
        address
        addressUrl
      }
    }
    total
  }
}
"""

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/json",
    "Origin": "https://www.realingo.cz",
    "Referer": "https://www.realingo.cz/pronajem_reality/cr/",
}

class RealingScraper(BaseScraper):
    source_name = "realingo"

    def __init__(self, params: dict = None):
        self.params = params or {}

    async def fetch_listings(self) -> list[dict]:
        try:
            payload = {
                "operationName": "SearchOffer",
                "query": QUERY,
                "variables": {
                    "purpose": "RENT",
                    "property": "FLAT",
                    "sort": "NEWEST",
                    "first": 50,
                    "skip": 0,
                }
            }

            async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
                resp = await client.post(GRAPHQL_URL, json=payload)
                resp.raise_for_status()

            data = resp.json()
            items = data.get("data", {}).get("searchOffer", {}).get("items", [])

            results = []
            for item in items:
                external_id = str(item.get("id", ""))
                if not external_id:
                    continue

                url = f"{BASE_URL}{item['url']}" if item.get("url", "").startswith("/") else item.get("url", "")
                price = item.get("price", {}).get("total", 0) or 0
                currency = item.get("price", {}).get("currency", "")

                # Только кроны
                if currency != "CZK":
                    continue

                address = item.get("location", {}).get("address", "")
                address_url = item.get("location", {}).get("addressUrl", "")

                # Город из addressUrl: "Praha,Praha_1" → "Praha"
                city = address_url.split(",")[0].strip() if address_url else ""

                results.append({
                    "external_id": f"realingo_{external_id}",
                    "source": self.source_name,
                    "title": address,
                    "price": price,
                    "city": city.lower(),
                    "property_type": "Pronájem bytu",
                    "url": url,
                })

            return results

        except Exception as e:
            print(f"[RealingScraper] Ошибка: {e}")
            return []