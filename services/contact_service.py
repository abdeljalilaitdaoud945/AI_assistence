"""
Service de gestion des contacts.
Sauvegarde locale dans contacts.json.
"""

import json
import os
import uuid

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE_PATH = os.path.join(BASE_DIR, "contacts.json")

def get_contacts() -> list:
    if not os.path.exists(FILE_PATH):
        return []
    try:
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_contact(nom: str, email: str, role: str = ""):
    contacts = get_contacts()
    nouveau = {
        "id": str(uuid.uuid4()),
        "nom": nom,
        "email": email,
        "role": role
    }
    contacts.append(nouveau)
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(contacts, f, ensure_ascii=False, indent=2)

def delete_contact(contact_id: str):
    contacts = get_contacts()
    contacts = [c for c in contacts if c.get("id") != contact_id]
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(contacts, f, ensure_ascii=False, indent=2)