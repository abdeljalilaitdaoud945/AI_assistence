from datetime import datetime, timezone
from googleapiclient.discovery import build
from services.google_auth import get_credentials

# Ajout pour la gouvernance
from services.logger_service import log_action

def get_today_events():
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)
    
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = now.replace(hour=23, minute=59, second=59, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    result = service.events().list(
        calendarId="primary",
        timeMin=start,
        timeMax=end,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    
    return result.get("items", [])

def get_month_events(year, month):
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)
    
    start = datetime(year, month, 1).isoformat() + "Z"
    if month == 12:
        end = datetime(year + 1, 1, 1).isoformat() + "Z"
    else:
        end = datetime(year, month + 1, 1).isoformat() + "Z"
    
    result = service.events().list(
        calendarId="primary",
        timeMin=start,
        timeMax=end,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    
    return result.get("items", [])

def get_events(date: str = None, max_results: int = 20):
    """Récupère les événements du calendrier.
    
    Si `date` est fourni : événements de cette date (format 'YYYY-MM-DD'),
    retourne une liste de strings formatés (pour affichage texte).
    
    Si `date` est None : prochains `max_results` événements à venir,
    retourne une liste de dicts {summary, start, end, location, hangoutLink}
    utilisable par le module home et la vue calendrier.
    """
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)
    
    if date is None:
        # Mode "upcoming" : prochains événements à venir, objets structurés
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        events = service.events().list(
            calendarId="primary", timeMin=now, maxResults=max_results,
            singleEvents=True, orderBy="startTime"
        ).execute()
        items = events.get("items", [])
        result = []
        for e in items:
            result.append({
                "id": e.get("id"),
                "summary": e.get("summary", "Sans titre"),
                "start": e["start"].get("dateTime", e["start"].get("date")),
                "end": e["end"].get("dateTime", e["end"].get("date")),
                "location": e.get("location", ""),
                "hangoutLink": e.get("hangoutLink", ""),
                "description": e.get("description", ""),
            })
        return result
    
    # Mode "date" : événements d'un jour précis, texte formaté
    start = f"{date}T00:00:00Z"
    end = f"{date}T23:59:59Z"
    events = service.events().list(
        calendarId="primary", timeMin=start, timeMax=end,
        singleEvents=True, orderBy="startTime"
    ).execute()
    items = events.get("items", [])
    if not items:
        return f"Aucun événement le {date}"
    
    result = []
    for e in items:
        raw_start = e["start"].get("dateTime", e["start"].get("date"))
        raw_end = e["end"].get("dateTime", e["end"].get("date"))
        summary = e.get("summary", "Sans titre")

        try:
            dt_start = datetime.fromisoformat(raw_start.replace("Z", "+00:00"))
            dt_end = datetime.fromisoformat(raw_end.replace("Z", "+00:00"))
            heure = f"{dt_start.strftime('%H:%M')} - {dt_end.strftime('%H:%M')}"
        except Exception:
            heure = raw_start

        line = f"📅 {summary}\n⏰ {heure}"

        location = e.get("location")
        if location:
            line += f"\n📍 {location}"

        description = e.get("description")
        if description:
            short = description[:100] + "..." if len(description) > 100 else description
            line += f"\n📝 {short}"

        attendees = e.get("attendees", [])
        if attendees:
            noms = [a.get("displayName", a.get("email", "")) for a in attendees]
            line += f"\n👥 {', '.join(noms)}"

        hangout = e.get("hangoutLink")
        if hangout:
            line += f"\n🔗 {hangout}"

        status = e.get("status")
        if status == "confirmed":
            line += "\n✅ Confirmé"
        elif status == "tentative":
            line += "\n⏳ En attente"
        elif status == "cancelled":
            line += "\n❌ Annulé"

        result.append(line)
    
    return "\n---\n".join(result)

def create_event(title: str, date: str, start_time: str, end_time: str):
    # ----- Garde-fou Mode Démo (silencieux si module absent) -----
    try:
        from services.demo_mode import is_demo_mode, log_demo_action
        if is_demo_mode():
            msg = log_demo_action("create_event", {
                "title": title, "date": date,
                "start_time": start_time, "end_time": end_time,
            })
            log_action("EVENT_DEMO", f"[DÉMO] événement simulé '{title}' le {date}")
            return msg
    except ImportError:
        pass  # demo_mode pas installé, on continue en mode normal
    # -------------------------------
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)
    event = {
        "summary": title,
        "start": {"dateTime": f"{date}T{start_time}:00", "timeZone": "Africa/Casablanca"},
        "end": {"dateTime": f"{date}T{end_time}:00", "timeZone": "Africa/Casablanca"},
    }
    service.events().insert(calendarId="primary", body=event).execute()
    
    # Enregistrement dans les logs de gouvernance
    log_action("EVENT_CREATED", f"Rendez-vous créé: '{title}' le {date} ({start_time}-{end_time})")
    
    return f"Événement '{title}' créé le {date} de {start_time} à {end_time}"

def delete_event(event_id: str):
    # ----- Garde-fou Mode Démo (silencieux si module absent) -----
    try:
        from services.demo_mode import is_demo_mode, log_demo_action
        if is_demo_mode():
            msg = log_demo_action("delete_event", {"event_id": event_id})
            log_action("EVENT_DELETE_DEMO", f"[DÉMO] suppression simulée {event_id}")
            return msg
    except ImportError:
        pass
    # -------------------------------
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)
    service.events().delete(calendarId="primary", eventId=event_id).execute()
    
    log_action("EVENT_DELETED", f"Événement supprimé (ID: {event_id})")
    
    return f"Événement {event_id} supprimé"

def list_upcoming_events(max_results: int = 10, as_text: bool = False):
    """Liste les prochains événements à venir.
    
    Par défaut retourne une liste de dicts (pour home/calendrier).
    Avec as_text=True, retourne une string formatée (pour l'agent Gemini).
    """
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    events = service.events().list(
        calendarId="primary", timeMin=now, maxResults=max_results,
        singleEvents=True, orderBy="startTime"
    ).execute()
    items = events.get("items", [])
    
    if as_text:
        if not items:
            return "Aucun événement à venir"
        return "\n".join([
            f"- {e['start'].get('dateTime', e['start'].get('date'))}: "
            f"{e.get('summary', 'Sans titre')}"
            for e in items
        ])
    
    # Mode structuré (par défaut)
    return [{
        "id": e.get("id"),
        "summary": e.get("summary", "Sans titre"),
        "start": e["start"].get("dateTime", e["start"].get("date")),
        "end": e["end"].get("dateTime", e["end"].get("date")),
        "location": e.get("location", ""),
        "hangoutLink": e.get("hangoutLink", ""),
    } for e in items]


# =====================================================================
# Wrappers texte pour l'agent Gemini (descriptions claires)
# =====================================================================

def get_events_text(date: str) -> str:
    """Retourne les événements du calendrier pour une date donnée.
    
    Args:
        date: Date au format 'YYYY-MM-DD' (ex: '2026-06-15').
    """
    res = get_events(date=date)
    if isinstance(res, list):
        return "\n\n".join(res) if res else f"Aucun événement le {date}"
    return res


def list_upcoming_events_text(max_results: int = 10) -> str:
    """Liste les prochains événements à venir, en texte lisible."""
    return list_upcoming_events(max_results=max_results, as_text=True)