import flet as ft
import threading
from services.email_service import get_emails_data

def build(page: ft.Page) -> ft.View:

    loading = ft.ProgressRing(visible=True, width=30, height=30, color="#38BDF8", stroke_width=3)
    all_emails_column = ft.Column(spacing=10, expand=True, scroll=ft.ScrollMode.AUTO)

    def fetch_all_mails():
        try:
            emails = get_emails_data(limit=30, unread_only=False)
            all_emails_column.controls.clear()
            loading.visible = False
            if not emails:
                all_emails_column.controls.append(ft.Text("Boîte vide.", color=ft.Colors.WHITE))
            else:
                for mail in emails:
                    all_emails_column.controls.append(
                        ft.Container(
                            padding=15,
                            border_radius=10,
                            bgcolor="#111827",
                            border=ft.border.all(1, "#1E293B"),
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon(ft.Icons.PERSON, color="#94A3B8", size=16),
                                    ft.Text(mail["expediteur"], weight=ft.FontWeight.BOLD, color="#38BDF8", size=14),
                                ]),
                                ft.Text(mail["sujet"], weight=ft.FontWeight.W_600, color=ft.Colors.WHITE, size=15),
                                ft.Text(mail["snippet"], color=ft.Colors.GREY_500, size=12, max_lines=2),
                            ], spacing=4)
                        )
                    )
            page.update()
        except Exception as e:
            loading.visible = False
            all_emails_column.controls.append(ft.Text(f"Erreur : {e}", color=ft.Colors.RED))
            page.update()

    threading.Thread(target=fetch_all_mails).start()

    async def go_back(e):
        await page.push_route("/mails")

    header = ft.Container(
        padding=15,
        border_radius=15,
        bgcolor="#111827",
        shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK)),
        content=ft.Row([
            ft.IconButton(icon=ft.Icons.ARROW_BACK_ROUNDED, icon_color=ft.Colors.WHITE, on_click=go_back),
            ft.Text("Historique Complet", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            loading
        ], spacing=10),
    )

    return ft.View(
        route="/mailtotal",
        padding=15,
        bgcolor="#0B1220", 
        controls=[
            ft.Column([
                header, 
                ft.Container(
                    expand=True,
                    border_radius=20,
                    bgcolor="#0F172A",
                    padding=15,
                    content=all_emails_column
                )
            ], expand=True, spacing=15)
        ],
    )