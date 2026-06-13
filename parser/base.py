from abc import ABC, abstractmethod

class BaseScraper(ABC):
    
    source_name: str = ""
    
    @abstractmethod
    async def fetch_listings(self) -> list[dict]:
        """
        Возвращает список объявлений в формате:
        {
            "external_id": str,
            "title": str,
            "price": int,
            "city": str,
            "property_type": str,
            "url": str
        }
        """
        pass