"""
Historique des analyses PDF — persistance simple en JSON local.

Stocké à côté du projet dans pdf_history.json (gitignored idéalement).
Chaque entrée :
    {
      "id": "uuid",
      "source": "local" | "drive",
      "filename": "...",
      "drive_id": "..." (si Drive),
      "analyzed_at": "ISO8601",
      "analysis": { resume, participants, decisions, evenements, taches }
    }
"""

import json
import os
import threading
import uuid
from datetime import datetime
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_PATH = os.path.join(BASE_DIR, "pdf_history.json")

_lock = threading.Lock()


def _load_raw() -> list[dict]:
    if not os.path.exists(HISTORY_PATH):
        return []
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[pdf_history] load error: {e}")
        return []


def _save_raw(items: list[dict]) -> None:
    try:
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[pdf_history] save error: {e}")


def list_history() -> list[dict]:
    """Retourne la liste de l'historique, le plus récent en premier."""
    with _lock:
        items = _load_raw()
    items.sort(key=lambda x: x.get("analyzed_at", ""), reverse=True)
    return items


def add_entry(
    filename: str,
    source: str,
    analysis: dict,
    drive_id: Optional[str] = None,
) -> dict:
    """Ajoute une entrée et retourne l'entrée créée (avec id et analyzed_at)."""
    entry = {
        "id": uuid.uuid4().hex,
        "source": source,
        "filename": filename,
        "drive_id": drive_id,
        "analyzed_at": datetime.now().isoformat(timespec="seconds"),
        "analysis": analysis,
    }
    with _lock:
        items = _load_raw()
        items.append(entry)
        _save_raw(items)
    return entry


def delete_entry(entry_id: str) -> bool:
    with _lock:
        items = _load_raw()
        new_items = [x for x in items if x.get("id") != entry_id]
        if len(new_items) == len(items):
            return False
        _save_raw(new_items)
        return True


def get_entry(entry_id: str) -> Optional[dict]:
    with _lock:
        items = _load_raw()
    for x in items:
        if x.get("id") == entry_id:
            return x
    return None


# =========================================================
# Wrapper texte pour Gemini (l'agent peut consulter l'historique)
# =========================================================

def get_pdf_history_text(limit: int = 10) -> str:
    """
    Retourne un résumé textuel des derniers comptes-rendus analysés.
    Utile pour que l'assistant IA puisse y faire référence.
    """
    items = list_history()[:limit]
    if not items:
        return "Aucun compte-rendu n'a encore été analysé."
    lines = ["📄 Derniers comptes-rendus analysés :\n"]
    for it in items:
        date = it.get("analyzed_at", "")[:10]
        an = it.get("analysis", {})
        resume = (an.get("resume") or "")[:200]
        ev_count = len(an.get("evenements", []))
        ta_count = len(an.get("taches", []))
        lines.append(
            f"• [{date}] {it.get('filename', 'PDF')} "
            f"({it.get('source', '?')}) — "
            f"{ev_count} RDV / {ta_count} tâches\n  {resume}"
        )
    return "\n".join(lines)