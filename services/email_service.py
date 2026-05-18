
from services.google_auth import get_credentials

def get_emails_data(limit: int = 5, unread_only: bool = True) -> list:
    """Récupère les emails sous forme de liste de dictionnaires pour l'interface Flet."""
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
            snippet = msg_data.get('snippet', '') # Le petit résumé du mail
            
            for header in headers:
                if header['name'] == 'Subject':
                    sujet = header['value']
                elif header['name'] == 'From':
                    expediteur = header['value']
            
            expediteur_propre = expediteur.split('<')[0].strip() if '<' in expediteur else expediteur
            
            # On ajoute chaque mail sous forme de dictionnaire
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