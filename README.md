# INPT App — Assistant IA de Direction

Application desktop/web d'assistance stratégique pour directeur d'entreprise, construite avec **Flet** (Python/Flutter) et propulsée par **Google Gemini 2.5 Flash**.

---

## Aperçu

INPT App centralise en une seule interface : emails Gmail, agenda Google Calendar, marchés financiers en temps réel, données ERP (Excel), comptes-rendus de réunions (PDF), pipeline commercial, et un assistant IA conversationnel. Un serveur MCP expose également les outils à des agents externes comme Claude Desktop.

---

## Architecture

```
AppZ1.py                  ← Point d'entrée (Flet + routeur)
├── vues/                 ← Pages UI (une par vue)
│   home, mails, mailtotal, rdv, calendrier, AIassistant,
│   bourse, pdf, business, erp, reunion, contacts, settings
├── services/             ← Logique métier (Python pur)
│   google_auth, email_service, calendar_service, drive_service,
│   stock_service, erp_service, pdf_service, pdf_history,
│   meeting_service, business_tracker, contact_service,
│   mail_classifier, scheduler_service, logger_service, ai_agent
└── mcp_server.py         ← Serveur MCP (outils exposés aux agents externes)
```

---

## Technologies

| Couche | Technologie |
|---|---|
| UI | Flet (Python/Flutter) |
| LLM / IA | Google Gemini 2.5 Flash (google-genai) |
| Serveur MCP | FastMCP |
| APIs Google | Gmail, Calendar, Drive, OAuth2, Tasks |
| Données boursières | yfinance (aucune clé API requise) |
| Lecture PDF | pypdf |
| Données ERP | openpyxl — lit `erp_data.xlsx` |
| Sorties structurées IA | Pydantic |
| Persistance locale | JSON (`contacts.json`, `business_deals.json`, `mail_tags.json`, `pdf_history.json`, `agent_logs.json`) |

---

## Fonctionnalités

### 📧 Gmail
- Lecture des emails non lus (snippet + corps complet)
- Envoi d'emails (texte brut et HTML)
- Brouillons de réponse générés par Gemini (ton au choix)
- Classification automatique des emails par IA (commercial, finance, interne, etc.)

### 📅 Agenda Google Calendar
- Affichage calendrier mensuel et événements du jour
- Création et suppression d'événements (fuseau Africa/Casablanca)
- Consultation des prochains N événements

### 🤖 Assistant IA (Gemini 2.5 Flash)
- Session de chat multi-tours avec 20 outils disponibles
- Copilote stratégique : propose, challenge, alerte
- Règle stricte : validation obligatoire de l'utilisateur avant tout envoi d'email
- Retry automatique avec backoff sur erreurs 429/503

### 📈 Bourse
- Cours en temps réel via yfinance (cache 30 s)
- Marchés : 🇲🇦 Casablanca, 🇺🇸 Wall Street, 🇫🇷 Paris, 🇸🇦 Tadawul, Cryptos
- Fiche complète : prix, variation, 52 sem. haut/bas, P/E, bêta, cap. boursière
- Historique OHLCV, recherche de symbole, comparaison multi-valeurs

### 🏢 ERP / Business Intelligence
- Lecture du fichier Excel `erp_data.xlsx` (5 onglets : Finance, Factures, Projets, Ventes, README)
- KPIs : CA YTD vs objectif, marge %, trésorerie, factures impayées
- Projets en retard avec cause et impact financier
- Note stratégique CODIR générée par Gemini (alertes, risques, actions)
- Fallback automatique sur données simulées si le fichier est absent

### 📄 Comptes-rendus de réunion (PDF)
- Import PDF local ou depuis Google Drive
- Analyse Gemini (sortie structurée Pydantic) : résumé, participants, décisions, RDV, tâches
- Génération de PV HTML formel + envoi aux participants
- Proposition d'ordre du jour pour la prochaine réunion
- Mode Challenge : Gemini challenge les décisions (questions, risques, alternatives, actions manquantes)
- Historique sauvegardé dans `pdf_history.json`

