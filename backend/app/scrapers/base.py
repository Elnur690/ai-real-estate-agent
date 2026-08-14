from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class RawListingItem(BaseModel):
    external_id: str
    title: str
    description: Optional[str] = None
    price: float
    currency: str = "AZN"
    district: Optional[str] = None
    metro_station: Optional[str] = None
    address_raw: Optional[str] = None
    phone_number: Optional[str] = None
    rooms: Optional[int] = None
    area_sqm: Optional[float] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    building_type: Optional[str] = None # new | old
    seller_type: Optional[str] = None   # owner | agency
    photos: List[str] = Field(default_factory=list)
    listing_url: str

class BaseScraper(ABC):
    @abstractmethod
    async def scrape_source(self, url_or_handle: str) -> List[RawListingItem]:
        pass
