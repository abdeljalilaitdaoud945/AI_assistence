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

if __name__ == "__main__":
    mcp.run()