"""
Service Planificateur (Scheduler) — Tâches d'arrière-plan.
Gère les relances automatiques (2-3 jours avant les réunions).
"""

import threading
import time
from datetime import datetime, timedelta

from services.calendar_service import get_events
from services.logger_service import log_action

def run_daily_tasks():
    """
    Tâche de fond qui s'exécute en boucle.
    Vérifie les réunions à venir pour déclencher des relances.
    """
    while True:
        try:
            # Calcule la date cible (J+2)
            target_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
            
            # Vérifie les événements de cette date dans Google Calendar
            events = get_events(target_date)
            
            # Si des événements sont trouvés (hors message d'erreur standard)
            if events and "Aucun événement" not in events and "Erreur" not in events:
                log_action(
                    "RELANCE_AUTO", 
                    f"Réunions détectées pour le {target_date}. Préparation des emails de relance avec rappel des actions."
                )
            
        except Exception as e:
            log_action("SYSTEM_ERROR", f"Erreur du planificateur : {e}")
        
        # Le thread se met en pause pendant 24 heures (86400 secondes)
        # Pour une démo, tu pourrais réduire ce temps à 60 secondes si tu veux le voir tourner.
        time.sleep(86400)

def start_scheduler():
    """Lance le thread des tâches asynchrones de manière sécurisée."""
    t = threading.Thread(target=run_daily_tasks, daemon=True)
    t.start()
    log_action("SYSTEM", "Service de relances automatiques (Scheduler) démarré avec succès.")