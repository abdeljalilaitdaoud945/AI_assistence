import os, json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/tasks",
    'https://www.googleapis.com/auth/gmail.send'
]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")
CREDS_PATH = os.path.join(BASE_DIR, "credentials.json")

def get_credentials():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=8551, prompt="consent")
        
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    
    return creds

def get_user_info(creds):
    service = build("oauth2", "v2", credentials=creds)
    user = service.userinfo().get().execute()
    return {
        "nom": user.get("family_name", ""),
        "prenom": user.get("given_name", ""),
        "email": user.get("email", ""),
        "photo": user.get("picture", ""),
    }

def logout():
    if os.path.exists(TOKEN_PATH):
        os.remove(TOKEN_PATH)