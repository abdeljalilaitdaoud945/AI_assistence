"""
Service Bourse — données en temps (quasi) réel via yfinance.
Gratuit, pas de clé API requise.

Symboles utiles :
    US      : ^GSPC (S&P500), ^IXIC (Nasdaq), ^DJI (Dow Jones)
    EU      : ^FCHI (CAC40), ^GDAXI (DAX), ^FTSE (FTSE100)
    Crypto  : BTC-USD, ETH-USD, SOL-USD
    Actions : AAPL, MSFT, TSLA, GOOGL, NVDA, LVMH.PA, MC.PA...

Les fonctions `*_text` retournent du texte brut destiné à Gemini.
Les fonctions `*_data` retournent des dicts/lists pour l'UI Flet.
"""

import time
from datetime import datetime

import yfinance as yf

# ---- Cache simple pour éviter de spammer Yahoo (TTL 30s) -----------------
_CACHE: dict = {}
_TTL_SECONDS = 30


def _cache_get(key: str):
    entry = _CACHE.get(key)
    if entry is None:
        return None
    ts, value = entry
    if time.time() - ts > _TTL_SECONDS:
        _CACHE.pop(key, None)
        return None
    return value


def _cache_set(key: str, value):
    _CACHE[key] = (time.time(), value)


# ---- Catalogue des marchés par défaut ------------------------------------
DEFAULT_INDICES = [
    # (symbole yahoo, nom affiché, catégorie)
    ("^GSPC",   "S&P 500",     "US"),
    ("^IXIC",   "Nasdaq",      "US"),
    ("^DJI",    "Dow Jones",   "US"),
    ("^FCHI",   "CAC 40",      "EU"),
    ("^GDAXI",  "DAX",         "EU"),
    ("^FTSE",   "FTSE 100",    "EU"),
    ("BTC-USD", "Bitcoin",     "Crypto"),
    ("ETH-USD", "Ethereum",    "Crypto"),
    ("SOL-USD", "Solana",      "Crypto"),
]


# =========================================================================
# Fonctions bas niveau (data brute)
# =========================================================================

def _safe_attr(obj, name, default=None):
    """Accès défensif à un attribut ou clé sur fast_info qui change selon les versions."""
    try:
        if hasattr(obj, name):
            v = getattr(obj, name)
            return v if v is not None else default
    except Exception:
        pass
    try:
        if hasattr(obj, "get"):
            v = obj.get(name)
            return v if v is not None else default
    except Exception:
        pass
    return default


def get_stock_data(symbol: str) -> dict:
    """
    Récupère le prix actuel et les infos d'un symbole.
    Retourne un dict avec :
        symbol, name, price, previous_close, change, change_percent,
        currency, error (si problème)
    """
    symbol = symbol.upper().strip()
    cached = _cache_get(f"data:{symbol}")
    if cached is not None:
        return cached

    price = None
    prev_close = None
    currency = "USD"
    name = symbol

    # ---- Tentative 1 : fast_info (rapide) ----
    try:
        ticker = yf.Ticker(symbol)
        try:
            fi = ticker.fast_info
            price = _safe_attr(fi, "last_price")
            prev_close = _safe_attr(fi, "previous_close")
            currency = _safe_attr(fi, "currency", "USD") or "USD"
        except Exception as e_fi:
            print(f"[stock_service] fast_info fail {symbol}: {e_fi}")

        # ---- Tentative 2 : fallback historique 2 jours ----
        if price is None or prev_close is None:
            try:
                hist = ticker.history(period="5d")
                if hist is not None and not hist.empty:
                    closes = hist["Close"].dropna()
                    if len(closes) >= 1:
                        price = float(closes.iloc[-1]) if price is None else price
                    if len(closes) >= 2:
                        prev_close = float(closes.iloc[-2]) if prev_close is None else prev_close
                    elif price is not None and prev_close is None:
                        prev_close = price
            except Exception as e_h:
                print(f"[stock_service] history fail {symbol}: {e_h}")

        if price is None:
            raise ValueError(f"Aucune donnée disponible pour {symbol}")

        price = float(price)
        prev_close = float(prev_close) if prev_close is not None else price
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0.0

        # Nom : tentative légère, sans bloquer si ça échoue
        try:
            info = ticker.info or {}
            name = info.get("shortName") or info.get("longName") or symbol
        except Exception:
            name = symbol

        result = {
            "symbol": symbol,
            "name": name,
            "price": round(price, 4),
            "previous_close": round(prev_close, 4),
            "change": round(change, 4),
            "change_percent": round(change_pct, 2),
            "currency": currency,
            "error": None,
        }
        _cache_set(f"data:{symbol}", result)
        return result

    except Exception as e:
        return {
            "symbol": symbol,
            "name": symbol,
            "price": None,
            "previous_close": None,
            "change": None,
            "change_percent": None,
            "currency": "",
            "error": str(e),
        }


