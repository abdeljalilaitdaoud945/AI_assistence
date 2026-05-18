import flet as ft


def build_navbar(page: ft.Page, selected: int = 0):

    routes = ["/", "/mails", "/rdv", "/AI"]

    icons = [
        ft.Icons.HOME_ROUNDED,
        ft.Icons.MAIL_ROUNDED,
        ft.Icons.EVENT_ROUNDED,
        ft.Icons.AUTO_AWESOME_ROUNDED,
    ]

    labels = ["Accueil", "Mails", "RDV", "AI"]

    def go(i):
        page.go(routes[i])

    def nav_item(i):
        active = i == selected

        return ft.GestureDetector(
            on_tap=lambda e: go(i),
            content=ft.Container(
                padding=10,
                border_radius=18,
                bgcolor="#1E293B" if active else None,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=3,
                    controls=[
                        ft.Icon(
                            icons[i],
                            size=26,
                            color="#60A5FA" if active else "#94A3B8",
                        ),
                        ft.Text(
                            labels[i],
                            size=11,
                            color="#E2E8F0" if active else "#64748B",
                        )
                    ],
                ),
            ),
        )

    return ft.Container(
        height=75,
        margin=10,
        padding=10,
        border_radius=25,
        bgcolor="#0F172A",
        shadow=ft.BoxShadow(
            blur_radius=20,
            spread_radius=1,
            color=ft.Colors.with_opacity(0.25, "black"),
            offset=ft.Offset(0, 8),
        ),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[nav_item(i) for i in range(len(routes))],
        ),
    )