"""
Service ERP (Simulation) — Pilotage de la performance et recommandations IA.
Génère des données fictives ultra-réalistes (CA, marges, trésorerie, factures, retards).
"""

import json
from google import genai

# =====================================================================
# SIMULATION DES DONNÉES ERP (Rich Mock Data)
# =====================================================================

ERP_DATA = {
    "finance": {
        "chiffre_affaires": {
            "realise_ytd": 12500000,
            "objectif_ytd": 15000000,
            "tendance_mensuelle": "baisse (-5%)",
            "devise": "MAD"
        },
        "marge_globale": {
            "realise": 22.5,
            "objectif": 28.0,
            "unite": "%"
        },
        "tresorerie": {
            "disponible": 850000,
            "seuil_alerte": 1000000,
            "statut": "critique"
        },
        "factures_impayees": {
            "montant_total": 420000,
            "clients_principaux": ["Groupe ONA", "Ministère de la Santé", "TechCorp"]
        }
    },
    "operations": {
        "projets_en_retard": [
            {
                "client": "TechCorp", 
                "projet": "Migration Cloud AWS", 
                "retard_jours": 18, 
                "impact_estime": 120000,
                "cause": "Manque de ressources DevOps seniors"
            },
            {
                "client": "MegaBank", 
                "projet": "Audit de Sécurité SI", 
                "retard_jours": 7, 
                "impact_estime": 45000,
                "cause": "Attente des accès VPN côté client"
            },
            {
                "client": "AutoMaroc", 
                "projet": "Déploiement ERP", 
                "retard_jours": 25, 
                "impact_estime": 250000,
                "cause": "Changement de périmètre (Scope creep)"
            }
        ],
        "top_ventes_services": [
            {"service": "Intégration Cybersécurité", "ca_genere": 4500000, "croissance": "+15%"},
            {"service": "Consulting Cloud", "ca_genere": 3200000, "croissance": "+8%"},
            {"service": "Support & Maintenance", "ca_genere": 1800000, "croissance": "-2%"}
        ],
        "taux_occupation_equipes": 92.5  # %
    }
}

def get_erp_data() -> dict:
    """Retourne les données ERP simulées."""
    return ERP_DATA

def get_erp_summary_text() -> str:
    """Formate les données ERP en texte pour l'agent IA (outils MCP)."""
    data = get_erp_data()
    fin = data["finance"]
    ops = data["operations"]
    ca = fin["chiffre_affaires"]
    
    lines = ["📊 Synthèse ERP (Performance & Opérations) :\n"]
    lines.append(f"• CA (YTD) : {ca['realise_ytd']:,} / {ca['objectif_ytd']:,} {ca['devise']} ({ca['tendance_mensuelle']})")
    lines.append(f"• Marge : {fin['marge_globale']['realise']}% (Obj: {fin['marge_globale']['objectif']}%)")
    lines.append(f"• Trésorerie : {fin['tresorerie']['disponible']:,} {ca['devise']} (Statut: {fin['tresorerie']['statut']})")
    lines.append(f"• Factures impayées : {fin['factures_impayees']['montant_total']:,} {ca['devise']}")
    
    retards = ops.get("projets_en_retard", [])
    if retards:
        lines.append("\n⚠️ Projets critiques en retard :")
        for r in retards:
            lines.append(f"  - {r['projet']} ({r['client']}) : {r['retard_jours']} jours | Cause: {r['cause']} | Impact: {r['impact_estime']:,} {ca['devise']}")
            
    return "\n".join(lines)

def generate_erp_recommendations() -> str:
    """Demande à Gemini d'analyser les données complexes et de proposer un plan d'action."""
    try:
        client = genai.Client()
        data_str = json.dumps(ERP_DATA, indent=2, ensure_ascii=False)
        prompt = (
            "Tu es le Directeur Général Adjoint (stratégie et finance). Analyse ces données complexes issues de notre ERP :\n"
            f"{data_str}\n\n"
            "Rédige une note stratégique très professionnelle (max 300 mots) structurée ainsi :\n"
            "1. 🔴 ALERTE FINANCIÈRE : Analyse la trésorerie, le CA et les impayés.\n"
            "2. 🟠 RISQUES OPÉRATIONNELS : Analyse les retards (mentionne les causes et clients) et le taux d'occupation.\n"
            "3. 🟢 PLAN D'ACTION IMMÉDIAT : 3 directives claires et actionnables pour le CODIR.\n"
            "Sois percutant, utilise un vocabulaire de pilotage d'entreprise."
        )
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return response.text
    except Exception as e:
        return f"Erreur lors de l'analyse IA : {e}"