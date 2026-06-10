"""
Service de Gouvernance (Logs) — Trace toutes les actions critiques de l'IA.
Enregistre les données dans agent_logs.json
"""

import json
import os
import threading
from datetime import datetime

# Utilisation du chemin absolu pour éviter les erreurs d'import
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(BASE_DIR, "agent_logs.json")

_lock = threading.Lock()

def log_action(category: str, description: str):
    """
    Enregistre une action de l'agent IA.
    Exemples de catégories : EMAIL_OUT, EVENT_CREATED, SYSTEM, SECURITY
    """
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "category": category,
        "description": description
    }
    
    with _lock:
        try:
            logs = []
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            
            # Insère la nouvelle action au début de la liste
            logs.insert(0, entry)
            
            # Limite à 200 logs pour ne pas alourdir le fichier
            logs = logs[:200]
            
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[logger] Erreur d'écriture des logs : {e}")

def get_logs() -> list:
    """Récupère l'historique des actions pour l'affichage dans l'interface."""
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []