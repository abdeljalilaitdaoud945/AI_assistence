import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Charger les variables d'environnement
load_dotenv()

# Initialisation du NOUVEAU client Google GenAI
# Il détecte automatiquement la variable GEMINI_API_KEY dans le .env
try:
    client = genai.Client()
except Exception as e:
    print(f"❌ ERREUR d'initialisation de Gemini : Vérifie ta clé dans le .env. Détails: {e}")

# Variable pour maintenir l'historique de la conversation
chat_session = None

def start_new_chat():
    """Initialise une nouvelle session de chat avec le nouveau SDK"""
    global chat_session
    
    # Configuration moderne
    config = types.GenerateContentConfig(
        system_instruction="Tu es l'assistant personnel du directeur d'une entreprise . Tu gères ses mails, son agenda et ses comptes-rendus. Sois professionnel, précis et concis.",
        temperature=0.7,
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
            # Envoi du message avec la nouvelle méthode
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
    print("--- Test du Nouvel Agent GenAI ---")
    reponse = ask_agent("Bonjour, es-tu bien mis à jour ?")
    print(f"IA : {reponse}")