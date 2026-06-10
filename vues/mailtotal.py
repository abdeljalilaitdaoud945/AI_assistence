"""
Vue Mailtotal — historique complet, cards cliquables.
"""

import threading
import re

import flet as ft

from vues import theme as T
from vues.theme import C, FONT
from vues.navbar import build_navbar, nav_index_for
from vues.mails import _mail_card, open_mail_detail, _clean_text
from services.email_service import get_emails_data


def build(page: ft.Page) -> ft.View:

    loading = ft.ProgressRing(visible=True, width=18, height=18,
                              color=C.accent, stroke_width=2)
    emails_col = ft.Column(spacing=10, expand=True)

    def fetch_all_mails():
        try:
            emails = get_emails_data(limit=30, unread_only=False)
            emails_col.controls.clear()
            loading.visible = False
            if not emails:
                emails_col.controls.append(
                    ft.Container(
                        padding=24, alignment=ft.Alignment.CENTER,
                        content=ft.Text("Boîte de réception vide.",
                                        color=C.text_subtle, italic=True,
                                        size=FONT.small),
                    )
                )
            else:
                for m in emails:
                    mid = m.get("id")
                    subj = _clean_text(m.get("sujet", ""))
                    sender = m.get("expediteur", "")
                    emails_col.controls.append(
                        _mail_card(
                            m,
                            on_click=lambda e, _mid=mid, _s=subj, _sd=sender:
                                open_mail_detail(page, _mid, _s, _sd),
                        )
                    )
            page.update()
        except Exception as e:
            loading.visible = False
            emails_col.controls.clear()
            emails_col.controls.append(
                ft.Text(f"Erreur Gmail : {e}", color=C.danger,
                        size=FONT.small)
            )
            page.update()

    threading.Thread(target=fetch_all_mails, daemon=True).start()

    def do_refresh(e):
        loading.visible = True
        page.update()
        threading.Thread(target=fetch_all_mails, daemon=True).start()

    actions = [
        ft.IconButton(
            icon=ft.Icons.REFRESH_ROUNDED,
            icon_color=C.text_muted, icon_size=18,
            tooltip="Rafraîchir",
            on_click=do_refresh,
        ),
        ft.Container(width=8),
    ]

    view = ft.View(
        route="/mailtotal", padding=0, bgcolor=C.bg,
        scroll=ft.ScrollMode.AUTO,
    )
    view.navigation_bar = build_navbar(
        page, selected=nav_index_for("/mailtotal"))
    view.appbar = T.appbar("Tous les mails", back_route="/mails",
                           page=page, actions=actions)

    view.controls = [
        ft.Container(
            padding=ft.Padding(left=20, top=8, right=20, bottom=24),
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text("Historique", size=FONT.display,
                                    color=C.text,
                                    weight=ft.FontWeight.W_700),
                            ft.Text("Tous tes mails récents", size=FONT.small,
                                    color=C.text_subtle,
                                    weight=ft.FontWeight.W_500),
                        ],
                    ),
                    ft.Row([loading], alignment=ft.MainAxisAlignment.START),
                    emails_col,
                ],
            ),
        ),
    ]

    return view