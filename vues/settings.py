import flet as ft
import os

def build(page: ft.Page) -> ft.View:
    
    prefs = ft.SharedPreferences()

    # Récupérer infos Google
    prenom = ""
    nom = ""
    email = ""
    photo = ""
    if page.data and isinstance(page.data, dict):
        prenom = page.data.get("prenom", "")
        nom = page.data.get("nom", "")
        email = page.data.get("email", "")
        photo = page.data.get("photo", "")

    # --- NOTIFICATIONS ---
    notif_switch = ft.Switch(value=False)
    notif_tile = ft.ListTile(
        leading=ft.Icon(ft.Icons.NOTIFICATIONS_OFF),
        title=ft.Text("Notifications"), 
        subtitle=ft.Text("Alertes in-app"),
        trailing=notif_switch,
    )
    
    # --- THÈME ---
    theme_switch = ft.Switch(value=page.theme_mode == ft.ThemeMode.DARK)
    theme_tile = ft.ListTile(
        leading=ft.Icon(ft.Icons.DARK_MODE if theme_switch.value else ft.Icons.LIGHT_MODE),
        title=ft.Text("Mode Sombre"), 
        subtitle=ft.Text("Apparence visuelle"),
        trailing=theme_switch,
    )

    async def load_data():
        saved_notifs = await prefs.get("notifications_enabled")
        notifs_on = saved_notifs if saved_notifs is not None else False
        notif_switch.value = notifs_on
        notif_tile.leading.name = ft.Icons.NOTIFICATIONS_ACTIVE if notifs_on else ft.Icons.NOTIFICATIONS_OFF
        page.update()
        
    page.run_task(load_data)

    async def toggle_theme(e):
        is_dark = e.control.value
        page.theme_mode = ft.ThemeMode.DARK if is_dark else ft.ThemeMode.LIGHT
        await prefs.set("theme_mode", "dark" if is_dark else "light")
        theme_tile.leading.name = ft.Icons.DARK_MODE if is_dark else ft.Icons.LIGHT_MODE
        page.update()

    async def save_notifications(e):
        notifs_on = e.control.value
        await prefs.set("notifications_enabled", notifs_on)
        notif_tile.leading.name = ft.Icons.NOTIFICATIONS_ACTIVE if notifs_on else ft.Icons.NOTIFICATIONS_OFF
        page.snack_bar = ft.SnackBar(ft.Text("Préférence sauvegardée !"), duration=2000)
        page.snack_bar.open = True
        page.update()

    theme_switch.on_change = toggle_theme
    notif_switch.on_change = save_notifications

    # --- PROFIL GOOGLE ---
    avatar = ft.CircleAvatar(
        foreground_image_src=photo,
        content=ft.Text(prenom[0].upper() if prenom else "?", size=24),
        radius=35,
        bgcolor=ft.Colors.BLUE_700,
    )

    profile_card = ft.Card(
        elevation=2, 
        margin=ft.margin.only(bottom=20),
        content=ft.Container(
            padding=20,
            content=ft.Row([
                avatar,
                ft.Column([
                    ft.Text(
                        f"{prenom} {nom}" if prenom else "Non connecté",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Text(
                        email if email else "Aucun compte",
                        size=13,
                        color=ft.Colors.GREY_500,
                    ),
                ], spacing=4),
            ], spacing=15)
        )
    )

    # --- PRÉFÉRENCES ---
    preferences_card = ft.Card(
        elevation=2,
        content=ft.Container(
            padding=ft.padding.symmetric(vertical=10),
            content=ft.Column([
                ft.Container(
                    padding=ft.padding.only(left=15, bottom=5, top=5), 
                    content=ft.Row([
                        ft.Icon(ft.Icons.TUNE, color=ft.Colors.ORANGE),
                        ft.Text("Préférences", size=18, weight=ft.FontWeight.BOLD)
                    ])
                ),
                ft.Divider(height=1),
                notif_tile,
                theme_tile,
            ], spacing=0)
        )
    )

    # --- DÉCONNEXION ---
    def on_logout(e):
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        token_path = os.path.join(BASE_DIR, "token.json")
        if os.path.exists(token_path):
            os.remove(token_path)
        
        page.data = None
        page.controls.clear()
        page.views.clear()
        page.views.append(
            ft.View(
                route="/login",
                bgcolor="#0F172A",
                controls=[
                    ft.Container(
                        expand=True,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Column([
                            ft.Icon(ft.Icons.LOCK_OUTLINE, size=60, color="white"),
                            ft.Text("Déconnecté", size=24, weight=ft.FontWeight.BOLD, color="white"),
                            ft.Text("Relancez l'application pour vous reconnecter.", size=14, color="#94A3B8"),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                    )
                ]
            )
        )
        page.update()
    logout_card = ft.Card(
        elevation=2,
        margin=ft.margin.only(top=20),
        content=ft.Container(
            padding=15,
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.LOGOUT, color=ft.Colors.RED),
                    ft.Text("Compte", size=18, weight=ft.FontWeight.BOLD)
                ]),
                ft.ElevatedButton(
                    "Se déconnecter",
                    icon=ft.Icons.LOGOUT,
                    color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.RED_700,
                    on_click=on_logout,
                ),
            ], spacing=10)
        )
    )
    # --- VUE FINALE ---
    return ft.View(
        route="/settings", 
        padding=20,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.AppBar(
                title=ft.Text("Paramètres", font_family="PROSTO"), 
                bgcolor=ft.Colors.BLUE_300, 
                center_title=True
            ),
            profile_card,
            preferences_card,
            logout_card,
            ft.Container(
                margin=ft.margin.only(top=40), 
                alignment=ft.Alignment(0, 0),
                content=ft.Text("INPT APP version 1.0", size=12, color=ft.Colors.GREY_500)
            )
        ]
    )