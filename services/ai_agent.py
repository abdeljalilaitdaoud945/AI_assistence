import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

# --- IMPORTATION DES OUTILS ---
from services.calendar_service import get_events, create_event, delete_event, list_upcoming_events
from services.email_service import get_unread_emails_text, send_email

# Charger les variables d'environnement
load_dotenv()

# Initialisation du NOUVEAU client Google GenAI
try:
    client = genai.Client()
except Exception as e:
    print(f"❌ ERREUR d'initialisation de Gemini : Vérifie ta clé dans le .env. Détails: {e}")

# Variable pour maintenir l'historique de la conversation
chat_session = None

def start_new_chat():
    """Initialise une nouvelle session de chat avec le nouveau SDK et les outils."""
    global chat_session
    
    # 1. On déclare la liste des outils disponibles pour l'IA
    mes_outils = [
        get_events, 
        create_event, 
        delete_event, 
        list_upcoming_events,
        get_unread_emails_text, 
        send_email
    ]
    
    # 2. Configuration moderne avec intégration des outils et règles de sécurité
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
    """
    Envoie un message à Gemini avec le nouveau système.
    """
    global chat_session
    
    if chat_session is None:
        start_new_chat()

    for attempt in range(max_retries):
        try:
            # Le SDK genai gère automatiquement l'exécution des fonctions Python en arrière-plan !
            response = chat_session.send_message(user_message)
            return response.text

        except Exception as e:
            print(f"⚠️ Tentative {attempt + 1} échouée : {e}")
            
            if "429" in str(e) or "503" in str(e):
                time.sleep(2)
            
            if attempt == max_retries - 1:
                return "Désolé, je rencontre une petite difficulté technique avec mes serveurs Google. Peux-tu reformuler ?"

# Test local
if __name__ == "__main__":
    print("--- Test du Nouvel Agent GenAI avec Outils ---")
    reponse = ask_agent("Rédige un mail à test@gmail.com pour dire que le projet avance bien, et envoie-le.")
    print(f"IA : {reponse}")