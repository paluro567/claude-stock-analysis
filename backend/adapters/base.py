from abc import ABC, abstractmethod
from datetime import date
from typing import Optional
import pandas as pd


class DataAdapter(ABC):
    @abstractmethod
    def get_price_history(self, ticker: str, days: int = 252) -> pd.DataFrame:
        """
        Returns DataFrame with columns: date, open, high, low, close, volume
        Index should be DatetimeIndex
        """
        pass

    @abstractmethod
    def get_earnings_date(self, ticker: str) -> Optional[date]:
        """Returns the next earnings date for the ticker, or None if unknown."""
        pass

    @abstractmethod
    def get_latest_price(self, ticker: str) -> float:
        """Returns the latest closing price."""
        pass
