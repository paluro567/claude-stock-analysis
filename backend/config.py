import os
from pathlib import Path

CLUSTERS = {
    "AI / Semis": ["NVDA", "AMD", "AVGO", "SMCI", "INTC", "QCOM"],
    "AI Software": ["PLTR", "BBAI", "PATH", "NOW", "CRM", "SNOW", "ADBE"],
    "Crypto-Linked": ["COIN", "MARA", "RIOT", "HOOD"],
    "High-Beta Speculative": ["BBAI", "FUBO", "SOFI", "RZLV", "HNST", "HIMS", "GME"],
    "Mega Cap Tech": ["AAPL", "MSFT", "GOOG", "META", "AMZN", "NVDA"],
    "Consumer / Retail": ["NKE", "ELF", "CELH", "CAKE", "EL", "WYNN", "PINS"],
    "Fintech": ["PYPL", "COIN", "HOOD", "SOFI"],
    "Energy / Nuclear": ["URNM", "BE", "VRT"],
    "Telecom / Defensive": ["T", "UNH", "AXP"],
}

MOCK_PRICES = {
    'NVDA': 115, 'AAPL': 195, 'MSFT': 375, 'META': 580, 'AMZN': 205,
    'GOOG': 170, 'SMCI': 35, 'AXP': 290, 'PANW': 175, 'NOW': 850,
    'SNOW': 125, 'PATH': 10, 'BBAI': 3, 'PINS': 28, 'BE': 18,
    'AVGO': 195, 'CRM': 290, 'FUBO': 4, 'ORCL': 155, 'AMD': 88,
    'HIMS': 28, 'RZLV': 2, 'CAKE': 48, 'VRT': 78, 'HOOD': 38,
    'TTD': 75, 'ADBE': 395, 'COIN': 195, 'HNST': 4, 'EL': 58,
    'CELH': 32, 'WYNN': 88, 'ELF': 42, 'NKE': 72, 'GME': 24,
    'T': 22, 'MARA': 14, 'SOFI': 12, 'TSLA': 245, 'PLTR': 85,
    'RIOT': 9, 'UNH': 490, 'PYPL': 62, 'IWM': 198, 'VOO': 515,
    'VTI': 258, 'URNM': 43, 'SPY': 548,
}

DEFAULT_HOLDINGS = {
    "equities": [
        {"ticker": "SMCI", "quantity": 15, "notes": ""},
        {"ticker": "AXP", "quantity": 1, "notes": ""},
        {"ticker": "AMZN", "quantity": 82, "notes": ""},
        {"ticker": "PANW", "quantity": 3, "notes": ""},
        {"ticker": "NOW", "quantity": 35, "notes": ""},
        {"ticker": "SNOW", "quantity": 10, "notes": ""},
        {"ticker": "PATH", "quantity": 660, "notes": ""},
        {"ticker": "BBAI", "quantity": 250, "notes": ""},
        {"ticker": "PINS", "quantity": 80, "notes": ""},
        {"ticker": "BE", "quantity": 3, "notes": ""},
        {"ticker": "AVGO", "quantity": 6, "notes": ""},
        {"ticker": "CRM", "quantity": 63, "notes": ""},
        {"ticker": "FUBO", "quantity": 25, "notes": ""},
        {"ticker": "ORCL", "quantity": 4, "notes": ""},
        {"ticker": "AMD", "quantity": 13, "notes": ""},
        {"ticker": "HIMS", "quantity": 37, "notes": ""},
        {"ticker": "RZLV", "quantity": 642, "notes": ""},
        {"ticker": "CAKE", "quantity": 95, "notes": ""},
        {"ticker": "VRT", "quantity": 3, "notes": ""},
        {"ticker": "HOOD", "quantity": 15, "notes": ""},
        {"ticker": "TTD", "quantity": 30, "notes": ""},
        {"ticker": "ADBE", "quantity": 44, "notes": ""},
        {"ticker": "GOOG", "quantity": 12, "notes": ""},
        {"ticker": "COIN", "quantity": 12, "notes": ""},
        {"ticker": "HNST", "quantity": 2800, "notes": ""},
        {"ticker": "EL", "quantity": 20, "notes": ""},
        {"ticker": "CELH", "quantity": 120, "notes": ""},
        {"ticker": "WYNN", "quantity": 20, "notes": ""},
        {"ticker": "ELF", "quantity": 25, "notes": ""},
        {"ticker": "NKE", "quantity": 95, "notes": ""},
        {"ticker": "GME", "quantity": 1, "notes": ""},
        {"ticker": "NVDA", "quantity": 20, "notes": ""},
        {"ticker": "T", "quantity": 40, "notes": ""},
        {"ticker": "AAPL", "quantity": 8, "notes": ""},
        {"ticker": "MARA", "quantity": 292, "notes": ""},
        {"ticker": "SOFI", "quantity": 145, "notes": ""},
        {"ticker": "META", "quantity": 8, "notes": ""},
        {"ticker": "TSLA", "quantity": 17, "notes": ""},
        {"ticker": "PLTR", "quantity": 49, "notes": ""},
        {"ticker": "RIOT", "quantity": 52, "notes": ""},
        {"ticker": "UNH", "quantity": 19, "notes": ""},
        {"ticker": "PYPL", "quantity": 57, "notes": ""},
        {"ticker": "MSFT", "quantity": 3, "notes": ""},
    ],
    "etfs": [
        {"ticker": "IWM", "quantity": 26, "notes": ""},
        {"ticker": "VOO", "quantity": 7, "notes": ""},
        {"ticker": "VTI", "quantity": 18, "notes": ""},
        {"ticker": "URNM", "quantity": 18, "notes": ""},
    ],
    "options": [
        {"underlying": "AMZN", "type": "CALL", "strike": 190, "expiry": "2027-01-15", "contracts": 1, "notes": ""},
        {"underlying": "AMZN", "type": "CALL", "strike": 210, "expiry": "2027-01-15", "contracts": 2, "notes": ""},
    ],
}

HOLDINGS_FILE = Path(__file__).parent / "data" / "holdings.json"
CACHE_TTL = 300  # 5 minutes
