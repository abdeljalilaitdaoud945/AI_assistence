"""
Service Bourse — yfinance, version enrichie.

Fusion :
  • dataclass StockQuote complet (52 sem high/low, market_cap, PE, dividend, beta…)
  • catalogue MARKETS (Casablanca / Wall Street / Paris / Tadawul / custom)
  • fetch_history avec OHLCV complet
  • fmt_number pour grands chiffres
  • cache TTL 30s
  • rétrocompat : get_stock_data / get_stock_history / get_market_indices /
    search_symbol et les wrappers Gemini sont conservés.

Pas de clé API requise.
"""

import math
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import yfinance as yf


# =====================================================================
#  CATALOGUE DES MARCHÉS — organisé pour l'app
# =====================================================================

MARKETS = {
    "ma": {
        "id": "ma",
        "name": "Casablanca",
        "flag": "🇲🇦",
        "category": "MA",
        "symbols": {
            "ATW.CS": "Attijariwafa Bank",
            "IAM.CS": "Maroc Telecom",
            "BCP.CS": "Banque Centrale Populaire",
            "BOA.CS": "Bank of Africa",
            "LHM.CS": "LafargeHolcim Maroc",
            "CSR.CS": "Cosumar",
            "MNG.CS": "Managem",
            "CIH.CS": "CIH Bank",
            "HPS.CS": "HPS",
            "WAA.CS": "Wafa Assurance",
            "TMA.CS": "Total Maroc",
            "ADH.CS": "Addoha",
            "ALM.CS": "Aluminium du Maroc",
            "SAH.CS": "Saham Assurance",
            "SNP.CS": "Sonasid",
        },
    },
    "us": {
        "id": "us",
        "name": "Wall Street",
        "flag": "🇺🇸",
        "category": "US",
        "symbols": {
            "AAPL":  "Apple",
            "MSFT":  "Microsoft",
            "GOOGL": "Alphabet",
            "AMZN":  "Amazon",
            "TSLA":  "Tesla",
            "META":  "Meta Platforms",
            "NVDA":  "NVIDIA",
            "BRK-B": "Berkshire Hathaway",
            "JPM":   "JPMorgan",
            "JNJ":   "Johnson & Johnson",
        },
    },
    "fr": {
        "id": "fr",
        "name": "Paris",
        "flag": "🇫🇷",
        "category": "EU",
        "symbols": {
            "MC.PA":  "LVMH",
            "TTE.PA": "TotalEnergies",
            "SAN.PA": "Sanofi",
            "AIR.PA": "Airbus",
            "BNP.PA": "BNP Paribas",
            "OR.PA":  "L'Oréal",
            "SU.PA":  "Schneider Electric",
            "DG.PA":  "Vinci",
            "ACA.PA": "Crédit Agricole",
            "GLE.PA": "Société Générale",
        },
    },
    "sa": {
        "id": "sa",
        "name": "Tadawul",
        "flag": "🇸🇦",
        "category": "SA",
        "symbols": {
            "2222.SR": "Saudi Aramco",
            "1180.SR": "Al Rajhi Bank",
            "2010.SR": "SABIC",
            "7010.SR": "STC",
            "2350.SR": "Saudi Kayan",
            "4030.SR": "Maaden",
            "2050.SR": "SAVOLA",
            "4200.SR": "Saudi Tadawul Group",
        },
    },
    "crypto": {
        "id": "crypto",
        "name": "Cryptos",
        "flag": "₿",
        "category": "Crypto",
        "symbols": {
            "BTC-USD": "Bitcoin",
            "ETH-USD": "Ethereum",
            "SOL-USD": "Solana",
            "BNB-USD": "BNB",
            "XRP-USD": "XRP",
            "ADA-USD": "Cardano",
        },
    },
}


