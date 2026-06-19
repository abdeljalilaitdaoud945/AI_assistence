import base64
import re
from email.message import EmailMessage
from services.google_auth import get_credentials
from googleapiclient.discovery import build
from google import genai

# Ajout pour la gouvernance
from services.logger_service import log_action

def _decode_b64url(s):
    if not s:
        return ""
    try:
        padding = "=" * (-len(s) % 4)
        return base64.urlsafe_b64decode(s + padding).decode("utf-8", errors="replace")
    except Exception:
        return ""

def _extract_body_parts(payload):
    if not payload:
        return ""
    mime = payload.get("mimeType", "")
    body = payload.get("body", {}) or {}
    data = body.get("data")

    if data and "text/plain" in mime:
        return _decode_b64url(data)

    parts = payload.get("parts") or []
    for p in parts:
        txt = _extract_body_parts(p)
        if txt and "text/plain" in (p.get("mimeType") or ""):
            return txt

    for p in parts:
        if (p.get("parts") or []):
            txt = _extract_body_parts(p)
            if txt:
                return txt

    for p in parts:
        if "text/html" in (p.get("mimeType") or ""):
            html = _decode_b64url(p.get("body", {}).get("data", ""))
            return _strip_html(html)

    if data and "text/html" in mime:
        return _strip_html(_decode_b64url(data))
    return ""

def _strip_html(html):
    if not html:
        return ""
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</p>", "\n\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", html)
    text = (text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<")
                .replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'"))
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()

def get_emails_data(limit: int = 5, unread_only: bool = True) -> list:
    try:
        creds = get_credentials()
        service = build('gmail', 'v1', credentials=creds)
        labels = ['INBOX']
        if unread_only:
            labels.append('UNREAD')

        results = service.users().messages().list(userId='me', labelIds=labels, maxResults=limit).execute()
        messages = results.get('messages', [])
        email_list = []

        if not messages:
            return email_list

        for msg in messages:
            msg_data = service.users().messages().get(
                userId='me', id=msg['id'], format='metadata', metadataHeaders=['Subject', 'From']
            ).execute()
            
            headers = msg_data['payload']['headers']
            sujet = "Sans objet"
            expediteur = "Inconnu"
            snippet = msg_data.get('snippet', '')
            
            for header in headers:
                if header['name'] == 'Subject':
                    sujet = header['value']
                elif header['name'] == 'From':
                    expediteur = header['value']
            
            expediteur_propre = expediteur.split('<')[0].strip() if '<' in expediteur else expediteur
            email_list.append({
                "id": msg['id'], "expediteur": expediteur_propre, "sujet": sujet, "snippet": snippet
            })
        return email_list
    except Exception as e:
        print(f"Erreur Gmail: {e}")
        return []

def get_unread_emails_text(limit: int = 5) -> str:
    emails = get_emails_data(limit, unread_only=True)
    if not emails:
        return "Vous n'avez aucun email non lu pour le moment."
    texte_ia = "Voici les derniers emails non lu :\n\n"
    for mail in emails:
        texte_ia += f"📧 De : {mail['expediteur']}\nSujet : {mail['sujet']}\nRésumé : {mail['snippet']}\n\n"
    return texte_ia

def send_email(destinataire: str, sujet: str, contenu: str) -> str:
    # ----- Garde-fou Mode Démo (silencieux si module absent) -----
    try:
        from services.demo_mode import is_demo_mode, log_demo_action
        if is_demo_mode():
            msg = log_demo_action("send_email", {
                "destinataire": destinataire, "sujet": sujet,
                "contenu_preview": (contenu or "")[:200],
            })
            log_action("EMAIL_DEMO", f"[DÉMO] envoi simulé à {destinataire}")
            return msg
    except ImportError:
        pass
    # -------------------------------
    try:
        creds = get_credentials()
        service = build('gmail', 'v1', credentials=creds)
        message = EmailMessage()
        message.set_content(contenu)
        message['To'] = destinataire
        message['Subject'] = sujet

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}
        service.users().messages().send(userId="me", body=create_message).execute()
        
        # Enregistrement dans les logs de gouvernance
        log_action("EMAIL_OUT", f"Email envoyé à {destinataire}. Sujet: {sujet}")
        
        return f"✅ Email envoyé avec succès à {destinataire} !"
    except Exception as e:
        log_action("EMAIL_ERROR", f"Échec d'envoi à {destinataire} : {str(e)}")
        return f"❌ Erreur lors de l'envoi de l'email : {str(e)}"

def get_email_full(message_id: str) -> dict:
    try:
        creds = get_credentials()
        service = build('gmail', 'v1', credentials=creds)
        msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
        headers = msg.get('payload', {}).get('headers', []) or []
        h = {x['name'].lower(): x['value'] for x in headers}
        body = _extract_body_parts(msg.get('payload', {}))
        if not body:
            body = msg.get('snippet', '')

        return {
            "id": message_id, "sender": h.get("from", ""), "to": h.get("to", ""),
            "subject": h.get("subject", "(sans objet)"), "date": h.get("date", ""),
            "body": body, "error": None,
        }
    except Exception as e:
        return {
            "id": message_id, "sender": "", "to": "", "subject": "(erreur)",
            "date": "", "body": "", "error": str(e),
        }

def send_html_email(destinataire: str, sujet: str, html_body: str) -> str:
    # ----- Garde-fou Mode Démo (silencieux si module absent) -----
    try:
        from services.demo_mode import is_demo_mode, log_demo_action
        if is_demo_mode():
            msg = log_demo_action("send_email", {
                "destinataire": destinataire, "sujet": sujet,
                "type": "HTML (PV)",
                "html_preview": (html_body or "")[:300],
            })
            log_action("EMAIL_DEMO_HTML", f"[DÉMO] envoi HTML simulé à {destinataire}")
            return msg
    except ImportError:
        pass
    # -------------------------------
    try:
        creds = get_credentials()
        service = build('gmail', 'v1', credentials=creds)
        message = EmailMessage()
        message.set_content("Voir version HTML.")
        message.add_alternative(html_body, subtype="html")
        message['To'] = destinataire
        message['Subject'] = sujet

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId="me", body={'raw': raw}).execute()
        
        log_action("EMAIL_OUT_HTML", f"Email HTML (PV) envoyé à {destinataire}. Sujet: {sujet}")
        return f"✅ Email envoyé à {destinataire}"
    except Exception as e:
        return f"❌ Erreur envoi HTML à {destinataire} : {e}"

def generate_email_reply(subject: str, body: str, tone: str = "cordial") -> str:
    """Génère un brouillon de réponse à un email en fonction du ton choisi."""
    try:
        client = genai.Client()
        prompt = (
            f"Tu es l'assistant d'un directeur. Rédige une réponse directe et professionnelle à cet email.\n"
            f"Ton imposé : {tone}.\n\n"
            f"Sujet de l'email reçu : {subject}\n"
            f"Contenu de l'email reçu :\n{body[:3000]}\n\n"
            "Ne rédige que le corps du mail de réponse. Ne mets pas d'objet. Reste concis."
        )
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return response.text
    except Exception as e:
        return f"Erreur IA : {e}"