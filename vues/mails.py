import flet as ft
import threading
from vues.navbar import build_navbar
from services.email_service import get_emails_data

def build(page: ft.Page) -> ft.View:
    
    # --- COMPOSANTS PRINCIPAUX ---
    loading = ft.ProgressRing(visible=True, width=30, height=30, color="#38BDF8", stroke_width=3)
    emails_column = ft.Column(spacing=12, expand=True, scroll=ft.ScrollMode.AUTO)

    # --- LOGIQUE DE RÉCUPÉRATION ---
    def fetch_mails():
        try:
            emails = get_emails_data(limit=5, unread_only=True)
            emails_column.controls.clear()
            loading.visible = False
            if not emails:
                emails_column.controls.append(
                    ft.Container(
                        padding=20,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Text("Aucun nouvel email. 🎉", color=ft.Colors.GREY_500, italic=True)
                    )
                )
            else:
                for mail in emails:
                    emails_column.controls.append(
                        ft.Container(
                            padding=15,
                            border_radius=12,
                            bgcolor="#1E293B",
                            border=ft.border.only(left=ft.BorderSide(4, "#38BDF8")),
                            shadow=ft.BoxShadow(blur_radius=5, color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK)),
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon(ft.Icons.MARK_EMAIL_UNREAD, color="#38BDF8", size=16),
                                    ft.Text(mail["expediteur"], weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=14),
                                ]),
                                ft.Text(mail["sujet"], weight=ft.FontWeight.W_600, color=ft.Colors.WHITE, size=14),
                                ft.Text(mail["snippet"], color=ft.Colors.GREY_400, size=12, max_lines=2),
                            ], spacing=5)
                        )
                    )
            page.update()
        except Exception as e:
            loading.visible = False
            emails_column.controls.append(ft.Text(f"Erreur : {e}", color=ft.Colors.RED))
            page.update()

    threading.Thread(target=fetch_mails).start()

    # --- ACTIONS ---
    async def open_mailtotal(e):
        await page.push_route("/mailtotal")

    async def push_settings(e):
        await page.push_route("/settings")

    # --- VUE ---
    view = ft.View(route="/mails", padding=20, bgcolor="#0B1220")
    view.navigation_bar = build_navbar(page, selected=1)

    view.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.APARTMENT_SHARP),
        title=ft.Text("Messagerie", font_family="PROSTO"),
        bgcolor=ft.Colors.BLUE_300,
        actions=[
            ft.PopupMenuButton(
                items=[
                    ft.PopupMenuItem(
                        content=ft.Row([ft.Icon(ft.Icons.SETTINGS), ft.Text("Paramètres")]),
                        on_click=push_settings,
                    ),
                ]
            ),
        ],
    )

    view.controls = [
        ft.Container(
            margin=ft.Margin(0, 0, 0, 20),
            content=ft.ElevatedButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.ALL_INBOX, color=ft.Colors.WHITE),
                    ft.Text("OUVRIR TOUS MES MAILS", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ], alignment=ft.MainAxisAlignment.CENTER),
                bgcolor="#2563EB",
                height=55,
                on_click=open_mailtotal
            )
        ),
        ft.Row([
            ft.Text("Derniers Non Lus", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            loading
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        emails_column
    ]
    return view