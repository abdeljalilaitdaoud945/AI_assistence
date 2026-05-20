import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

from services.calendar_service import get_events, create_event, delete_event, list_upcoming_events
from services.email_service import get_unread_emails_text, send_email

load_dotenv()

try:
    client = genai.Client()
except Exception as e:
    print(f"❌ ERREUR d'initialisation de Gemini : Vérifie ta clé dans le .env. Détails: {e}")

chat_session = None

def start_new_chat():
    global chat_session
    
    mes_outils = [
        get_events, 
        create_event, 
        delete_event, 
        list_upcoming_events,
        get_unread_emails_text, 
        send_email
    ]
    
    config = types.GenerateContentConfig(
        system_instruction=(
            "Tu es l'assistant personnel du directeur d'une entreprise. Tu gères ses mails, son agenda et ses comptes-rendus. "
            "RÈGLE STRICTE POUR L'ENVOI D'EMAILS : Quand l'utilisateur te demande d'envoyer un email, tu DOIS d'abord rédiger un brouillon complet "
            "et lui demander explicitement s'il valide ce contenu. Tu ne dois JAMAIS utiliser l'outil d'envoi d'email avant que "
            "l'utilisateur n'ait répondu par l'affirmative pour valider le brouillon. "
            "N'hésite pas à utiliser tes autres outils pour lire l'agenda ou les mails. Sois professionnel, précis et concis."
        ),
        temperature=0.7,
        tools=mes_outils,
    )
    
    chat_session = client.chats.create(
        model="gemini-2.5-flash",
        config=config
    )

def ask_agent(user_message: str, max_retries=3):
    global chat_session
    
    if chat_session is None:
        start_new_chat()

    for attempt in range(max_retries):
        try:
            response = chat_session.send_message(user_message)
            return response.text

        except Exception as e:
            print(f"⚠️ Tentative {attempt + 1} échouée : {e}")
            
            if "429" in str(e) or "503" in str(e):
                time.sleep(2)
            
            if attempt == max_retries - 1:
                return "Désolé, je rencontre une petite difficulté technique avec mes serveurs Google. Peux-tu reformuler ?"