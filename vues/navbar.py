"""
NavBar — pilule flottante sobre style Arc.
"""

import flet as ft
from vues.theme import C, FONT


def build_navbar(page: ft.Page, selected: int = 0):

    routes = ["/", "/mails", "/rdv", "/AI"]
    icons = [
        ft.Icons.HOME_ROUNDED,
        ft.Icons.MAIL_OUTLINE_ROUNDED,
        ft.Icons.EVENT_AVAILABLE_ROUNDED,
        ft.Icons.AUTO_AWESOME_OUTLINED,
    ]
    labels = ["Accueil", "Mails", "RDV", "Assistant"]

    async def _go(i):
        if routes[i] != page.route:
            await page.push_route(routes[i])

    def nav_item(i):
        active = i == selected
        icon_color = C.accent if active else C.text_subtle
        text_color = C.text if active else C.text_subtle

        return ft.Container(
            padding=ft.Padding(left=14, top=10, right=14, bottom=10),
            border_radius=999,
            bgcolor=(ft.Colors.with_opacity(0.12, C.accent)
                     if active else None),
            ink=True,
            on_click=(lambda e, idx=i: page.run_task(_go, idx)),
            content=ft.Row(
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icons[i], size=20, color=icon_color),
                    *([ft.Text(labels[i], size=FONT.small,
                               color=text_color,
                               weight=ft.FontWeight.W_600)]
                      if active else []),
                ],
            ),
        )

    return ft.Container(
        height=70,
        margin=ft.Margin(left=16, top=0, right=16, bottom=14),
        padding=ft.Padding(left=6, top=6, right=6, bottom=6),
        border_radius=999,
        bgcolor=ft.Colors.with_opacity(0.85, C.bg_elevated),
        border=ft.Border(
            top=ft.BorderSide(1, C.border),
            bottom=ft.BorderSide(1, C.border),
            left=ft.BorderSide(1, C.border),
            right=ft.BorderSide(1, C.border),
        ),
        shadow=ft.BoxShadow(
            blur_radius=30,
            spread_radius=0,
            color=ft.Colors.with_opacity(0.4, "#000000"),
            offset=ft.Offset(0, 10),
        ),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[nav_item(i) for i in range(len(routes))],
        ),
    )