import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

from services.calendar_service import (
    get_events_text, create_event, delete_event, list_upcoming_events_text,
)
from services.email_service import get_unread_emails_text, send_email
from services.stock_service import (
    get_stock_price_text,
    get_market_summary_text,
    get_market_stocks_text,
    search_symbol_text,
    compare_stocks_text,
)
from services.pdf_history import get_pdf_history_text
from services.meeting_service import (
    propose_agenda_text,
    challenge_last_meeting_text,
)
from services.business_tracker import (
    list_deals_text,
    get_deals_followup_text,
)
from services.mail_classifier import (
    list_clients_text,
    get_priority_emails_text,
)
from services.erp_service import get_erp_summary_text

load_dotenv()

try:
    client = genai.Client()
except Exception as e:
    print(f"❌ ERREUR d'initialisation de Gemini : Vérifie ta clé dans le .env. Détails: {e}")

chat_session = None

def start_new_chat():
    global chat_session
    
    mes_outils = [
        get_events_text, 
        create_event, 
        delete_event, 
        list_upcoming_events_text,
        get_unread_emails_text, 
        send_email,
        # ----- Bourse -----
        get_stock_price_text,
        get_market_summary_text,
        get_market_stocks_text,
        search_symbol_text,
        compare_stocks_text,
        # ----- PDFs / comptes-rendus -----
        get_pdf_history_text,
        propose_agenda_text,
        challenge_last_meeting_text,
        # ----- Dossiers commerciaux -----
        list_deals_text,
        get_deals_followup_text,
        # ----- Classement mails -----
        list_clients_text,
        get_priority_emails_text,
        # ----- ERP / Performance -----
        get_erp_summary_text,
    ]
    
    config = types.GenerateContentConfig(
        system_instruction=(
            "Tu es l'assistant personnel du directeur d'une entreprise. Tu gères ses mails, son agenda, ses comptes-rendus, "
            "ses dossiers commerciaux et tu as accès aux marchés financiers via tes outils.\n"
            "RÈGLE STRICTE POUR L'ENVOI D'EMAILS : Quand l'utilisateur te demande d'envoyer un email, tu DOIS d'abord rédiger un brouillon complet "
            "et lui demander explicitement s'il valide ce contenu. Tu ne dois JAMAIS utiliser l'outil d'envoi d'email avant que "
            "l'utilisateur n'ait répondu par l'affirmative pour valider le brouillon.\n"
            "POUR L'ERP / PERFORMANCE : utilise `get_erp_summary_text` pour connaître le Chiffre d'Affaires, la marge globale, et surtout les projets en retard qui nécessitent une alerte.\n"
            "POUR LA BOURSE : si l'utilisateur cite un nom d'entreprise sans symbole, utilise d'abord `search_symbol_text` "
            "pour trouver le bon ticker, puis `get_stock_price_text`. Pour un point marché global, utilise `get_market_summary_text`.\n"
            "Sois professionnel, précis et concis. Joue un rôle de copilote stratégique : propose, challenge, alerte."
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