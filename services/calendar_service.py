from datetime import datetime
from googleapiclient.discovery import build
from services.google_auth import get_credentials

def get_today_events():
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)
    
    now = datetime.utcnow()
    start = now.replace(hour=0, minute=0, second=0).isoformat() + "Z"
    end = (now.replace(hour=23, minute=59, second=59)).isoformat() + "Z"
    
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

def get_events(date: str):
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)
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
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)
    event = {
        "summary": title,
        "start": {"dateTime": f"{date}T{start_time}:00", "timeZone": "Africa/Casablanca"},
        "end": {"dateTime": f"{date}T{end_time}:00", "timeZone": "Africa/Casablanca"},
    }
    service.events().insert(calendarId="primary", body=event).execute()
    return f"Événement '{title}' créé le {date} de {start_time} à {end_time}"

def delete_event(event_id: str):
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)
    service.events().delete(calendarId="primary", eventId=event_id).execute()
    return f"Événement {event_id} supprimé"

def list_upcoming_events(max_results: int = 10):
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)
    now = datetime.utcnow().isoformat() + "Z"
    events = service.events().list(
        calendarId="primary", timeMin=now, maxResults=max_results,
        singleEvents=True, orderBy="startTime"
    ).execute()
    items = events.get("items", [])
    if not items:
        return "Aucun événement à venir"
    return "\n".join([f"- {e['start'].get('dateTime', e['start'].get('date'))}: {e.get('summary', 'Sans titre')}" for e in items])