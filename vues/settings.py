"""
Vue Settings — préférences et compte, refondu Arc-style.
"""

import os

import flet as ft

from vues import theme as T
from vues.theme import C, FONT
from vues.navbar import build_navbar, nav_index_for


def build(page: ft.Page) -> ft.View:

    prefs = ft.SharedPreferences()

    # ---- Récup des infos utilisateur ----
    prenom = ""
    nom = ""
    email = ""
    photo = ""
    if page.data and isinstance(page.data, dict):
        prenom = page.data.get("prenom", "")
        nom = page.data.get("nom", "")
        email = page.data.get("email", "")
        photo = page.data.get("photo", "")

    # ---- Profile card ----
    initial = (prenom[:1] + nom[:1]).upper() if prenom or nom else "?"
    avatar = ft.Container(
        width=56, height=56,
        border_radius=999,
        bgcolor=ft.Colors.with_opacity(0.22, C.accent),
        alignment=ft.Alignment.CENTER,
        content=ft.Text(initial, color=C.accent,
                        size=FONT.h2, weight=ft.FontWeight.W_700),
    )

    profile_card = T.card(
        accent=True,
        padding=18,
        content=ft.Row(
            spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                avatar,
                ft.Column(
                    spacing=2, expand=True,
                    controls=[
                        ft.Text(
                            f"{prenom} {nom}".strip() or "Non connecté",
                            color=C.text, size=FONT.h3,
                            weight=ft.FontWeight.W_700,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Text(
                            email or "Aucun compte",
                            color=C.text_subtle, size=FONT.small,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                ),
            ],
        ),
    )

    # ---- Switches préférences ----
    theme_switch = ft.Switch(
        value=page.theme_mode == ft.ThemeMode.DARK,
        active_color=C.accent,
    )
    notif_switch = ft.Switch(
        value=False,
        active_color=C.accent,
    )

    async def load_data():
        try:
            saved = await prefs.get("notifications_enabled")
            notif_switch.value = saved if saved is not None else False
            page.update()
        except Exception as e:
            print(f"[settings] load error: {e}")

    page.run_task(load_data)

    async def toggle_theme(e):
        is_dark = e.control.value
        page.theme_mode = ft.ThemeMode.DARK if is_dark else ft.ThemeMode.LIGHT
        try:
            await prefs.set("theme_mode", "dark" if is_dark else "light")
        except Exception:
            pass
        page.update()

    async def save_notifications(e):
        try:
            await prefs.set("notifications_enabled", e.control.value)
        except Exception:
            pass
        page.show_dialog(ft.SnackBar(ft.Text("Préférence sauvegardée"),
                                     duration=1500))

    theme_switch.on_change = toggle_theme
    notif_switch.on_change = save_notifications

    def pref_row(icon, title, subtitle, trailing):
        return ft.Container(
            padding=ft.Padding(left=4, top=10, right=4, bottom=10),
            content=ft.Row(
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=36, height=36,
                        border_radius=12,
                        bgcolor=ft.Colors.with_opacity(0.14, C.accent),
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(icon, color=C.accent, size=18),
                    ),
                    ft.Column(
                        spacing=2, expand=True,
                        controls=[
                            ft.Text(title, color=C.text, size=FONT.body,
                                    weight=ft.FontWeight.W_600),
                            ft.Text(subtitle, color=C.text_subtle,
                                    size=FONT.micro),
                        ],
                    ),
                    trailing,
                ],
            ),
        )

    preferences_card = T.card(
        padding=18,
        content=ft.Column(
            spacing=0,
            controls=[
                ft.Text("Préférences", color=C.text_muted,
                        size=FONT.small, weight=ft.FontWeight.W_600),
                pref_row(
                    ft.Icons.DARK_MODE_OUTLINED,
                    "Mode sombre", "Apparence visuelle",
                    theme_switch,
                ),
                T.divider(),
                pref_row(
                    ft.Icons.NOTIFICATIONS_NONE_ROUNDED,
                    "Notifications", "Alertes in-app",
                    notif_switch,
                ),
            ],
        ),
    )

    # ---- Logout ----
    def on_logout(e):
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        token_path = os.path.join(BASE_DIR, "token.json")
        if os.path.exists(token_path):
            try:
                os.remove(token_path)
            except Exception:
                pass

        page.data = None
        try:
            page.controls.clear()
        except Exception:
            pass
        page.views.clear()
        page.views.append(
            ft.View(
                route="/login",
                bgcolor=C.bg,
                controls=[
                    ft.Container(
                        expand=True,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=14,
                            controls=[
                                ft.Container(
                                    width=64, height=64,
                                    border_radius=999,
                                    bgcolor=ft.Colors.with_opacity(0.18, C.accent),
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Icon(ft.Icons.LOCK_OUTLINE,
                                                    size=28, color=C.accent),
                                ),
                                ft.Text("Déconnecté", size=FONT.h2,
                                        color=C.text,
                                        weight=ft.FontWeight.W_700),
                                ft.Text("Relance l'app pour te reconnecter.",
                                        size=FONT.small, color=C.text_subtle),
                            ],
                        ),
                    )
                ],
            )
        )
        page.update()

    logout_card = T.card(
        padding=18,
        content=ft.Column(
            spacing=14,
            controls=[
                ft.Text("Compte", color=C.text_muted,
                        size=FONT.small, weight=ft.FontWeight.W_600),
                ft.Container(
                    bgcolor=ft.Colors.with_opacity(0.14, C.danger),
                    border_radius=999,
                    padding=ft.Padding(left=18, top=11, right=18, bottom=11),
                    ink=True,
                    on_click=on_logout,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.LOGOUT_ROUNDED,
                                    color=C.danger, size=16),
                            ft.Text("Se déconnecter", color=C.danger,
                                    weight=ft.FontWeight.W_700,
                                    size=FONT.body),
                        ],
                    ),
                ),
            ],
        ),
    )

    view = ft.View(
        route="/settings", padding=0, bgcolor=C.bg,
        scroll=ft.ScrollMode.AUTO,
    )
    view.navigation_bar = build_navbar(
        page, selected=nav_index_for("/settings"))
    view.appbar = T.appbar("Paramètres", back_route="/", page=page)

    view.controls = [
        ft.Container(
            padding=ft.Padding(left=20, top=8, right=20, bottom=24),
            content=ft.Column(
                spacing=14,
                controls=[
                    profile_card,
                    preferences_card,
                    logout_card,
                    ft.Container(
                        margin=ft.Margin(left=0, top=30, right=0, bottom=0),
                        alignment=ft.Alignment.CENTER,
                        content=ft.Text("INPT APP — v1.0",
                                        size=FONT.micro,
                                        color=C.text_subtle),
                    ),
                ],
            ),
        ),
    ]

    return view