def get_stock_history(symbol: str, period: str = "1mo") -> list:
    """
    Historique de cours pour le mini-graphe.
    period : '1d', '5d', '1mo', '3mo', '6mo', '1y', '5y', 'max'
    Retourne une liste de floats (closes).
    """
    symbol = symbol.upper().strip()
    key = f"hist:{symbol}:{period}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    try:
        ticker = yf.Ticker(symbol)
        # Intervalle adapté pour ne pas surcharger
        interval = "5m" if period == "1d" else "1h" if period == "5d" else "1d"
        hist = ticker.history(period=period, interval=interval)
        if hist.empty:
            return []
        closes = [float(x) for x in hist["Close"].dropna().tolist()]
        _cache_set(key, closes)
        return closes
    except Exception as e:
        print(f"[stock_service] history error {symbol}: {e}")
        return []


def get_market_indices() -> list:
    """
    Renvoie la liste des indices/cryptos par défaut avec leurs données.
    """
    out = []
    for sym, name, cat in DEFAULT_INDICES:
        d = get_stock_data(sym)
        d["display_name"] = name
        d["category"] = cat
        out.append(d)
    return out


def search_symbol(query: str, max_results: int = 8) -> list:
    """
    Recherche un symbole/entreprise. Utilise l'endpoint search interne de yfinance.
    Retourne une liste de dicts : {symbol, name, exchange, type}
    """
    if not query or not query.strip():
        return []
    try:
        # yfinance.Search existe à partir d'une version récente
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


# =========================================================================
# Wrappers TEXTE pour Gemini (le LLM consomme du texte, pas des dicts)
# =========================================================================

def get_stock_price_text(symbol: str) -> str:
    """
    Renvoie le prix actuel d'une action ou indice boursier.
    Paramètre : symbol (ex: 'AAPL' pour Apple, 'BTC-USD' pour Bitcoin,
    '^FCHI' pour le CAC40, 'MC.PA' pour LVMH sur Euronext Paris).
    Utile quand l'utilisateur demande le cours d'une action, d'un indice,
    d'une crypto ou veut comparer plusieurs valeurs.
    """
    d = get_stock_data(symbol)
    if d.get("error"):
        return f"❌ Impossible de trouver les données pour '{symbol}'. Erreur : {d['error']}"

    arrow = "📈" if (d["change"] or 0) >= 0 else "📉"
    sign = "+" if (d["change"] or 0) >= 0 else ""
    return (
        f"{arrow} {d['name']} ({d['symbol']})\n"
        f"Prix actuel : {d['price']} {d['currency']}\n"
        f"Clôture précédente : {d['previous_close']} {d['currency']}\n"
        f"Variation : {sign}{d['change']} {d['currency']} "
        f"({sign}{d['change_percent']}%)\n"
        f"Données : {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )


def get_market_summary_text() -> str:
    """
    Renvoie un résumé des principaux indices boursiers mondiaux
    (S&P500, Nasdaq, Dow Jones, CAC40, DAX, FTSE) et des cryptos
    principales (Bitcoin, Ethereum, Solana). Utile pour un point de
    marché global.
    """
    data = get_market_indices()
    lines = ["📊 Aperçu des marchés :\n"]
    current_cat = None
    for d in data:
        if d["category"] != current_cat:
            current_cat = d["category"]
            lines.append(f"\n— {current_cat} —")
        if d.get("error") or d["price"] is None:
            lines.append(f"• {d['display_name']} : données indisponibles")
            continue
        sign = "+" if d["change_percent"] >= 0 else ""
        emoji = "🟢" if d["change_percent"] >= 0 else "🔴"
        lines.append(
            f"{emoji} {d['display_name']} : {d['price']} {d['currency']} "
            f"({sign}{d['change_percent']}%)"
        )
    return "\n".join(lines)


def search_symbol_text(query: str) -> str:
    """
    Recherche le symbole boursier d'une entreprise par son nom
    (ex: 'Apple' -> AAPL, 'LVMH' -> MC.PA). À utiliser quand l'utilisateur
    cite un nom d'entreprise sans connaître le symbole exact.
    """
    res = search_symbol(query)
    if not res:
        return f"Aucun résultat pour '{query}'."
    lines = [f"🔎 Résultats pour '{query}' :"]
    for r in res:
        lines.append(f"• {r['symbol']} — {r['name']} ({r['exchange']}, {r['type']})")
    return "\n".join(lines)


def compare_stocks_text(symbols: list) -> str:
    """
    Compare plusieurs valeurs boursières côte à côte.
    Paramètre : symbols, liste de symboles (ex: ['AAPL', 'MSFT', 'GOOGL']).
    """
    if not symbols:
        return "Aucun symbole à comparer."
    lines = ["📊 Comparaison :\n"]
    for s in symbols:
        d = get_stock_data(s)
        if d.get("error") or d["price"] is None:
            lines.append(f"• {s} : données indisponibles")
            continue
        sign = "+" if d["change_percent"] >= 0 else ""
        emoji = "🟢" if d["change_percent"] >= 0 else "🔴"
        lines.append(
            f"{emoji} {d['name']} ({d['symbol']}) : "
            f"{d['price']} {d['currency']} ({sign}{d['change_percent']}%)"
        )
    return "\n".join(lines)