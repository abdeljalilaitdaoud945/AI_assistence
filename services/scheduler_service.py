"""
Service Planificateur (Scheduler) — Tâches d'arrière-plan.
Gère les relances automatiques (2-3 jours avant les réunions) et le rappel des actions.
"""

import threading
import time
from datetime import datetime, timedelta

from services.calendar_service import get_events
from services.logger_service import log_action
from services.pdf_history import list_history

# --- SÉCURITÉ ANTI-DOUBLON ---
_scheduler_started = False
_lock = threading.Lock()

def run_daily_tasks():
    """
    Tâche de fond qui s'exécute en boucle.
    Vérifie les réunions à venir pour déclencher des relances intelligentes.
    """
    while True:
        try:
            # Calcule la date cible (J+2)
            target_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
            
            # Vérifie les événements de cette date dans Google Calendar
            events = get_events(target_date)
            
            # Si des événements sont trouvés (hors message d'erreur standard)
            if events and "Aucun événement" not in events and "Erreur" not in events:
                
                # 1. On va chercher les tâches du dernier compte-rendu
                hist = list_history()
                taches_txt = "(Aucune action précédente enregistrée dans le système)"
                
                if hist:
                    derniere_analyse = hist[0].get("analysis", {})
                    taches = derniere_analyse.get("taches", [])
                    if taches:
                        # On formate la liste des actions à rappeler
                        lignes_taches = []
                        for t in taches:
                            titre = t.get('titre', 'Tâche inconnue')
                            desc = t.get('description', 'Non assigné')
                            deadline = t.get('deadline', 'Aucune')
                            lignes_taches.append(f"  - {titre} (Resp/Contexte: {desc}) | Échéance: {deadline}")
                        
                        taches_txt = "\n".join(lignes_taches)
                
                # 2. On génère le corps du mail de relance
                mail_body = (
                    f"Bonjour à tous,\n\n"
                    f"Ceci est une relance automatique de votre Assistant IA concernant "
                    f"vos engagements pour la journée du {target_date}.\n\n"
                    f"📅 Événements prévus :\n{events}\n\n"
                    f"⚠️ Rappel de vos actions en attente :\n{taches_txt}\n\n"
                    f"Merci de mettre à jour votre avancement avant la réunion.\n"
                )
                
                # 3. On enregistre cette relance officielle dans la gouvernance
                log_action(
                    "RELANCE_AUTO", 
                    f"Email de relance généré pour le {target_date}.\nContenu :\n{mail_body}"
                )
            
        except Exception as e:
            log_action("SYSTEM_ERROR", f"Erreur du planificateur : {e}")
        
        # Le thread se met en pause pendant 24 heures (86400 secondes)
        # Laisse ça à 86400 pour un usage normal, ou mets 10 (secondes) si tu veux tester rapidement.
        time.sleep(86400)

def start_scheduler():
    """Lance le thread des tâches asynchrones de manière sécurisée (une seule fois)."""
    global _scheduler_started
    
    with _lock:
        if _scheduler_started:
            return  # Si déjà lancé, on ignore silencieusement
        _scheduler_started = True

    t = threading.Thread(target=run_daily_tasks, daemon=True)
    t.start()
    log_action("SYSTEM", "Service de relances automatiques (Scheduler) démarré avec succès.")