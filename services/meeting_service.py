"""
Meeting service — PV pro, agenda, challenge des décisions.

- generate_pv_html(analysis, ...) : génère un PV HTML formel
- send_pv_to_participants(html, emails, subject) : envoie par mail
- propose_agenda(type_reunion, contexte) : Gemini propose un ordre du jour
- challenge_meeting(analysis) : Gemini challenge décisions (questions, risques)
- Wrappers texte pour Gemini agent.
"""

from datetime import datetime
from typing import Optional

from google import genai
from google.genai import types

from services.email_service import send_html_email


_client: Optional[genai.Client] = None
def _g():
    global _client
    if _client is None:
        _client = genai.Client()
    return _client


# =====================================================
#  PV HTML pro
# =====================================================

def generate_pv_html(analysis: dict, type_reunion: str = "Réunion",
                     animateur: str = "—",
                     date_reunion: str = "") -> str:
    """Construit un PV HTML structuré à partir d'une analyse Gemini d'un CR."""
    resume = analysis.get("resume", "") or "—"
    participants = analysis.get("participants", []) or []
    decisions = analysis.get("decisions", []) or []
    evenements = analysis.get("evenements", []) or []
    taches = analysis.get("taches", []) or []
    today = date_reunion or datetime.now().strftime("%d/%m/%Y")

    def li(items):
        if not items:
            return "<li><em>Aucun élément.</em></li>"
        return "".join(f"<li>{x}</li>" for x in items)

    actions_rows = ""
    for t in taches:
        actions_rows += (
            f"<tr>"
            f"<td>{t.get('titre','')}</td>"
            f"<td>{t.get('description','') or '—'}</td>"
            f"<td>{t.get('deadline','') or 'À définir'}</td>"
            f"<td>Court terme</td>"
            f"</tr>"
        )
    for e in evenements:
        actions_rows += (
            f"<tr>"
            f"<td>Préparer / participer à : {e.get('titre','')}</td>"
            f"<td>{e.get('description','') or '—'}</td>"
            f"<td>{e.get('date','') or 'À définir'}</td>"
            f"<td>Court terme</td>"
            f"</tr>"
        )
    if not actions_rows:
        actions_rows = "<tr><td colspan='4'><em>Aucune action.</em></td></tr>"

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>PV — {type_reunion}</title>
<style>
body{{font-family:-apple-system,Inter,Segoe UI,sans-serif;color:#1f2937;
     max-width:760px;margin:24px auto;padding:0 16px;line-height:1.55}}
h1{{font-size:24px;color:#1e1b4b;border-bottom:2px solid #7c3aed;
   padding-bottom:8px;margin-bottom:18px}}
h2{{font-size:16px;color:#4c1d95;margin-top:24px;margin-bottom:8px;
   text-transform:uppercase;letter-spacing:.5px}}
