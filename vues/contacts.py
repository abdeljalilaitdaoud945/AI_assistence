"""
Vue Contacts — Carnet d'adresses et partage rapide.
"""

import threading
import flet as ft

from vues import theme as T
from vues.theme import C, FONT
from vues.navbar import build_navbar, nav_index_for
from services.contact_service import get_contacts, save_contact, delete_contact
from services.email_service import send_email

def build(page: ft.Page) -> ft.View:

    contacts_col = ft.Column(spacing=10)

    # ==========================================
    # MODAL : AJOUTER UN CONTACT
    # ==========================================
    def open_add_modal(e):
        f_nom = ft.TextField(label="Nom & Prénom", bgcolor=C.bg_subtle, color=C.text, border_color=C.border, focused_border_color=C.accent)
        f_email = ft.TextField(label="Adresse Email", bgcolor=C.bg_subtle, color=C.text, border_color=C.border, focused_border_color=C.accent)
        f_role = ft.TextField(label="Rôle / Entreprise", bgcolor=C.bg_subtle, color=C.text, border_color=C.border, focused_border_color=C.accent)

        def _save(e2):
            if f_nom.value and f_email.value:
                save_contact(f_nom.value, f_email.value, f_role.value)
                page.pop_dialog()
                refresh()

        dialog = ft.AlertDialog(
            modal=False, bgcolor=C.bg_elevated,
            title=ft.Text("Nouveau Contact", color=C.text, weight=ft.FontWeight.W_700),
            content=ft.Column([f_nom, f_email, f_role], tight=True, spacing=10),
            actions=[
                ft.TextButton("Annuler", on_click=lambda e3: page.pop_dialog()),
                ft.TextButton("Enregistrer", on_click=_save, style=ft.ButtonStyle(color=C.accent))
            ]
        )
        page.show_dialog(dialog)

    # ==========================================
    # MODAL : PARTAGER LIEN MEET
    # ==========================================
    def open_share_modal(contact_email, contact_nom):
        f_lien = ft.TextField(
            label="Collez le lien de la réunion ici", 
            hint_text="ex: https://meet.google.com/abc-defg-hij",
            bgcolor=C.bg_subtle, color=C.text, border_color=C.border, focused_border_color=C.accent
        )
        loading = ft.ProgressRing(visible=False, width=16, height=16, color=C.accent, stroke_width=2)
        feedback = ft.Text("", size=FONT.micro)

        def _send(e):
            if not f_lien.value: return
            loading.visible = True
            page.update()

            def work():
                sujet = "Invitation à notre réunion (Lien)"
                corps = f"Bonjour {contact_nom},\n\nVoici le lien pour rejoindre notre réunion :\n{f_lien.value}\n\nÀ tout de suite !"
                res = send_email(contact_email, sujet, corps)
                loading.visible = False
                feedback.value = "Envoyé avec succès !" if "✅" in res else "Erreur d'envoi."
                feedback.color = C.success if "✅" in res else C.danger
                page.update()
                
            threading.Thread(target=work, daemon=True).start()

        dialog = ft.AlertDialog(
            modal=False, bgcolor=C.bg_elevated,
            title=ft.Text(f"Inviter {contact_nom}", color=C.text, weight=ft.FontWeight.W_700),
            content=ft.Column([
                ft.Text(f"Email : {contact_email}", color=C.text_subtle, size=FONT.small),
                f_lien, 
                ft.Row([loading, feedback])
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("Fermer", on_click=lambda e: page.pop_dialog()),
                ft.TextButton("Envoyer l'invitation", on_click=_send, style=ft.ButtonStyle(color=C.accent))
            ]
        )
        page.show_dialog(dialog)

    # ==========================================
    # GÉNÉRATION DES CARTES
    # ==========================================
    def _contact_card(c):
        def _delete(e):
            delete_contact(c["id"])
            refresh()

        return T.card(
            padding=14,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Column(spacing=2, expand=True, controls=[
                        ft.Text(c["nom"], color=C.text, weight=ft.FontWeight.W_700, size=FONT.body),
                        ft.Text(f"📧 {c['email']}", color=C.text_subtle, size=FONT.small),
                        ft.Text(f"🏢 {c.get('role', '')}", color=C.text_muted, size=FONT.micro) if c.get('role') else ft.Container(),
                    ]),
                    ft.Row(spacing=4, controls=[
                        ft.IconButton(
                            icon=ft.Icons.VIDEO_CALL_ROUNDED, 
                            icon_color=C.accent, 
                            tooltip="Envoyer un lien de réunion",
                            on_click=lambda e: open_share_modal(c["email"], c["nom"])
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE, 
                            icon_color=C.danger, 
                            tooltip="Supprimer",
                            on_click=_delete
                        )
                    ])
                ]
            )
        )

    def refresh():
        contacts = get_contacts()
        contacts_col.controls.clear()
        if not contacts:
            contacts_col.controls.append(ft.Text("Aucun contact. Cliquez sur + pour en ajouter.", color=C.text_subtle, italic=True))
        else:
            for c in contacts:
                contacts_col.controls.append(_contact_card(c))
        page.update()

    # ==========================================
    # BUILD
    # ==========================================
    add_btn = ft.IconButton(icon=ft.Icons.ADD_ROUNDED, icon_color="#FFFFFF", bgcolor=C.accent_strong, tooltip="Nouveau contact", on_click=open_add_modal)

    view = ft.View(route="/contacts", padding=0, bgcolor=C.bg, scroll=ft.ScrollMode.AUTO)
    # L'index 4 c'est la vue "Réunion" (pour que le menu reste propre)
    view.navigation_bar = build_navbar(page, selected=4) 
    view.appbar = T.appbar("Carnet d'adresses", back_route="/reunion", page=page, actions=[add_btn, ft.Container(width=8)])

    view.controls = [
        ft.Container(
            padding=ft.Padding(left=20, top=8, right=20, bottom=24),
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Text("Mes Contacts", size=FONT.display, color=C.text, weight=ft.FontWeight.W_700),
                    ft.Text("Gérez vos contacts et invitez-les rapidement à vos réunions.", size=FONT.small, color=C.text_subtle),
                    ft.Container(height=8),
                    contacts_col
                ]
            )
        )
    ]

    refresh()
    return view