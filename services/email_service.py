import base64
from email.message import EmailMessage
from services.google_auth import get_credentials
from googleapiclient.discovery import build

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
                userId='me', 
                id=msg['id'], 
                format='metadata', 
                metadataHeaders=['Subject', 'From']
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
                "id": msg['id'],
                "expediteur": expediteur_propre,
                "sujet": sujet,
                "snippet": snippet
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
        return f"✅ Email envoyé avec succès à {destinataire} !"

    except Exception as e:
        return f"❌ Erreur lors de l'envoi de l'email : {str(e)}"