import flet as ft
from vues.navbar import build_navbar


def build(page: ft.Page) -> ft.View:

    # ================= ETAT =================
    sidebar_visible = True

    # ================= IA SIDEBAR =================
    ia_content = ft.Column(
        [
            ft.Text("Assistant Mail IA", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),

            ft.Text("Suggestions", weight=ft.FontWeight.W_600),
            ft.Container(
                content=ft.Text(
                    "📬 Répondre au mail 'Client X' recommandé",
                    size=12,
                ),
                padding=10,
                bgcolor=ft.Colors.BLUE_50,
                border_radius=10,
            ),

            ft.Text("Priorités", weight=ft.FontWeight.W_600),
            ft.ListTile(
                leading=ft.Icon(ft.Icons.WARNING, color=ft.Colors.RED),
                title=ft.Text("Relance facture", size=12),
                subtitle=ft.Text("En attente depuis 3 jours", size=10),
            ),

            ft.ElevatedButton(
                "Générer réponse automatique",
                icon=ft.Icons.AUTO_AWESOME,
            ),
        ],
        spacing=15,
        scroll=ft.ScrollMode.AUTO,
    )

    sidebar = ft.Container(
        content=ia_content,
        width=300,
        padding=20,
        bgcolor=ft.Colors.GREY_200,
        visible=sidebar_visible,
        animate=ft.Animation(300, "decelerate"),
    )

    # ================= MAIL CARD =================
    def mail_card(sender, subject, preview, time, color):
        return ft.Card(
            content=ft.Container(
                padding=15,
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.CIRCLE, color=color, size=10),
                                ft.Text(time, size=11),
                            ]
                        ),
                        ft.Text(sender, weight=ft.FontWeight.BOLD),
                        ft.Text(subject, size=13),
                        ft.Text(preview, size=11, color=ft.Colors.GREY_600),
                    ],
                    spacing=5,
                ),
            )
        )

    # ================= DASHBOARD =================
    dashboard = ft.Column(
        [
            ft.Text("Boîte de réception", size=24, weight=ft.FontWeight.BOLD),
            ft.Text("Aujourd’hui", color=ft.Colors.GREY_600),
            ft.Divider(height=15, color=ft.Colors.TRANSPARENT),

            mail_card("Client X", "Proposition commerciale", "Pouvez-vous envoyer...", "09:12", ft.Colors.BLUE),
            mail_card("Admin", "Validation requise", "Merci de valider...", "11:30", ft.Colors.ORANGE),
            mail_card("Support", "Ticket résolu", "Votre problème est...", "14:05", ft.Colors.GREEN),

        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    # ================= INTERACTION =================
    def toggle_sidebar(e):
        nonlocal sidebar_visible
        sidebar_visible = not sidebar_visible
        sidebar.visible = sidebar_visible
        toggle_btn.icon = (
            ft.Icons.CHEVRON_RIGHT if sidebar_visible else ft.Icons.CHEVRON_LEFT
        )
        page.update()

    toggle_btn = ft.IconButton(
        icon=ft.Icons.CHEVRON_RIGHT,
        on_click=toggle_sidebar,
        tooltip="Afficher/Masquer IA",
    )

    def handle_checked_item_click(e):
        e.control.checked = not e.control.checked
        page.update()

    # ================= VIEW =================
    view = ft.View(route="/mails", padding=0)

    route_indexes = {"/": 0, "/mails": 1, "/rdv": 2}
    current_index = route_indexes.get(page.route, 0)

    view.navigation_bar = build_navbar(page, current_index)

    view.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.APARTMENT_SHARP),
        title=ft.Text("MAILS", font_family="PROSTO"),
        bgcolor=ft.Colors.BLUE_300,
        actions=[
            toggle_btn,
            ft.IconButton(ft.Icons.WB_SUNNY_OUTLINED),
            ft.IconButton(ft.Icons.FILTER_3),
            ft.PopupMenuButton(
                items=[
                    ft.PopupMenuItem(content=ft.Text("Item 1")),
                    ft.PopupMenuItem(
                        content=ft.Text("Checked item"),
                        checked=False,
                        on_click=handle_checked_item_click,
                    ),
                ]
            ),
        ],
    )

    view.controls = [
        ft.Row(
            [
                ft.Container(content=dashboard, expand=True, padding=20),
                sidebar,
            ],
            expand=True,
        )
    ]

    return view