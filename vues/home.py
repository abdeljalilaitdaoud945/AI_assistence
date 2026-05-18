import flet as ft
from vues.navbar import build_navbar


def build(page: ft.Page) -> ft.View:

    def handle_checked_item_click(e):
        e.control.checked = not e.control.checked
        page.update()

    async def push_settings(e):
        await page.push_route("/settings")

    view = ft.View(
        route=page.route,
        padding=0,
        scroll=ft.ScrollMode.ALWAYS,
        bgcolor="#0B1220",
    )

    route_indexes = {"/": 0, "/mails": 1, "/rdv": 2}
    current_index = route_indexes.get(page.route, 0)

    view.navigation_bar = build_navbar(page, current_index)

    # ===============================
    # APPBAR (compatible anciennes versions)
    # ===============================
    view.appbar = ft.AppBar(
        bgcolor="#0F172A",
        elevation=0,
        leading=ft.Container(
            margin=10,
            width=46,
            height=46,
            border_radius=16,
            bgcolor="#2563EB",
            alignment=ft.alignment.Alignment(0, 0),
            content=ft.Icon(ft.Icons.AUTO_AWESOME, color="white"),
        ),
        leading_width=60,
        title=ft.Text(
            "APP INPT1",
            size=24,
            weight=ft.FontWeight.BOLD,
            color="white",
        ),
        actions=[
            glass_icon(ft.Icons.SEARCH),
            glass_icon(ft.Icons.NOTIFICATIONS_NONE),

            ft.PopupMenuButton(
                icon=ft.Icons.MENU,
                icon_color="white",
                items=[
                    ft.PopupMenuItem(
                        content=ft.Row([
                            ft.Icon(ft.Icons.SETTINGS),
                            ft.Text("Paramètres")
                        ]),
                        on_click=push_settings
                    ),
                    ft.PopupMenuItem(
                        content=ft.Text("Profil")
                    ),
                    ft.PopupMenuItem(
                        content=ft.Text("Checked item"),
                        checked=False,
                        on_click=handle_checked_item_click
                    )
                ]
            )
        ]
    )

    view.controls = [

        # ===============================
        # HERO
        # ===============================
        ft.Container(
            margin=20,
            padding=30,
            border_radius=30,
            bgcolor="#1E3A8A",
            shadow=ft.BoxShadow(
                blur_radius=25,
                spread_radius=1,
                color=ft.Colors.with_opacity(0.25, "black"),
                offset=ft.Offset(0, 12),
            ),
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Text(
                        "Dashboard Nouvelle Génération 🚀",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color="white",
                    ),
                    ft.Text(
                        "Gestion rapide, moderne et intelligente.",
                        size=15,
                        color="#DBEAFE"
                    ),
                    ft.Row(
                        controls=[
                            neon_button("Explorer"),
                            outline_button("Statistiques")
                        ]
                    )
                ]
            )
        ),

        section_title("Accès rapide"),

        # ===============================
        # GRID MENU
        # ===============================
        ft.Container(
            padding=20,
            height=320,
            content=ft.GridView(
                runs_count=2,
                max_extent=180,
                spacing=16,
                run_spacing=16,
                child_aspect_ratio=1.0,
                controls=[
                    premium_card("Messages", ft.Icons.MAIL, "#2563EB"),
                    premium_card("Rendez-vous", ft.Icons.EVENT, "#10B981"),
                    premium_card("Documents", ft.Icons.FOLDER, "#F59E0B"),
                    premium_card("Étudiants", ft.Icons.GROUP, "#EC4899"),
                ]
            )
        ),

        section_title("Analytics"),

        ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=14,
            controls=[
                stats_box("124", "Mails"),
                stats_box("89", "RDV"),
                stats_box("98%", "Done"),
            ]
        ),

        ft.Container(height=30),
    ]

    return view


# ==================================
# COMPONENTS
# ==================================

def glass_icon(icon):
    return ft.Container(
        margin=8,
        padding=10,
        border_radius=14,
        bgcolor="#1E293B",
        content=ft.Icon(icon, color="white"),
    )


def section_title(text):
    return ft.Container(
        padding=20,
        content=ft.Text(
            text,
            size=22,
            weight=ft.FontWeight.BOLD,
            color="white"
        )
    )


def premium_card(title, icon, color):
    return ft.Container(
        border_radius=24,
        padding=22,
        bgcolor="#111827",
        shadow=ft.BoxShadow(
            blur_radius=18,
            spread_radius=1,
            color=ft.Colors.with_opacity(0.15, "black"),
            offset=ft.Offset(0, 8),
        ),
        content=ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=14,
            controls=[
                ft.Container(
                    width=58,
                    height=58,
                    border_radius=18,
                    bgcolor=color,
                    alignment=ft.alignment.Alignment(0, 0),
                    content=ft.Icon(icon, color="white", size=28),
                ),
                ft.Text(
                    title,
                    size=16,
                    color="white",
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER,
                )
            ]
        )
    )


def stats_box(value, label):
    return ft.Container(
        width=110,
        padding=18,
        border_radius=20,
        bgcolor="#111827",
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(
                    value,
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color="#38BDF8"
                ),
                ft.Text(
                    label,
                    size=13,
                    color="#94A3B8"
                )
            ]
        )
    )


def neon_button(text):
    return ft.ElevatedButton(
        text,
        style=ft.ButtonStyle(
            bgcolor="white",
            color="#111827",
            padding=20,
            shape=ft.RoundedRectangleBorder(radius=16),
        )
    )


def outline_button(text):
    return ft.OutlinedButton(
        text,
        style=ft.ButtonStyle(
            color="white",
            side=ft.BorderSide(1, "white"),
            padding=20,
            shape=ft.RoundedRectangleBorder(radius=16),
        )
    )