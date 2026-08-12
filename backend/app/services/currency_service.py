import logging
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Tuple

logger = logging.getLogger(__name__)

# Fallback default exchange rate (1 USD = 1.70 AZN as set by Central Bank of Azerbaijan)
DEFAULT_USD_AZN_RATE = 1.7000

class CurrencyService:
    _cached_rate: float = DEFAULT_USD_AZN_RATE
    _last_fetched: datetime = None

    @classmethod
    async def get_usd_azn_rate(cls) -> float:
        """
        Fetch real-time USD/AZN exchange rate from Central Bank of Azerbaijan (cbar.az).
        Caches result in memory for 12 hours.
        """
        now = datetime.now(timezone.utc)
        if cls._last_fetched and (now - cls._last_fetched) < timedelta(hours=12):
            return cls._cached_rate

        try:
            today_str = now.strftime("%d.%m.%Y")
            url = f"https://www.cbar.az/currencies/{today_str}.xml"
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    root = ET.fromstring(res.text)
                    for valType in root.findall("ValType"):
                        for valute in valType.findall("Valute"):
                            if valute.get("Code") == "USD":
                                val_elem = valute.find("Value")
                                if val_elem is not None and val_elem.text:
                                    rate = float(val_elem.text.replace(",", "."))
                                    cls._cached_rate = rate
                                    cls._last_fetched = now
                                    logger.info(f"[CurrencyService] Live CBAR USD/AZN rate fetched: {rate}")
                                    return rate
        except Exception as e:
            logger.warning(f"[CurrencyService] Could not fetch live CBAR rate: {e}. Using fallback rate {DEFAULT_USD_AZN_RATE}")

        return cls._cached_rate

    @classmethod
    async def convert_to_azn(cls, amount: float, currency: str) -> float:
        """Convert any amount in USD or EUR to AZN."""
        curr = currency.upper().strip()
        if curr in ["USD", "$", "DOLLAR"]:
            rate = await cls.get_usd_azn_rate()
            return round(amount * rate, 2)
        return amount

    @classmethod
    async def convert_azn_to_usd(cls, amount_azn: float) -> float:
        """Convert AZN amount to USD."""
        rate = await cls.get_usd_azn_rate()
        if rate <= 0:
            return round(amount_azn / 1.70, 2)
        return round(amount_azn / rate, 2)
