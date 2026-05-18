import flet as ft
from vues.navbar import build_navbar
from services.calendar_service import get_today_events
def build(page: ft.Page) -> ft.View:
    
    # --- 1. ÉTAT DE L'INTERFACE ---
    sidebar_visible = True

    # --- 2. COMPOSANTS DU PANNEAU IA (DISCRET) ---
    ia_content = ft.Column([
        ft.Text("Copilote IA", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800),
        ft.Divider(),
        ft.Text("Points Critiques", weight=ft.FontWeight.W_600),
        ft.Container(
            content=ft.Text("📉 Baisse de marge détectée sur la zone Nord. À challenger.", size=12),
            padding=10, bgcolor=ft.Colors.ORANGE_50, border_radius=10
        ),
        ft.Text("Actions en retard", weight=ft.FontWeight.W_600),
        ft.ListTile(
            leading=ft.Icon(ft.Icons.WARNING, color=ft.Colors.RED),
            title=ft.Text("Devis Client X", size=12),
            subtitle=ft.Text("Échéance dépassée de 2j", size=10),
        ),
        ft.ElevatedButton(
            "Générer PV Automatique", 
            icon=ft.Icons.AUTO_AWESOME,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
        )
    ], spacing=15, scroll=ft.ScrollMode.AUTO)

    sidebar = ft.Container(
        content=ia_content,
        width=300,
        padding=20,
        bgcolor=ft.Colors.GREY_200, 
        visible=sidebar_visible,
        animate=ft.Animation(400, "decelerate"),
    )

    # --- 3. BOUTON VERS LE CALENDRIER COMPLET ---
    btn_open_calendar = ft.Container(
        content=ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.CALENDAR_MONTH, color=ft.Colors.WHITE),
                ft.Text("OUVRIR MON AGENDA COMPLET", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=ft.Colors.BLUE_700,
            height=60,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
            on_click=lambda _: page.go("/calendrier") # Assure-toi que c'est bien "/calendar" et non "/calendrier" selon ton main.py
        ),
        margin=ft.margin.only(bottom=20)
    )

    # --- 4. COMPOSANTS DU TABLEAU DE BORD (PRINCIPAL) ---
    def create_event(title, time, type_meet, color):
        return ft.Card(
            content=ft.Container(
                padding=15,
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.CIRCLE, color=color, size=12),
                        ft.Text(time, size=12, weight=ft.FontWeight.W_500),
                    ]),
                    ft.Text(title, weight=ft.FontWeight.BOLD, size=16),
                    ft.Text(f"Type: {type_meet}", size=12, color=ft.Colors.GREY_700),
                ], spacing=5)
            )
        )

    dashboard_column = ft.Column([
        btn_open_calendar,
        ft.Text("Aperçu de la journée", size=24, weight=ft.FontWeight.BOLD),
        ft.Text("Jeudi 23 Avril", color=ft.Colors.GREY_600),
        ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
        create_event("Réunion Commerciale", "09:00 - 10:30", "Ventes", ft.Colors.BLUE),
        create_event("Point Stratégique", "14:00 - 15:00", "Groupe", ft.Colors.RED),     
        create_event("Comptabilité", "16:30 - 17:30", "Finance", ft.Colors.GREEN),     
    ], expand=True, scroll=ft.ScrollMode.AUTO)

    # --- 5. LOGIQUE D'INTERACTION ---
    def toggle_sidebar(e):
        nonlocal sidebar_visible
        sidebar_visible = not sidebar_visible
        sidebar.visible = sidebar_visible
        toggle_btn.icon = ft.Icons.CHEVRON_RIGHT if sidebar_visible else ft.Icons.CHEVRON_LEFT
        page.update()

    toggle_btn = ft.IconButton(
        icon=ft.Icons.CHEVRON_RIGHT,
        on_click=toggle_sidebar,
        tooltip="Afficher/Masquer l'Assistant IA"
    )

    # Menus de la AppBar
    def handle_checked_item_click(e):
        e.control.checked = not e.control.checked
        page.update()

    async def push_settings(e):
        await page.push_route("/settings")

    # --- 6. ASSEMBLAGE FINAL DE LA VUE ---
    
    # On crée la vue avec un padding 0 pour que le panneau IA touche le bord droit
    view = ft.View(route="/rdv", padding=0)

    # Ajout de la barre de navigation en bas (Index 2 correspond à Rendez-vous)
    view.navigation_bar = build_navbar(page, selected=2)

    # Ajout de la barre du haut fusionnée (Titre RDV + Bouton IA + Menu Paramètres)
    view.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.APARTMENT_SHARP),
        leading_width=40,
        title=ft.Text("Chef d'Orchestre", font_family="PROSTO"),
        center_title=False,
        bgcolor=ft.Colors.BLUE_300,
        actions=[
            toggle_btn, # <-- Le bouton pour afficher l'IA est bien là !
            ft.IconButton(ft.Icons.WB_SUNNY_OUTLINED),
            ft.IconButton(ft.Icons.FILTER_3),
            ft.PopupMenuButton(
                items=[
                    ft.PopupMenuItem(
                        content=ft.Row([
                            ft.Icon(ft.Icons.SETTINGS),
                            ft.Text("Paramètres"),
                        ]),
                        on_click=push_settings,
                    ),
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

    # Ajout du contenu central (Le Dashboard à gauche, l'IA à droite)
    view.controls = [
        ft.Row([
            # Zone Gauche : Tableau de bord et bouton
            ft.Container(content=dashboard_column, expand=True, padding=20),
            # Zone Droite : Sidebar IA
            sidebar,
        ], expand=True, spacing=0)
    ]

    return view