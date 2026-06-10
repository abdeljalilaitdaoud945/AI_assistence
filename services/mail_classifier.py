"""
Mail classifier — l'IA propose une catégorisation pour un mail.

Storage : mail_tags.json à la racine.
Catégories : type (commercial / finance / interne / marketing / admin / autre)
           + client (texte libre ou vide)
           + projet (texte libre ou vide)
"""

import json
import os
import threading
from typing import Optional

from pydantic import BaseModel, Field
from google import genai
from google.genai import types

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(BASE_DIR, "mail_tags.json")
_lock = threading.Lock()

CATEGORIES = ["commercial", "finance", "interne", "marketing",
              "administratif", "autre"]


class MailClassification(BaseModel):
    type: str = Field(description="Une des catégories : commercial, finance, "
                                  "interne, marketing, administratif, autre")
    client: str = Field(default="",
                        description="Nom du client/entreprise si identifiable, sinon vide")
    projet: str = Field(default="",
                        description="Nom du projet si mentionné, sinon vide")
    importance: str = Field(default="normale",
                            description="basse / normale / haute / critique")
    action_requise: bool = Field(default=False,
                                 description="Le mail demande-t-il une action ?")
    resume: str = Field(default="",
                        description="Résumé en 1 phrase courte")


_client: Optional[genai.Client] = None
def _g():
    global _client
    if _client is None:
        _client = genai.Client()
    return _client


def _load() -> dict:
    if not os.path.exists(STORE):
        return {}
    try:
        with open(STORE, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _save(d: dict):
    try:
        with open(STORE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[mail_classifier] save error: {e}")


def get_tags(mail_id: str) -> Optional[dict]:
    with _lock:
        return _load().get(mail_id)


def save_tags(mail_id: str, tags: dict):
    with _lock:
        d = _load()
        d[mail_id] = tags
        _save(d)


def classify_mail(mail_id: str, sender: str, subject: str,
                  body: str) -> dict:
    """Appelle Gemini pour classer un mail. Sauve et retourne le résultat."""
    cached = get_tags(mail_id)
    if cached:
        return cached

    text = (
        f"Sender: {sender}\nSubject: {subject}\n\n"
        f"Body:\n{(body or '')[:5000]}"
    )
    prompt = (
        "Tu classes des emails professionnels. Renvoie un JSON avec : "
        "type (commercial/finance/interne/marketing/administratif/autre), "
        "client (nom d'entreprise ou vide), projet (nom de projet ou vide), "
        "importance (basse/normale/haute/critique), "
        "action_requise (bool), resume (1 phrase courte).\n\n"
        f"Mail :\n{text}"
    )
    try:
        r = _g().models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=MailClassification,
                temperature=0.2,
            ),
        )
        parsed = getattr(r, "parsed", None)
        if parsed is not None:
            result = parsed.model_dump()
        else:
            result = json.loads(r.text)
        save_tags(mail_id, result)
        return result
    except Exception as e:
        return {
            "type": "autre", "client": "", "projet": "",
            "importance": "normale", "action_requise": False,
            "resume": f"(erreur IA : {e})",
        }


def all_tagged() -> dict:
    with _lock:
        return _load()


# =====================================================
#  Wrappers texte pour Gemini
# =====================================================

def list_clients_text() -> str:
    """Liste les clients identifiés à partir de la classification des emails."""
    tags = all_tagged()
    if not tags:
        return "Aucun mail n'a encore été classé."
    by_client = {}
    for mid, t in tags.items():
        c = (t.get("client") or "").strip()
        if not c:
            continue
        by_client.setdefault(c, []).append(t)
    if not by_client:
        return "Aucun client identifié dans les mails classés."
    lines = ["👥 Clients identifiés dans les mails :\n"]
    for c, items in sorted(by_client.items()):
        lines.append(f"• {c} ({len(items)} mail{'s' if len(items)>1 else ''})")
    return "\n".join(lines)


def get_priority_emails_text() -> str:
    """Renvoie les emails classés comme haute ou critique nécessitant action."""
    tags = all_tagged()
    if not tags:
        return "Aucun mail classé pour l'instant."
    urgents = [
        (mid, t) for mid, t in tags.items()
        if t.get("importance") in ("haute", "critique") or t.get("action_requise")
    ]
    if not urgents:
        return "Aucun mail urgent dans les mails classés."
    lines = [f"⚠️ Mails prioritaires ({len(urgents)}) :\n"]
    for _mid, t in urgents:
        lines.append(
            f"• [{t.get('importance','?')}] {t.get('client','?')} — "
            f"{t.get('resume','')}"
        )
    return "\n".join(lines)