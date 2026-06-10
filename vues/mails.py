"""
Vue Mails — Arc-inspired, lisible et aéré.

Améliorations :
  - Avatar initiale (cercle accent)
  - Sender en haut, sujet en gras, snippet en gris clair
  - Dot accent pour les non-lus
  - Espacement généreux
  - Bouton "Tout voir" → mailtotal
"""

import re
import threading

import flet as ft

from vues import theme as T
from vues.theme import C, FONT
from vues.navbar import build_navbar
from services.email_service import get_emails_data


# ----- Helpers -----

def _clean_text(s):
    """Nettoyage léger : retire entités, espaces multiples, etc."""
    if not s: return ""
    s = re.sub(r"\s+", " ", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&")
    s = s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    return s.strip()


def _parse_sender(raw):
    """
    Extrait (nom, email) d'un sender genre 'Jean Dupont <jean@x.com>'.
    Retourne (display, email) ; si pas de nom, display = email.
    """
    if not raw:
        return ("?", "")
    m = re.match(r'\s*"?([^"<]+?)"?\s*<\s*([^>]+)\s*>\s*$', raw)
    if m:
        return (m.group(1).strip() or m.group(2).strip(), m.group(2).strip())
    return (raw.strip(), raw.strip())


def _initial(name):
    name = (name or "?").strip()
    if not name: return "?"
    parts = name.split()
    if len(parts) >= 2 and parts[0] and parts[1]:
        return (parts[0][0] + parts[1][0]).upper()
    return name[0].upper()


def _avatar(name, size=36):
    """Avatar cercle avec initiale (couleur dérivée du nom)."""
    palette = [C.accent, C.info, C.success, C.warning, "#F472B6",
               "#22D3EE", "#FB7185"]
    color = palette[abs(hash(name)) % len(palette)] if name else C.accent
    return ft.Container(
        width=size, height=size,
        border_radius=size,
        bgcolor=ft.Colors.with_opacity(0.18, color),
        alignment=ft.Alignment.CENTER,
        content=ft.Text(_initial(name),
                        color=color,
                        weight=ft.FontWeight.W_700,
                        size=int(size / 2.5)),
    )


def _mail_card(mail, on_click=None):
    raw_sender = mail.get("expediteur", "")
    display, email = _parse_sender(raw_sender)
    subject = _clean_text(mail.get("sujet", "")) or "(sans sujet)"
    snippet = _clean_text(mail.get("snippet", ""))
    unread = mail.get("unread", True)

    return T.card(
        on_click=on_click,
        padding=16,
        content=ft.Row(
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                _avatar(display),
                ft.Column(
                    expand=True, spacing=4,
                    controls=[
                        ft.Row(
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Text(display, color=C.text,
                                        size=FONT.body,
                                        weight=ft.FontWeight.W_700,
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                        expand=True),
                                *([ft.Container(
                                    width=8, height=8,
                                    border_radius=999,
                                    bgcolor=C.accent,
                                )] if unread else []),
                            ],
                        ),
                        ft.Text(subject, color=C.text,
                                size=FONT.body,
                                weight=ft.FontWeight.W_500,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(snippet, color=C.text_muted,
                                size=FONT.small,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS),
                    ],
                ),
            ],
        ),
    )


def build(page: ft.Page) -> ft.View:

    loading = ft.ProgressRing(visible=True, width=18, height=18,
                              color=C.accent, stroke_width=2)
    emails_column = ft.Column(spacing=10, expand=True)

    def fetch_mails():
        try:
            emails = get_emails_data(limit=10, unread_only=True)
            emails_column.controls.clear()
            loading.visible = False
            if not emails:
                emails_column.controls.append(
                    ft.Container(
                        padding=24,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=8,
                            controls=[
                                ft.Icon(ft.Icons.INBOX_OUTLINED,
                                        color=C.text_subtle, size=28),
                                ft.Text("Aucun nouvel email.",
                                        color=C.text_subtle,
                                        italic=True, size=FONT.small),
                            ],
                        ),
                    )
                )
            else:
                for m in emails:
                    emails_column.controls.append(_mail_card(m))
            page.update()
        except Exception as e:
            loading.visible = False
            emails_column.controls.append(
                ft.Text(f"Erreur : {e}", color=C.danger, size=FONT.small)
            )
            page.update()

    threading.Thread(target=fetch_mails, daemon=True).start()

    async def open_mailtotal(e):
        await page.push_route("/mailtotal")

    async def push_settings(e):
        await page.push_route("/settings")

    # AppBar Arc
    actions = [
        ft.IconButton(
            icon=ft.Icons.INBOX_ROUNDED,
            icon_color=C.text_muted, icon_size=18,
            tooltip="Tous les mails",
            on_click=open_mailtotal,
        ),
        ft.IconButton(
            icon=ft.Icons.TUNE_ROUNDED,
            icon_color=C.text_muted, icon_size=18,
            tooltip="Paramètres",
            on_click=push_settings,
        ),
        ft.Container(width=8),
    ]

    view = ft.View(
        route="/mails", padding=0, bgcolor=C.bg,
        scroll=ft.ScrollMode.AUTO,
    )
    view.navigation_bar = build_navbar(page, selected=1)
    view.appbar = T.appbar("Messagerie", actions=actions)

    view.controls = [
        ft.Container(
            padding=ft.Padding(left=20, top=8, right=20, bottom=24),
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text("Boîte de réception",
                                    size=FONT.display, color=C.text,
                                    weight=ft.FontWeight.W_700),
                            ft.Text("Non lus", size=FONT.small,
                                    color=C.text_subtle,
                                    weight=ft.FontWeight.W_500),
                        ],
                    ),
                    ft.Row([loading], alignment=ft.MainAxisAlignment.START),
                    emails_column,
                ],
            ),
        ),
    ]

    return view