### 💼 Pipeline Commercial
- CRM 6 étapes : demande → offre → relance → négociation → gagné / perdu
- CRUD sur les dossiers (stocké dans `business_deals.json`)
- Détection des dossiers sans activité récente
- Brouillons d'offres commerciales générés par Gemini

### 📌 Contacts
- Carnet d'adresses local (JSON) avec nom, email, rôle
- Ajout / suppression de contacts

### ⚙️ Gouvernance & Logs
- Toutes les actions critiques de l'IA sont tracées dans `agent_logs.json`
- Catégories : `EMAIL_OUT`, `EVENT_CREATED`, `EVENT_DELETED`, `RELANCE_AUTO`, `SYSTEM`, `SYSTEM_ERROR`
- Écriture thread-safe, historique limité à 200 entrées
- Visible dans la vue Settings

### 🔄 Planificateur (Background)
- Thread daemon lancé au démarrage, cycle de 24 heures
- Vérifie le calendrier à J+2
- Génère un email de relance automatique avec les événements et les actions en attente du dernier CR
- Loggé dans la gouvernance

### 🔌 Serveur MCP (`mcp_server.py`)
- Serveur FastMCP standalone (13 outils exposés)
- Permet à des agents externes (Claude Desktop, etc.) d'accéder aux données de l'app
- Outils : CRUD agenda, lecture/envoi email, cotations boursières, historique PDF, résumé ERP

---

## Prérequis

- Python 3.13+
- Un projet Google Cloud avec les APIs activées : Gmail, Calendar, Drive, Tasks, OAuth2
- Une clé API Google Gemini (`GEMINI_API_KEY` dans `.env`)
- Le fichier `credentials.json` issu de la Google Cloud Console

---

## Installation

```bash
# Cloner le dépôt
git clone <url-du-repo>
cd inptapp2

# Créer et activer l'environnement virtuel
python -m venv .inptappvenv
.inptappvenv\Scripts\activate   # Windows

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
# → Remplir GEMINI_API_KEY dans .env
# → Placer credentials.json à la racine
```

---

## Lancement

```bash
# Lancer l'application principale
python AppZ1.py

# Lancer le serveur MCP (optionnel, pour agents externes)
python mcp_server.py
```

Au premier lancement, une fenêtre de consentement Google OAuth s'ouvre dans le navigateur. Le token est ensuite sauvegardé dans `token.json` et rafraîchi automatiquement.

---

## Structure des données locales

| Fichier | Contenu |
|---|---|
| `agent_logs.json` | Journal de gouvernance des actions IA |
| `business_deals.json` | Dossiers du pipeline commercial |
| `contacts.json` | Carnet d'adresses |
| `mail_tags.json` | Cache des classifications d'emails |
| `pdf_history.json` | Historique des comptes-rendus analysés |
| `erp_data.xlsx` | Données ERP modifiables dans Excel |

---

## Configuration ERP

Ouvrir `erp_data.xlsx` dans Excel et remplir les 5 onglets :

- **Finance** : CA, marge, trésorerie, taux d'occupation
- **FacturesImpayees** : liste des factures avec formule SUMIF
- **Projets** : projets en retard, cause, impact
- **Ventes** : CA par service avec taux de croissance
- **README** : instructions intégrées

L'application relit le fichier à chaque ouverture de la vue ERP.

---

## Sécurité & Bonnes pratiques

- Ne jamais committer `token.json`, `credentials.json`, ni `.env` (ajoutés dans `.gitignore`)
- Le mode démo (`DEMO_MODE=true` dans `.env`) bloque les envois réels et les écritures agenda
- L'IA ne peut envoyer un email qu'après validation explicite de l'utilisateur
- Toutes les actions critiques sont tracées dans le journal de gouvernance

---

## Licence

Usage privé / interne. Voir le responsable du projet pour toute redistribution.