from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class StructuredCriteria(BaseModel):
    district: Optional[str] = Field(None, description="District or location name(s), e.g., Yasamal, Nəsimi, Xətai")
    metro_station: Optional[str] = Field(None, description="Baku metro station name(s), e.g., Qara Qarayev, Neftçilər, Elmlər Akademiyası")
    locations: List[str] = Field(default_factory=list, description="All requested target districts and metro stations")
    min_price: Optional[float] = Field(None, description="Minimum price in AZN")
    max_price: Optional[float] = Field(None, description="Maximum price in AZN")
    min_price_usd: Optional[float] = Field(None, description="Minimum price in USD")
    max_price_usd: Optional[float] = Field(None, description="Maximum price in USD")
    min_rooms: Optional[int] = Field(None, description="Minimum number of rooms")
    max_rooms: Optional[int] = Field(None, description="Maximum number of rooms")
    min_area: Optional[float] = Field(None, description="Minimum area in sqm")
    max_area: Optional[float] = Field(None, description="Maximum area in sqm")
    seller_type: str = Field("any", description="owner | agency | any")
    building_type: str = Field("any", description="new | old | any")
    summary_az: str = Field("", description="Azerbaijani summary of criteria for confirmation message")


class StructuredListing(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    currency: str = "AZN"
    price_usd: Optional[float] = None
    district: Optional[str] = None
    metro_station: Optional[str] = None
    rooms: Optional[int] = None
    area_sqm: Optional[float] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    building_type: Optional[str] = None
    seller_type: Optional[str] = None
    photos: List[str] = Field(default_factory=list)


class AIProvider(ABC):
    @abstractmethod
    async def parse_search_criteria(self, raw_text: str) -> StructuredCriteria:
        pass

    @abstractmethod
    async def parse_telegram_listing(self, raw_text: str, photos: List[str] = []) -> StructuredListing:
        pass

    @abstractmethod
    async def score_match(self, listing: Dict[str, Any], criteria: StructuredCriteria) -> float:
        pass
