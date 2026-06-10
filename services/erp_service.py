"""
Service ERP (Simulation) — Pilotage de la performance et recommandations IA.
Génère des données fictives de CA, marges et retards pour simuler un vrai SI.
"""

import json
from google import genai

# =====================================================================
# SIMULATION DES DONNÉES ERP
# =====================================================================

ERP_DATA = {
    "chiffre_affaires": {
        "realise": 1250000,
        "objectif": 1500000,
        "devise": "MAD"
    },
    "marge_globale": {
        "realise": 24.5,
        "objectif": 28.0,
        "unite": "%"
    },
    "projets_en_retard": [
        {"client": "TechCorp", "projet": "Déploiement Serveurs", "retard_jours": 12, "impact_estime": 45000},
        {"client": "MegaBank", "projet": "Audit Sécurité", "retard_jours": 5, "impact_estime": 15000}
    ],
    "top_ventes": [
        {"produit": "Licence Enterprise", "quantite": 45, "ca_genere": 450000},
        {"produit": "Consulting IT", "quantite": 120, "ca_genere": 360000}
    ]
}

def get_erp_data() -> dict:
    """Retourne les données ERP simulées."""
    return ERP_DATA

def get_erp_summary_text() -> str:
    """Formate les données ERP en texte pour l'agent IA."""
    data = get_erp_data()
    ca = data["chiffre_affaires"]
    marge = data["marge_globale"]
    
    lines = ["📊 Synthèse ERP (Performance) :\n"]
    lines.append(f"• Chiffre d'affaires : {ca['realise']:,} / {ca['objectif']:,} {ca['devise']}")
    lines.append(f"• Marge globale : {marge['realise']}% (Objectif: {marge['objectif']}%)")
    
    retards = data.get("projets_en_retard", [])
    if retards:
        lines.append("\n⚠️ Projets en retard :")
        for r in retards:
            lines.append(f"  - {r['projet']} ({r['client']}) : {r['retard_jours']} jours de retard (Impact: {r['impact_estime']} {ca['devise']})")
            
    return "\n".join(lines)

def generate_erp_recommendations() -> str:
    """Demande à Gemini d'analyser les données ERP et de proposer un plan d'action."""
    try:
        client = genai.Client()
        data_str = json.dumps(ERP_DATA, indent=2, ensure_ascii=False)
        prompt = (
            "Tu es un directeur des opérations et financier. Analyse ces données issues de notre ERP :\n"
            f"{data_str}\n\n"
            "Rédige une analyse concise avec :\n"
            "1. Le constat principal sur le CA et la marge.\n"
            "2. Les risques liés aux retards.\n"
            "3. Trois recommandations ou plans d'action correctifs immédiats.\n"
            "Sois direct et professionnel."
        )
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return response.text
    except Exception as e:
        return f"Erreur lors de l'analyse IA : {e}"