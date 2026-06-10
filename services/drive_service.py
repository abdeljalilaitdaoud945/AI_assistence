"""
Service Google Drive — lecture seule.

Le scope drive.readonly est déjà demandé dans google_auth.py donc on
peut directement lister et télécharger des PDFs.
"""

import io
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from services.google_auth import get_credentials


def _service():
    creds = get_credentials()
    return build("drive", "v3", credentials=creds)


def list_pdfs_on_drive(max_results: int = 50, query_extra: str = "") -> list[dict]:
    """
    Liste les PDFs accessibles sur le Drive de l'utilisateur, triés par
    date de modification décroissante.
    """
    try:
        svc = _service()
        q = "mimeType='application/pdf' and trashed=false"
        if query_extra:
            q += f" and {query_extra}"
        results = svc.files().list(
            q=q,
            pageSize=max_results,
            fields="files(id, name, modifiedTime, size, webViewLink)",
            orderBy="modifiedTime desc",
        ).execute()
        return results.get("files", [])
    except Exception as e:
        print(f"[drive_service] list_pdfs error: {e}")
        return []


def download_pdf_from_drive(file_id: str) -> Optional[bytes]:
    """Télécharge le PDF en bytes. None si erreur."""
    try:
        svc = _service()
        request = svc.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _status, done = downloader.next_chunk()
        return buf.getvalue()
    except Exception as e:
        print(f"[drive_service] download error: {e}")
        return None


def search_pdfs(name_query: str, max_results: int = 30) -> list[dict]:
    """Recherche les PDFs dont le nom contient name_query."""
    safe_q = (name_query or "").replace("'", "")
    extra = f"name contains '{safe_q}'" if safe_q else ""
    return list_pdfs_on_drive(max_results=max_results, query_extra=extra)