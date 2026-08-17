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
    offer_type: str = Field("sale", description="sale | rent | any")
    property_type: str = Field("apartment", description="apartment | house | office | commercial | land | any")
    min_months_on_market: Optional[int] = Field(None, description="Minimum months property on market / lookback (e.g. 3 for '3 aydan bəri')")
    
    # Advanced criteria filters
    not_first_last_floor: bool = Field(False, description="True if 1st and top floors should be excluded")
    min_floor: Optional[int] = Field(None, description="Minimum floor")
    max_floor: Optional[int] = Field(None, description="Maximum floor")
    has_kupcha: Optional[bool] = Field(None, description="True if only deed/kupcha properties requested")
    is_mortgageable: Optional[bool] = Field(None, description="True if only mortgage-eligible properties requested")
    is_repaired: Optional[bool] = Field(None, description="True if only repaired properties requested")

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
    offer_type: Optional[str] = "sale"
    property_type: Optional[str] = "apartment"
    photos: List[str] = Field(default_factory=list)


class AIProvider(ABC):
    @abstractmethod
    async def parse_search_criteria(self, raw_text: str) -> StructuredCriteria:
        pass

    @abstractmethod
    async def score_match(self, criteria: StructuredCriteria, listing: Dict[str, Any]) -> float:
        pass
