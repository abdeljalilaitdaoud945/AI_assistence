import flet as ft
import threading
from datetime import datetime
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
        # Utilisation de l'énumération officielle pour l'animation
        animate=ft.Animation(400, ft.AnimationCurve.DECELERATE),
    )

    # --- 3. BOUTON VERS LE CALENDRIER COMPLET ---
    async def open_calendar(e):
        await page.push_route("/calendrier")

    btn_open_calendar = ft.Container(
        content=ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.CALENDAR_MONTH, color=ft.Colors.WHITE),
                ft.Text("OUVRIR MON AGENDA COMPLET", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=ft.Colors.BLUE_700,
            height=60,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
            on_click=open_calendar 
        ),
        # ft.Margin strict avec majuscule
        margin=ft.Margin(left=0, top=0, right=0, bottom=20)
    )

    # --- 4. TABLEAU DE BORD (SYNCHRONISATION GOOGLE EN TEMPS RÉEL) ---
    dashboard_column = ft.Column([], expand=True, scroll=ft.ScrollMode.AUTO)
    loading = ft.ProgressRing(visible=False, width=20, height=20, color=ft.Colors.BLUE_700)

    def load_real_events():
        loading.visible = True
        page.update()

        def fetch():
            dashboard_column.controls.clear()
            dashboard_column.controls.append(btn_open_calendar)
            
            today_str = datetime.now().strftime("%A %d %B").capitalize()
            dashboard_column.controls.append(
                ft.Row([
                    ft.Column([
                        ft.Text("Aperçu de la journée", size=24, weight=ft.FontWeight.BOLD),
                        ft.Text(today_str, color=ft.Colors.GREY_600),
                    ], spacing=0),
                    loading
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            )
            dashboard_column.controls.append(ft.Divider(height=20, color=ft.Colors.TRANSPARENT))

            try:
                events = get_today_events()
                now = datetime.now().astimezone() 
                
                if not events:
                    dashboard_column.controls.append(
                        ft.Text("Aucun événement prévu aujourd'hui.", italic=True, color=ft.Colors.GREY_500)
                    )
                else:
                    colors = [ft.Colors.BLUE, ft.Colors.RED, ft.Colors.GREEN, ft.Colors.ORANGE, ft.Colors.PURPLE]
                    upcoming_count = 0
                    
                    for i, e in enumerate(events):
                        raw_start = e["start"].get("dateTime", e["start"].get("date", ""))
                        raw_end = e["end"].get("dateTime", e["end"].get("date", ""))
                        
                        try:
                            dt_start = datetime.fromisoformat(raw_start.replace("Z", "+00:00")).astimezone()
                            dt_end = datetime.fromisoformat(raw_end.replace("Z", "+00:00")).astimezone()
                            
                            if dt_end < now:
                                continue
                                
                            time_str = f"{dt_start.strftime('%H:%M')} - {dt_end.strftime('%H:%M')}"
                        except Exception:
                            time_str = "Toute la journée"
                            
                        upcoming_count += 1
                        summary = e.get("summary", "Sans titre")
                        color = colors[i % len(colors)]
                        
                        dashboard_column.controls.append(
                            ft.Card(
                                content=ft.Container(
                                    padding=15,
                                    content=ft.Column([
                                        ft.Row([
                                            ft.Icon(ft.Icons.CIRCLE, color=color, size=12),
                                            ft.Text(time_str, size=12, weight=ft.FontWeight.W_500),
                                        ]),
                                        ft.Text(summary, weight=ft.FontWeight.BOLD, size=16),
                                        ft.Text("Type: Google Calendar", size=12, color=ft.Colors.GREY_700),
                                    ], spacing=5)
                                )
                            )
                        )
                        
                    if upcoming_count == 0:
                        dashboard_column.controls.append(
                            ft.Container(
                                padding=20,
                                alignment=ft.Alignment(0, 0),
                                content=ft.Text("🎉 Journée terminée ! Plus aucun rendez-vous à venir.", 
                                                color=ft.Colors.GREEN_700, weight=ft.FontWeight.BOLD)
                            )
                        )

            except Exception as ex:
                dashboard_column.controls.append(
                    ft.Text(f"Erreur de synchronisation Google : {ex}", color=ft.Colors.RED)
                )
            
            loading.visible = False
            page.update()

        threading.Thread(target=fetch).start()

    load_real_events()

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

    def handle_checked_item_click(e):
        e.control.checked = not e.control.checked
        page.update()

    async def push_settings(e):
        await page.push_route("/settings")

    # --- 6. ASSEMBLAGE FINAL DE LA VUE ---
    view = ft.View(route="/rdv", padding=0)

    route_indexes = {"/": 0, "/mails": 1, "/rdv": 2}
    current_index = route_indexes.get(page.route, 2)
    view.navigation_bar = build_navbar(page, current_index)

    view.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.APARTMENT_SHARP),
        leading_width=40,
        title=ft.Text("Chef d'Orchestre", font_family="PROSTO"),
        center_title=False,
        bgcolor=ft.Colors.BLUE_300,
        actions=[
            toggle_btn, 
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

    view.controls = [
        ft.Row([
            ft.Container(content=dashboard_column, expand=True, padding=20),
            sidebar,
        ], expand=True, spacing=0)
    ]

    return view