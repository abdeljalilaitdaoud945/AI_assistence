"""
Business tracker — suivi des dossiers commerciaux et génération d'offres IA.

Stages : demande → offre → relance → négociation → décision (gagne/perd)
Stockage : business_deals.json à la racine du projet.
"""

import json
import os
import threading
import uuid
from datetime import datetime, timedelta
from typing import Optional
from google import genai

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(BASE_DIR, "business_deals.json")
_lock = threading.Lock()

STAGES = [
    ("demande",     "Demande reçue",       "#60A5FA"),
    ("offre",       "Offre envoyée",       "#A78BFA"),
    ("relance",     "Relance en cours",    "#FBBF24"),
    ("negociation", "En négociation",      "#F59E0B"),
    ("gagne",       "Gagné",               "#34D399"),
    ("perdu",       "Perdu",               "#F87171"),
]
STAGE_IDS = [s[0] for s in STAGES]
STAGE_LABELS = {s[0]: s[1] for s in STAGES}
STAGE_COLORS = {s[0]: s[2] for s in STAGES}


def _load() -> list:
    if not os.path.exists(STORE):
        return []
    try:
        with open(STORE, "r", encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, list) else []
    except Exception:
        return []

def _save(items: list):
    try:
        with open(STORE, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[business] save error: {e}")

def list_deals() -> list:
    with _lock:
        items = _load()
    items.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return items

def add_deal(client: str, intitule: str, montant: Optional[float] = None,
             stage: str = "demande", contact_email: str = "",
             notes: str = "") -> dict:
    now = datetime.now().isoformat(timespec="seconds")
    entry = {
        "id": uuid.uuid4().hex,
        "client": client.strip(),
        "intitule": intitule.strip(),
        "montant": montant,
        "stage": stage if stage in STAGE_IDS else "demande",
        "contact_email": contact_email.strip(),
        "notes": notes.strip(),
        "created_at": now,
        "updated_at": now,
        "last_action_at": now,
    }
    with _lock:
        items = _load()
        items.append(entry)
        _save(items)
    return entry

def update_deal(deal_id: str, **fields) -> bool:
    with _lock:
        items = _load()
        found = False
        for it in items:
            if it.get("id") == deal_id:
                for k, v in fields.items():
                    if k in ("client", "intitule", "stage", "contact_email",
                             "notes", "montant"):
                        it[k] = v
                it["updated_at"] = datetime.now().isoformat(timespec="seconds")
                if "stage" in fields:
                    it["last_action_at"] = it["updated_at"]
                found = True
                break
        if found:
            _save(items)
        return found

def delete_deal(deal_id: str) -> bool:
    with _lock:
        items = _load()
        new = [x for x in items if x.get("id") != deal_id]
        if len(new) == len(items):
            return False
        _save(new)
        return True

def deals_needing_followup(days: int = 7) -> list:
    cutoff = datetime.now() - timedelta(days=days)
    out = []
    for d in list_deals():
        if d.get("stage") in ("gagne", "perdu"):
            continue
        try:
            la = datetime.fromisoformat(d.get("last_action_at", ""))
            if la < cutoff:
                out.append(d)
        except Exception:
            out.append(d)
    return out

def list_deals_text() -> str:
    items = list_deals()
    if not items:
        return "Aucun dossier commercial enregistré."
    lines = ["📂 Dossiers commerciaux :\n"]
    for d in items:
        m = f"{d['montant']:,.0f}" if d.get("montant") else "—"
        lines.append(
            f"• [{STAGE_LABELS.get(d['stage'], d['stage'])}] "
            f"{d['client']} — {d['intitule']} ({m})"
        )
    return "\n".join(lines)

def get_deals_followup_text(days: int = 7) -> str:
    items = deals_needing_followup(days=days)
    if not items:
        return f"✅ Aucun dossier en attente de relance (> {days} jours)."
    lines = [f"⏰ Dossiers à relancer ({len(items)}) :\n"]
    for d in items:
        last = d.get("last_action_at", "")[:10]
        lines.append(
            f"• {d['client']} — {d['intitule']} "
            f"[{STAGE_LABELS.get(d['stage'], d['stage'])}] "
            f"dernière action : {last}"
            + (f" · contact : {d['contact_email']}"
               if d.get("contact_email") else "")
        )
    return "\n".join(lines)

def generate_commercial_offer(client: str, intitule: str, montant: str, notes: str) -> str:
    """Génère un brouillon de proposition commerciale via Gemini."""
    try:
        ia_client = genai.Client()
        prompt = (
            f"Rédige un email très professionnel et persuasif contenant une offre commerciale/financière.\n"
            f"Client destinataire : {client}\n"
            f"Objet du projet : {intitule}\n"
            f"Montant estimé : {montant if montant else 'À déterminer'}\n"
            f"Notes/Contexte supplémentaires : {notes}\n\n"
            "Mets en avant notre expertise, structure bien l'offre et finis par un appel à l'action. "
            "Ne rédige que le corps du mail."
        )
        response = ia_client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return response.text
    except Exception as e:
        return f"Erreur IA : {e}"