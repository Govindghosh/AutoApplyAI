import httpx
from app.core.logging import logger
import asyncio

class CurrencyService:
    _rates_cache = {}
    _last_updated = 0
    CACHE_TTL = 3600 # 1 hour

    @classmethod
    async def get_rates(cls, base: str = "USD"):
        # For simplicity, we'll use a public API. 
        # In production, use a reliable paid service.
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://api.exchangerate-api.com/v4/latest/{base}")
                if response.status_code == 200:
                    data = response.json()
                    return data.get("rates", {})
        except Exception as e:
            logger.error(f"Failed to fetch currency rates: {e}")
        
        # Fallback rates (Approximate)
        return {
            "USD": 1.0,
            "INR": 83.0,
            "EUR": 0.92,
            "GBP": 0.79
        }

    @classmethod
    async def convert(cls, amount: float, from_currency: str, to_currency: str) -> float:
        if from_currency == to_currency:
            return amount
        
        rates = await cls.get_rates(from_currency)
        rate = rates.get(to_currency)
        
        if rate:
            return round(amount * rate, 2)
        
        return amount

    @classmethod
    async def get_salary_in_multiple_currencies(cls, amount: float, base_currency: str = "USD"):
        """
        Returns salary in common currencies based on the input base currency
        """
        rates = await cls.get_rates(base_currency)
        return {
            "USD": round(amount * rates.get("USD", 1.0), 2),
            "INR": round(amount * rates.get("INR", 83.0), 2),
            "EUR": round(amount * rates.get("EUR", 0.92), 2),
        }
