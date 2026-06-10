"""
NavBar — pilule flottante sobre style Arc.
Labels toujours visibles, item actif beaucoup plus contrasté.
"""

import flet as ft
from vues.theme import C, FONT


# Mapping route -> index (utilisé par les vues pour calculer selected)
ROUTE_TO_NAV = {
    "/":          0,
    "/mails":     1,
    "/rdv":       2,
    "/AI":        3,
    # Pages secondaires : héritent du parent
    "/settings":   0,
    "/bourse":     0,
    "/pdf":        0,
    "/mailtotal":  1,
    "/calendrier": 2,
}


def nav_index_for(route: str) -> int:
    """Détermine l'index de l'onglet sélectionné à partir de la route."""
    return ROUTE_TO_NAV.get(route, 0)


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
        target = routes[i]
        if target != page.route:
            await page.push_route(target)

    def nav_item(i):
        active = i == selected

        if active:
            # Item actif : bg violet saturé, icône + label en blanc
            bg = C.accent_strong
            icon_color = "#FFFFFF"
            text_color = "#FFFFFF"
        else:
            bg = None
            icon_color = C.text_subtle
            text_color = C.text_subtle

        return ft.Container(
            padding=ft.Padding(left=14, top=8, right=14, bottom=8),
            border_radius=999,
            bgcolor=bg,
            ink=True,
            on_click=(lambda e, idx=i: page.run_task(_go, idx)),
            content=ft.Column(
                spacing=2,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icons[i], size=20, color=icon_color),
                    ft.Text(labels[i], size=FONT.micro,
                            color=text_color,
                            weight=ft.FontWeight.W_700 if active else ft.FontWeight.W_500),
                ],
            ),
        )

    return ft.Container(
        height=78,
        margin=ft.Margin(left=16, top=0, right=16, bottom=14),
        padding=ft.Padding(left=8, top=6, right=8, bottom=6),
        border_radius=999,
        bgcolor=ft.Colors.with_opacity(0.92, C.bg_elevated),
        border=ft.Border(
            top=ft.BorderSide(1, C.border),
            bottom=ft.BorderSide(1, C.border),
            left=ft.BorderSide(1, C.border),
            right=ft.BorderSide(1, C.border),
        ),
        shadow=ft.BoxShadow(
            blur_radius=30, spread_radius=0,
            color=ft.Colors.with_opacity(0.5, "#000000"),
            offset=ft.Offset(0, 12),
        ),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[nav_item(i) for i in range(len(routes))],
        ),
    )