.meta{{background:#f5f3ff;padding:14px 16px;border-radius:10px;
      border-left:3px solid #7c3aed;font-size:13px;margin-bottom:18px}}
.meta b{{color:#1e1b4b}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin-top:8px}}
th,td{{border:1px solid #e5e7eb;padding:8px 10px;text-align:left;
      vertical-align:top}}
th{{background:#1e1b4b;color:#fff;font-weight:600}}
tr:nth-child(even) td{{background:#fafafa}}
ul{{padding-left:22px;font-size:14px}}
.foot{{margin-top:28px;font-size:11px;color:#6b7280;text-align:center;
      border-top:1px solid #e5e7eb;padding-top:10px}}
</style></head><body>

<h1>Procès-verbal — {type_reunion}</h1>

<div class="meta">
<b>Date :</b> {today}<br>
<b>Type de réunion :</b> {type_reunion}<br>
<b>Animateur :</b> {animateur}<br>
<b>Participants :</b> {", ".join(participants) if participants else "—"}
</div>

<h2>Synthèse</h2>
<p>{resume}</p>

<h2>Décisions prises</h2>
<ul>{li(decisions)}</ul>

<h2>Plan d'action</h2>
<table>
<thead><tr>
<th style="width:30%">Action</th>
<th style="width:30%">Contexte / responsable</th>
<th style="width:20%">Échéance</th>
<th style="width:20%">Priorité</th>
</tr></thead>
<tbody>{actions_rows}</tbody>
</table>

<div class="foot">PV généré automatiquement par l'assistant IA.</div>
</body></html>
"""


# =====================================================
#  Envoi du PV
# =====================================================

def send_pv_to_participants(pv_html: str, participants_emails: list,
                            subject: str = "PV de réunion") -> str:
    """Envoie le PV HTML aux participants. Retourne un résumé texte."""
    if not participants_emails:
        return "❌ Aucun destinataire fourni."
    sent = 0
    errors = []
    for em in participants_emails:
        em = (em or "").strip()
        if not em or "@" not in em:
            errors.append(f"{em} (invalide)")
            continue
        try:
            send_html_email(em, subject, pv_html)
            sent += 1
        except Exception as ex:
            errors.append(f"{em} : {ex}")
    msg = f"✅ PV envoyé à {sent}/{len(participants_emails)} destinataires."
    if errors:
        msg += "\nÉchecs : " + " · ".join(errors[:5])
    return msg


# =====================================================
#  Wrappers Gemini (génération texte, sans tools)
# =====================================================

def _gen_one_shot(prompt: str, temperature=0.5) -> str:
    try:
        r = _g().models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=temperature),
        )
        return r.text or "(pas de réponse)"
    except Exception as e:
        return f"Erreur IA : {e}"


def propose_agenda(type_reunion: str = "Comité de direction",
                   contexte: str = "") -> str:
    """Propose un ordre du jour structuré pour une réunion."""
    prompt = (
        f"Tu es l'assistant d'un directeur. Propose un ordre du jour clair et "
        f"structuré pour une {type_reunion} hebdomadaire. "
        "Liste 5 à 7 points concis et professionnels, numérotés. "
        "Pas de bla-bla, juste la liste prête à l'emploi.\n\n"
    )
    if contexte:
        prompt += f"Contexte / décisions précédentes :\n{contexte[:3000]}\n"
    return _gen_one_shot(prompt, temperature=0.6)


def challenge_meeting(analysis: dict) -> str:
    """À partir d'une analyse de CR, l'IA challenge les décisions et propose."""
    decisions = analysis.get("decisions", []) or []
    taches = analysis.get("taches", []) or []
    resume = analysis.get("resume", "") or ""

    decisions_txt = "\n".join(f"- {d}" for d in decisions) or "(aucune)"
    taches_txt = "\n".join(
        f"- {t.get('titre','')} (deadline: {t.get('deadline','—')})"
        for t in taches
    ) or "(aucune)"

    prompt = (
        "Tu es un copilote stratégique pour un directeur. À partir du "
        "compte-rendu suivant, joue ton rôle de CHALLENGE :\n\n"
        f"Résumé :\n{resume}\n\n"
        f"Décisions :\n{decisions_txt}\n\n"
        f"Actions :\n{taches_txt}\n\n"
        "Tu dois rendre 4 sections courtes, chacune en bullet points :\n"
        "🟣 QUESTIONS À POSER (3 max) — questions critiques non posées\n"
        "🟠 RISQUES IDENTIFIÉS (3 max) — risques / incohérences\n"
        "🔵 ALTERNATIVES POSSIBLES (3 max) — autres options à considérer\n"
        "🟢 ACTIONS MANQUANTES (3 max) — actions oubliées\n\n"
        "Sois concis, factuel, professionnel. Pas d'introduction."
    )
    return _gen_one_shot(prompt, temperature=0.7)


# =====================================================
#  Outils pour l'agent Gemini (interactif)
# =====================================================

def propose_agenda_text(type_reunion: str = "Comité de direction") -> str:
    """Propose un ordre du jour pour une réunion à venir.
    type_reunion : ex. 'Comité de direction', 'Réunion commerciale',
    'Revue financière', 'Réunion marketing'."""
    return propose_agenda(type_reunion)


def challenge_last_meeting_text() -> str:
    """Analyse le dernier compte-rendu PDF traité et challenge ses décisions
    (questions, risques, alternatives, actions manquantes)."""
    from services.pdf_history import list_history
    hist = list_history()
    if not hist:
        return "Aucun compte-rendu n'a encore été analysé."
    return challenge_meeting(hist[0].get("analysis", {}))