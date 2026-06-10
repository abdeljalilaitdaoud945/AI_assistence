from mcp.server.fastmcp import FastMCP

# Imports des services Agenda
from services.calendar_service import (
    get_events,
    create_event,
    delete_event,
    list_upcoming_events,
)

# Imports des services Email
from services.email_service import (
    get_unread_emails_text, 
    send_email
)

# Imports des services Bourse
from services.stock_service import (
    get_stock_price_text,
    get_market_summary_text,
    search_symbol_text,
    compare_stocks_text,
)

# Import service PDF
from services.pdf_history import get_pdf_history_text

mcp = FastMCP(name="InptApp2")

# ==========================================
# 📅 OUTILS AGENDA
# ==========================================

@mcp.tool()
def mcp_get_events(date: str) -> str:
    """Récupère les événements de l'agenda pour une date précise (Format attendu: YYYY-MM-DD)."""
    return get_events(date)

@mcp.tool()
def mcp_create_event(title: str, date: str, start_time: str, end_time: str) -> str:
    """Crée un rendez-vous. Format: date en YYYY-MM-DD, start_time et end_time en HH:MM."""
    return create_event(title, date, start_time, end_time)

@mcp.tool()
def mcp_delete_event(event_id: str) -> str:
    """Supprime un événement de l'agenda à partir de son ID unique."""
    return delete_event(event_id)

@mcp.tool()
def mcp_list_upcoming(max_results: int = 10) -> str:
    """Liste les prochains événements à venir dans l'agenda."""
    return list_upcoming_events(max_results)

# ==========================================
# 📧 OUTILS EMAILS
# ==========================================

@mcp.tool()
def mcp_get_unread_emails(limit: int = 5) -> str:
    """Récupère les derniers emails non lus du directeur en texte brut. Utile pour faire un résumé de la boîte de réception."""
    return get_unread_emails_text(limit)

@mcp.tool()
def mcp_send_email(destinataire: str, sujet: str, contenu: str) -> str:
    """Envoie un email à un contact. Paramètres attendus : destinataire (adresse email valide), sujet de l'email, et contenu du message."""
    return send_email(destinataire, sujet, contenu)

# ==========================================
# 📈 OUTILS BOURSE
# ==========================================

@mcp.tool()
def mcp_get_stock_price(symbol: str) -> str:
    """Renvoie le prix actuel et la variation du jour pour un symbole boursier (ex: 'AAPL', 'BTC-USD', '^FCHI')."""
    return get_stock_price_text(symbol)

@mcp.tool()
def mcp_get_market_summary() -> str:
    """Renvoie un résumé des principaux marchés mondiaux (S&P500, Nasdaq, Dow, CAC40, DAX, FTSE, BTC, ETH, SOL)."""
    return get_market_summary_text()

@mcp.tool()
def mcp_search_symbol(query: str) -> str:
    """Recherche le symbole boursier d'une entreprise par son nom (ex: 'Apple' -> AAPL)."""
    return search_symbol_text(query)

@mcp.tool()
def mcp_compare_stocks(symbols: list) -> str:
    """Compare plusieurs valeurs boursières côte à côte. Paramètre : liste de symboles."""
    return compare_stocks_text(symbols)

# ==========================================
# 📄 OUTILS COMPTES-RENDUS PDF
# ==========================================

@mcp.tool()
def mcp_get_pdf_history(limit: int = 10) -> str:
    """Renvoie la liste des derniers comptes-rendus de réunion analysés (résumé, nb RDV / tâches)."""
    return get_pdf_history_text(limit)

if __name__ == "__main__":
    mcp.run()