# Indices par défaut pour la page d'accueil et résumé marché
DEFAULT_INDICES = [
    ("^GSPC",   "S&P 500",     "US"),
    ("^IXIC",   "Nasdaq",      "US"),
    ("^DJI",    "Dow Jones",   "US"),
    ("^FCHI",   "CAC 40",      "EU"),
    ("^GDAXI",  "DAX",         "EU"),
    ("^FTSE",   "FTSE 100",    "EU"),
    ("BTC-USD", "Bitcoin",     "Crypto"),
    ("ETH-USD", "Ethereum",    "Crypto"),
]


# =====================================================================
#  DATACLASS
# =====================================================================

@dataclass
class StockQuote:
    """Cotation enrichie d'une action / indice / crypto."""
    symbol:         str
    name:           str
    price:          float
    previous_close: float
    open_price:     float = 0.0
    day_high:       float = 0.0
    day_low:        float = 0.0
    week52_high:    float = 0.0
    week52_low:     float = 0.0
    volume:         int = 0
    avg_volume:     int = 0
    market_cap:     Optional[float] = None
    pe_ratio:       Optional[float] = None
    eps:            Optional[float] = None
    dividend_yield: Optional[float] = None
    beta:           Optional[float] = None
    sector:         str = "—"
    currency:       str = "USD"
    exchange:       str = "—"
    error:          Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now().strftime("%H:%M:%S")
    )

    @property
    def change(self) -> float:
        return round(self.price - self.previous_close, 4)

    @property
    def change_pct(self) -> float:
        if not self.previous_close:
            return 0.0
        return round((self.change / self.previous_close) * 100, 2)

    @property
    def is_up(self) -> bool:
        return self.change >= 0

    @property
    def week52_position_pct(self) -> float:
        rng = self.week52_high - self.week52_low
        if rng == 0:
            return 50.0
        return round((self.price - self.week52_low) / rng * 100, 1)

    def to_dict(self) -> dict:
        """Compat avec l'ancien dict get_stock_data."""
        return {
            "symbol":          self.symbol,
            "name":            self.name,
            "price":           self.price,
            "previous_close":  self.previous_close,
            "change":          self.change,
            "change_percent":  self.change_pct,
            "currency":        self.currency,
            "error":           self.error,
            # Bonus enrichi :
            "open_price":      self.open_price,
            "day_high":        self.day_high,
            "day_low":         self.day_low,
            "week52_high":     self.week52_high,
            "week52_low":      self.week52_low,
            "volume":          self.volume,
            "avg_volume":      self.avg_volume,
            "market_cap":      self.market_cap,
            "pe_ratio":        self.pe_ratio,
            "eps":             self.eps,
            "dividend_yield":  self.dividend_yield,
            "beta":            self.beta,
            "sector":          self.sector,
            "exchange":        self.exchange,
            "is_up":           self.is_up,
            "week52_position": self.week52_position_pct,
        }


# =====================================================================
#  HELPERS
# =====================================================================

