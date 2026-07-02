import httpx
import re
from bs4 import BeautifulSoup
from parser.base import BaseScraper

BASE_URL = "https://espolubydleni.cz"
LIST_URL = f"{BASE_URL}/podnajem-spolubydlici/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "cs-CZ,cs;q=0.9",
}


class EspolubydleniScraper(BaseScraper):
    source_name = "espolubydleni"

    def init(self, params: dict = None):
        self.params = params or {}

    async def fetch_listings(self) -> list[dict]:
        try:
            results = []
            seen_ids = set()

            async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
                for page in range(1, 4):
                    url = LIST_URL if page == 1 else f"{LIST_URL}{page}"
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        break

                    soup = BeautifulSoup(resp.text, "html.parser")
                    table = soup.find("table", {"cellspacing": "1"})
                    if not table:
                        break

                    all_trs = table.find_all("tr", recursive=False)

                    i = 0
                    while i < len(all_trs):
                        tr = all_trs[i]
                        div3 = tr.find("div", class_=lambda c: c and "res_div3" in c)

                        if div3:
                            text = div3.get_text(separator="|", strip=True)

                            link = div3.find("a", class_="re_2")
                            href = link.get("href", "") if link else ""
                            if not href:
                                i += 1
                                continue

                            id_match = re.search(r'/(\d+)-', href)
                            if not id_match:
                                i += 1
                                continue
                            external_id = id_match.group(1)
                            if external_id in seen_ids:
                                i += 1
                                continue
                            seen_ids.add(external_id)

                            url_listing = f"{BASE_URL}{href}" if href.startswith("/") else href

                            price = 0
                            price_match = re.search(r'(\d[\d\s\.]+)Kč', text)
                            if price_match:
                                try:
                                    price = int("".join(filter(str.isdigit, price_match.group(1))))
                                except Exception:
                                    pass

                            parts = [p.strip() for p in text.split("|") if p.strip()]
                            title = parts[0] if parts else ""

                            city = ""
                            CITIES = [
                                "ceske-budejovice", "hradec-kralove", "usti-nad-labem",
                                "frydek-mistek", "ceska-lipa", "mlada-boleslav",
                                "brno", "praha", "ostrava", "zlin", "olomouc", "plzen",
                                "liberec", "pardubice", "jihlava", "opava", "havirov",
                                "kladno", "most", "karvina", "teplice", "decin",
                                "znojmo", "hodonin", "prostejov", "prerov", "trebic",
                                "slapanice", "kurim", "blansko", "vyskov", "breclav",
                                "kromeriz", "uherske-hradiste", "valasske-mezirici",
                                "novy-jicin", "cesky-krumlov", "pribram", "kolin",
                                "chrudim", "tabor", "pisek", "strakonice",
                                "jindrichuv-hradec", "pelhrimov", "trutnov", "nachod",
                                "jicin", "rychnov", "semily", "liberec", "jablonec",
                                "chomutov", "litvinov", "bilina", "louny", "zatec",
                                "rakovnik", "beroun", "benesov", "kutna-hora",
                                "nymburk", "podebrady", "melnik", "kladno",
                                "rokycany", "domazlice", "klatovy", "susice",
                                "vsetin", "uhersky-brod", "hodonin", "kyjov",
                                "znojmo", "trebic", "vyskov", "breclav",
                                "sumperk", "jesenik", "sternberk", "litomysl",
                                "svitavy", "policka", "hlinsko", "cheb",
                                "sokolov", "karlovy-vary", "marianske-lazne",
                                "frantiskovy-lazne",
                            ]
                            for c in CITIES:
                                if c in href.lower():
                                    city = c.replace("-", " ").title()
                                    break

                            results.append({
                                "external_id": f"espolubydleni_{external_id}",
                                "source": self.source_name,
                                "title": title[:100],
                                "price": price,
                                "city": city,
                                "property_type": "Комната/подселение",
                                "url": url_listing,
                            })
                            i += 2
                        else:
                            i += 1

            return results

        except Exception as e:
            print(f"[EspolubydleniScraper] Ошибка: {e}")
            return []