"""
Service d'analyse de PDFs (comptes-rendus de réunion).

Pipeline :
    PDF (path ou bytes) -> texte (via pypdf) -> Gemini (structured output)
                                                       -> JSON : résumé + RDVs + tâches

IMPORTANT : on utilise un client Gemini DÉDIÉ pour l'analyse, sans tools,
parce que l'API ne supporte pas response_mime_type=application/json avec tools.
"""

import io
import os
import json
from typing import Optional

from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# pypdf est importé à la volée pour donner un message clair si absent
try:
    from pypdf import PdfReader
    _PYPDF_AVAILABLE = True
    _PYPDF_ERROR = None
except Exception as _e:
    _PYPDF_AVAILABLE = False
    _PYPDF_ERROR = str(_e)


# =====================================================================
# Schéma de la réponse Gemini (structured output)
# =====================================================================

class DetectedEvent(BaseModel):
    """Un RDV / événement détecté dans le compte-rendu."""
    titre: str = Field(description="Titre clair et concis de l'événement")
    date: str = Field(description="Date au format YYYY-MM-DD si connue, sinon chaîne vide")
    heure_debut: str = Field(description="HH:MM ou chaîne vide si non précisé", default="")
    heure_fin: str = Field(description="HH:MM ou chaîne vide si non précisé", default="")
    lieu: str = Field(description="Lieu de l'événement ou chaîne vide", default="")
    description: str = Field(description="Détails brefs sur l'événement", default="")


class DetectedTask(BaseModel):
    """Une tâche à faire détectée dans le compte-rendu."""
    titre: str = Field(description="Action à effectuer, formulée à l'infinitif")
    deadline: str = Field(description="Date limite YYYY-MM-DD ou chaîne vide", default="")
    description: str = Field(description="Contexte / responsable / précisions", default="")


class MeetingAnalysis(BaseModel):
    """Analyse complète d'un compte-rendu de réunion."""
    resume: str = Field(description="Résumé synthétique en 2-3 phrases du contenu du PDF")
    participants: list[str] = Field(default_factory=list,
                                    description="Noms ou rôles des participants identifiés")
    decisions: list[str] = Field(default_factory=list,
                                 description="Décisions importantes prises lors de la réunion")
    evenements: list[DetectedEvent] = Field(default_factory=list,
                                            description="Prochains RDV / événements mentionnés")
    taches: list[DetectedTask] = Field(default_factory=list,
                                       description="Tâches à effectuer (action items) mentionnées")


# =====================================================================
# Extraction de texte
# =====================================================================

def extract_text_from_pdf_path(path: str) -> str:
    """Extrait le texte d'un PDF local."""
    if not _PYPDF_AVAILABLE:
        raise RuntimeError(
            f"La bibliothèque pypdf n'est pas installée. Lance : pip install pypdf. "
            f"Détail : {_PYPDF_ERROR}"
        )
    if not os.path.exists(path):
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    reader = PdfReader(path)
    pages = []
    for i, p in enumerate(reader.pages):
        try:
            pages.append(p.extract_text() or "")
        except Exception as e:
            pages.append(f"[Erreur page {i+1}: {e}]")
    return "\n\n".join(pages).strip()


def extract_text_from_pdf_bytes(data: bytes) -> str:
    """Extrait le texte d'un PDF en mémoire (bytes)."""
    if not _PYPDF_AVAILABLE:
        raise RuntimeError(
            f"La bibliothèque pypdf n'est pas installée. Lance : pip install pypdf. "
            f"Détail : {_PYPDF_ERROR}"
        )
    reader = PdfReader(io.BytesIO(data))
    pages = []
    for i, p in enumerate(reader.pages):
        try:
            pages.append(p.extract_text() or "")
        except Exception as e:
            pages.append(f"[Erreur page {i+1}: {e}]")
    return "\n\n".join(pages).strip()


# =====================================================================
# Analyse Gemini (client séparé)
# =====================================================================

_analyzer_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    global _analyzer_client
    if _analyzer_client is None:
        _analyzer_client = genai.Client()
    return _analyzer_client


def analyze_meeting_text(text: str) -> dict:
    """
    Envoie le texte d'un compte-rendu à Gemini et récupère une analyse structurée.
    Retour : dict avec les clés resume, participants, decisions, evenements, taches.
    Si erreur, retourne un dict avec error.
    """
    if not text or not text.strip():
        return {
            "error": "Texte vide : aucun contenu lisible dans le PDF.",
            "resume": "",
            "participants": [],
            "decisions": [],
            "evenements": [],
            "taches": [],
        }

    # Truncate aggressively pour éviter des coûts/latence trop hauts
    MAX_CHARS = 30000
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n\n[…texte tronqué…]"

    prompt = (
        "Tu reçois le texte brut d'un compte-rendu de réunion en français. "
        "Analyse-le et retourne un objet JSON structuré contenant : "
        "1) un résumé court (2-3 phrases) ; "
        "2) la liste des participants ; "
        "3) la liste des décisions prises ; "
        "4) la liste des PROCHAINS RDV / événements explicitement mentionnés "
        "(avec date au format YYYY-MM-DD si possible, heures HH:MM si précisées, lieu) ; "
        "5) la liste des TÂCHES À FAIRE (action items) avec deadline si mentionnée. "
        "Ne fabrique RIEN : si une info n'est pas dans le texte, mets une chaîne vide. "
        "Sois concis et factuel.\n\n"
        "--- TEXTE DU COMPTE-RENDU ---\n"
        f"{text}"
    )

    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=MeetingAnalysis,
                temperature=0.2,
            ),
        )
        # response.parsed est un MeetingAnalysis pydantic si tout va bien
        parsed = getattr(response, "parsed", None)
        if parsed is not None:
            return parsed.model_dump()
        # Fallback : parser le text JSON brut
        return json.loads(response.text)
    except Exception as e:
        return {
            "error": str(e),
            "resume": "",
            "participants": [],
            "decisions": [],
            "evenements": [],
            "taches": [],
        }


def analyze_pdf_path(path: str) -> dict:
    """Convenience : lit le PDF + analyse. Renvoie le dict d'analyse."""
    try:
        text = extract_text_from_pdf_path(path)
    except Exception as e:
        return {
            "error": str(e),
            "resume": "", "participants": [], "decisions": [],
            "evenements": [], "taches": [],
        }
    res = analyze_meeting_text(text)
    res["_raw_text_preview"] = text[:500]
    return res


def analyze_pdf_bytes(data: bytes) -> dict:
    """Idem pour des bytes."""
    try:
        text = extract_text_from_pdf_bytes(data)
    except Exception as e:
        return {
            "error": str(e),
            "resume": "", "participants": [], "decisions": [],
            "evenements": [], "taches": [],
        }
    res = analyze_meeting_text(text)
    res["_raw_text_preview"] = text[:500]
    return res