def _safe_float(v, default=0.0) -> float:
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def _safe_int(v, default=0) -> int:
    try:
        return int(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def fmt_number(n, decimals: int = 2) -> str:
    """Formate un grand nombre : T / B / M / K."""
    if n is None:
        return "N/A"
    abs_n = abs(n)
    if abs_n >= 1e12:
        return f"{n / 1e12:.{decimals}f} T"
    if abs_n >= 1e9:
        return f"{n / 1e9:.{decimals}f} B"
    if abs_n >= 1e6:
        return f"{n / 1e6:.{decimals}f} M"
    if abs_n >= 1e3:
        return f"{n / 1e3:.{decimals}f} K"
    return f"{n:,.{decimals}f}"


# =====================================================================
#  CACHE TTL 30s
# =====================================================================

_CACHE: dict = {}
_TTL_SECONDS = 30


def _cache_get(key):
    e = _CACHE.get(key)
    if e is None:
        return None
    ts, val = e
    if time.time() - ts > _TTL_SECONDS:
        _CACHE.pop(key, None)
        return None
    return val


def _cache_set(key, value):
    _CACHE[key] = (time.time(), value)


# =====================================================================
#  FETCH PRINCIPAL — retourne un StockQuote
# =====================================================================

def fetch_quote(symbol: str) -> StockQuote:
    """Récupère un StockQuote complet. En cas d'échec, retourne un StockQuote
    avec error renseigné mais avec valeurs par défaut (jamais None)."""
    symbol = (symbol or "").upper().strip()
    cached = _cache_get(f"q:{symbol}")
    if cached is not None:
        return cached

    price = 0.0
    prev_close = 0.0
    currency = "USD"
    name = symbol
    error = None

    info = {}
    fi = None
    try:
        ticker = yf.Ticker(symbol)

        try:
            fi = ticker.fast_info
        except Exception:
            fi = None

        # 1. Tentative fast_info
        if fi is not None:
            try:
                price = _safe_float(getattr(fi, "last_price", None))
                prev_close = _safe_float(getattr(fi, "previous_close", None))
                currency = getattr(fi, "currency", None) or currency
            except Exception:
                pass

        # 2. Tentative info (riche mais lent) — n'avorte pas si fail
        try:
            info = ticker.info or {}
        except Exception:
            info = {}

        if not price:
            price = _safe_float(info.get("currentPrice"))
        if not prev_close:
            prev_close = _safe_float(info.get("previousClose"))
        if info.get("currency"):
            currency = info.get("currency")

        name = (info.get("shortName") or info.get("longName") or symbol)

        # 3. Fallback historique 5j si toujours pas de prix
        if not price:
            try:
                hist = ticker.history(period="5d")
                if hist is not None and not hist.empty:
                    closes = hist["Close"].dropna()
                    if len(closes):
                        price = float(closes.iloc[-1])
                    if len(closes) >= 2 and not prev_close:
                        prev_close = float(closes.iloc[-2])
            except Exception:
                pass

        if not price:
            error = "Aucune donnée disponible"

        # Récupération des champs étendus (depuis info)
        quote = StockQuote(
            symbol         = symbol,
            name           = name,
            price          = round(price, 4),
            previous_close = round(prev_close or price, 4),
            open_price     = round(_safe_float(info.get("open")
                                               or getattr(fi, "open", None)), 2),
            day_high       = round(_safe_float(info.get("dayHigh")
                                               or getattr(fi, "day_high", None)), 2),
            day_low        = round(_safe_float(info.get("dayLow")
                                               or getattr(fi, "day_low", None)), 2),
            week52_high    = round(_safe_float(info.get("fiftyTwoWeekHigh")
                                               or getattr(fi, "year_high", None)), 2),
            week52_low     = round(_safe_float(info.get("fiftyTwoWeekLow")
                                               or getattr(fi, "year_low", None)), 2),
            volume         = _safe_int(info.get("volume")
                                       or getattr(fi, "last_volume", None)),
            avg_volume     = _safe_int(info.get("averageVolume")
                                       or getattr(fi, "three_month_average_volume", None)),
            market_cap     = info.get("marketCap"),
            pe_ratio       = info.get("trailingPE"),
            eps            = info.get("trailingEps"),
            dividend_yield = info.get("dividendYield"),
            beta           = info.get("beta"),
            sector         = info.get("sector") or info.get("quoteType") or "—",
            currency       = currency or "USD",
            exchange       = info.get("exchange") or info.get("fullExchangeName") or "—",
            error          = error,
        )

    except Exception as e:
        quote = StockQuote(
            symbol=symbol, name=symbol, price=0.0, previous_close=0.0,
            error=str(e),
        )

    _cache_set(f"q:{symbol}", quote)
    return quote


# =====================================================================
#  RÉTROCOMPAT — fonctions historiques utilisées par le reste de l'app
# =====================================================================

def get_stock_data(symbol: str) -> dict:
    """Compat ancienne API : retourne un dict (utilisé par home.py, bourse.py)."""
    return fetch_quote(symbol).to_dict()


def get_stock_history(symbol: str, period: str = "1mo") -> list:
    """Compat ancienne API : retourne juste une liste de closes (pour sparkline)."""
    records = get_stock_ohlcv(symbol, period=period)
    return [r["close"] for r in records]


def get_stock_ohlcv(symbol: str, period: str = "1mo",
                    interval: Optional[str] = None) -> list:
    """
    Historique OHLCV complet pour graphique chandeliers ou plus riche.
    period   : 1d 5d 1mo 3mo 6mo 1y 2y 5y ytd max
    interval : auto-déduit du period si None
    """
    symbol = (symbol or "").upper().strip()
    if interval is None:
        if period == "1d":
            interval = "5m"
        elif period == "5d":
            interval = "1h"
        else:
            interval = "1d"

    key = f"h:{symbol}:{period}:{interval}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    try:
        hist = yf.Ticker(symbol).history(period=period, interval=interval)
        if hist is None or hist.empty:
            return []
        intraday = interval in ("1m", "5m", "15m", "30m", "1h", "60m", "90m")
        out = []
        for ts, row in hist.iterrows():
            try:
                o = float(row["Open"]); h = float(row["High"])
                l = float(row["Low"]);  c = float(row["Close"])
            except Exception:
                continue
            if any(math.isnan(v) for v in (o, h, l, c)):
                continue
            out.append({
                "date":  ts.strftime("%Y-%m-%d %H:%M") if intraday
                         else ts.strftime("%Y-%m-%d"),
                "open":  round(o, 4),
                "high":  round(h, 4),
                "low":   round(l, 4),
                "close": round(c, 4),
                "volume": int(row["Volume"]) if not math.isnan(float(row["Volume"])) else 0,
            })
        _cache_set(key, out)
        return out
    except Exception as e:
        print(f"[stock_service] ohlcv error {symbol}: {e}")
        return []


def get_market_indices() -> list:
    """Indices par défaut pour la home — format dict."""
    out = []
    for sym, display, cat in DEFAULT_INDICES:
        d = get_stock_data(sym)
        d["display_name"] = display
        d["category"] = cat
        out.append(d)
    return out


def get_markets_catalog() -> dict:
    """Renvoie tout le catalogue des marchés (id -> {name, flag, symbols})."""
    return MARKETS


def get_market_stocks(market_id: str) -> list:
    """Récupère les cotations de toutes les actions d'un marché donné."""
    market = MARKETS.get(market_id)
    if not market:
        return []
    out = []
    for sym, friendly in market["symbols"].items():
        d = get_stock_data(sym)
        # forcer le nom convivial si l'API ne retourne rien
        if d.get("name") == sym:
            d["name"] = friendly
        d["display_name"] = friendly
        d["market"] = market_id
        d["category"] = market["category"]
        out.append(d)
    return out


def search_symbol(query: str, max_results: int = 8) -> list:
    """Recherche de symbole via yfinance.Search."""
    if not query or not query.strip():
        return []
    try:
        from yfinance import Search
        res = Search(query, max_results=max_results).quotes or []
        out = []
        for q in res:
            out.append({
                "symbol":   q.get("symbol", ""),
                "name":     q.get("shortname") or q.get("longname") or q.get("symbol", ""),
                "exchange": q.get("exchDisp") or q.get("exchange", ""),
                "type":     q.get("quoteType", ""),
            })
        return out
    except Exception as e:
        print(f"[stock_service] search error: {e}")
        return []


# =====================================================================
#  WRAPPERS TEXTE pour Gemini
# =====================================================================

def get_stock_price_text(symbol: str) -> str:
    """Prix actuel d'une action / indice / crypto (avec contexte enrichi)."""
    q = fetch_quote(symbol)
    if q.error:
        return f"❌ Impossible de trouver les données pour '{symbol}'. {q.error}"

    arrow = "📈" if q.is_up else "📉"
    sign = "+" if q.is_up else ""
    extra = []
    if q.market_cap:
        extra.append(f"Cap. : {fmt_number(q.market_cap)} {q.currency}")
    if q.pe_ratio:
        extra.append(f"P/E : {q.pe_ratio:.2f}")
    if q.sector and q.sector != "—":
        extra.append(f"Secteur : {q.sector}")
    extra_str = " · ".join(extra) if extra else ""

    return (
        f"{arrow} {q.name} ({q.symbol})\n"
        f"Prix : {q.price} {q.currency}\n"
        f"Variation : {sign}{q.change} ({sign}{q.change_pct}%)\n"
        f"Clôture préc. : {q.previous_close} {q.currency}\n"
        f"Range jour : {q.day_low} – {q.day_high}\n"
        f"Range 52 sem. : {q.week52_low} – {q.week52_high}\n"
        + (f"{extra_str}\n" if extra_str else "")
        + f"Place : {q.exchange} · {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )


def get_market_summary_text() -> str:
    """Résumé des principaux indices mondiaux + cryptos."""
    data = get_market_indices()
    lines = ["📊 Aperçu des marchés :\n"]
    current_cat = None
    for d in data:
        if d["category"] != current_cat:
            current_cat = d["category"]
            lines.append(f"\n— {current_cat} —")
        if d.get("error") or not d.get("price"):
            lines.append(f"• {d['display_name']} : données indisponibles")
            continue
        sign = "+" if d.get("change_percent", 0) >= 0 else ""
        emoji = "🟢" if d.get("change_percent", 0) >= 0 else "🔴"
        lines.append(
            f"{emoji} {d['display_name']} : {d['price']} {d['currency']} "
            f"({sign}{d['change_percent']}%)"
        )
    return "\n".join(lines)


def get_market_stocks_text(market_id: str) -> str:
    """Cotations d'un marché entier (ex: 'ma' pour Casablanca)."""
    market = MARKETS.get(market_id)
    if not market:
        valid = ", ".join(MARKETS.keys())
        return f"Marché '{market_id}' inconnu. Valides : {valid}."
    stocks = get_market_stocks(market_id)
    lines = [f"{market['flag']} Bourse de {market['name']} :\n"]
    for d in stocks:
        if d.get("error") or not d.get("price"):
            lines.append(f"• {d['display_name']} : indisponible")
            continue
        sign = "+" if d.get("change_percent", 0) >= 0 else ""
        emoji = "🟢" if d.get("change_percent", 0) >= 0 else "🔴"
        lines.append(
            f"{emoji} {d['display_name']} ({d['symbol']}) : "
            f"{d['price']} {d['currency']} ({sign}{d['change_percent']}%)"
        )
    return "\n".join(lines)


def search_symbol_text(query: str) -> str:
    """Recherche d'un symbole par nom d'entreprise."""
    res = search_symbol(query)
    if not res:
        return f"Aucun résultat pour '{query}'."
    lines = [f"🔎 Résultats pour '{query}' :"]
    for r in res:
        lines.append(f"• {r['symbol']} — {r['name']} ({r['exchange']}, {r['type']})")
    return "\n".join(lines)


from typing import List


def compare_stocks_text(symbols: List[str]) -> str:
    """Compare plusieurs valeurs boursières côte à côte. 
    
    Args:
        symbols: Liste de tickers boursiers (ex: ["AAPL", "MSFT", "GOOGL"]).
    """
    if not symbols:
        return "Aucun symbole à comparer."
    lines = ["📊 Comparaison :\n"]
    for s in symbols:
        q = fetch_quote(s)
        if q.error or not q.price:
            lines.append(f"• {s} : données indisponibles")
            continue
        sign = "+" if q.is_up else ""
        emoji = "🟢" if q.is_up else "🔴"
        lines.append(
            f"{emoji} {q.name} ({q.symbol}) : "
            f"{q.price} {q.currency} ({sign}{q.change_pct}%)"
        )
    return "\n".join(lines)