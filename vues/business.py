"""
Vue Affaires — suivi dossiers commerciaux Arc-style.
Onglets : Tous / À relancer
Modal ajouter/éditer un deal avec génération d'offre IA.
"""

import flet as ft
import threading

from vues import theme as T
from vues.theme import C, FONT
from vues.navbar import build_navbar, nav_index_for
from services.business_tracker import (
    list_deals, add_deal, update_deal, delete_deal,
    deals_needing_followup, generate_commercial_offer,
    STAGES, STAGE_IDS, STAGE_LABELS, STAGE_COLORS,
)

def build(page: ft.Page) -> ft.View:

    state = {"tab": "all"}

    deals_col = ft.Column(spacing=10)

    # ============================================
    #  Modal d'édition
    # ============================================
    def open_edit_dialog(deal=None):
        is_new = deal is None
        deal = deal or {}

        f_client = ft.TextField(
            label="Client", value=deal.get("client", ""),
            bgcolor=C.bg_subtle, border_color=C.border, focused_border_color=C.accent, color=C.text,
            label_style=ft.TextStyle(color=C.text_subtle),
        )
        f_intitule = ft.TextField(
            label="Intitulé / objet", value=deal.get("intitule", ""),
            bgcolor=C.bg_subtle, border_color=C.border, focused_border_color=C.accent, color=C.text,
            label_style=ft.TextStyle(color=C.text_subtle),
        )
        f_montant = ft.TextField(
            label="Montant (optionnel)", value=str(deal["montant"]) if deal.get("montant") else "",
            keyboard_type=ft.KeyboardType.NUMBER,
            bgcolor=C.bg_subtle, border_color=C.border, focused_border_color=C.accent, color=C.text,
            label_style=ft.TextStyle(color=C.text_subtle),
        )
        f_email = ft.TextField(
            label="Email contact", value=deal.get("contact_email", ""),
            bgcolor=C.bg_subtle, border_color=C.border, focused_border_color=C.accent, color=C.text,
            label_style=ft.TextStyle(color=C.text_subtle),
        )
        f_stage = ft.Dropdown(
            label="Stage", value=deal.get("stage", "demande"),
            options=[ft.dropdown.Option(key=s, text=STAGE_LABELS[s]) for s in STAGE_IDS],
            bgcolor=C.bg_subtle, border_color=C.border, color=C.text, label_style=ft.TextStyle(color=C.text_subtle),
        )
        f_notes = ft.TextField(
            label="Notes", value=deal.get("notes", ""), multiline=True, min_lines=2, max_lines=4,
            bgcolor=C.bg_subtle, border_color=C.border, focused_border_color=C.accent, color=C.text,
            label_style=ft.TextStyle(color=C.text_subtle),
        )

        # Génération IA Offre
        ai_draft_field = ft.TextField(
            label="Brouillon Offre (IA)", multiline=True, min_lines=4, max_lines=6,
            bgcolor=C.bg_elevated, color=C.success, border_color=C.accent, visible=False,
            label_style=ft.TextStyle(color=C.accent)
        )
        ai_loading = ft.ProgressRing(visible=False, width=14, height=14, color=C.accent, stroke_width=2)

        def _gen_offer(e):
            ai_loading.visible = True
            ai_draft_field.visible = False
            page.update()
            def work():
                draft = generate_commercial_offer(f_client.value, f_intitule.value, f_montant.value, f_notes.value)
                ai_draft_field.value = draft
                ai_draft_field.visible = True
                ai_loading.visible = False
                page.update()
            threading.Thread(target=work, daemon=True).start()

        btn_gen_offer = T.pill_button("Générer Offre (IA)", icon=ft.Icons.AUTO_AWESOME, on_click=_gen_offer, primary=False)

        def _save(e):
            try: montant = float(f_montant.value) if f_montant.value else None
            except Exception: montant = None
            
            # Si un brouillon a été généré, on l'ajoute aux notes pour ne pas le perdre
            final_notes = f_notes.value or ""
            if ai_draft_field.visible and ai_draft_field.value:
                final_notes += f"\n\n--- BROUILLON OFFRE ---\n{ai_draft_field.value}"

            if is_new:
                add_deal(client=f_client.value or "Client", intitule=f_intitule.value or "Sans titre", montant=montant, stage=f_stage.value or "demande", contact_email=f_email.value or "", notes=final_notes)
            else:
                update_deal(deal["id"], client=f_client.value, intitule=f_intitule.value, montant=montant, stage=f_stage.value, contact_email=f_email.value, notes=final_notes)
            page.pop_dialog()
            refresh()

        def _del(e):
            if deal.get("id"):
                delete_deal(deal["id"])
                page.pop_dialog()
                refresh()

        actions = [ft.TextButton("Annuler", on_click=lambda _e: page.pop_dialog())]
        if not is_new:
            actions.append(ft.TextButton("Supprimer", on_click=_del, style=ft.ButtonStyle(color=C.danger)))
        actions.append(ft.TextButton("Enregistrer", on_click=_save))

        dialog = ft.AlertDialog(
            modal=False, bgcolor=C.bg_elevated,
            title=ft.Text("Nouveau dossier" if is_new else "Modifier dossier", color=C.text, weight=ft.FontWeight.W_700, size=FONT.h3),
            content=ft.Container(
                width=420,
                content=ft.Column(
                    spacing=10, tight=True, scroll=ft.ScrollMode.AUTO,
                    controls=[f_client, f_intitule, f_montant, f_email, f_stage, f_notes, ft.Row([btn_gen_offer, ai_loading]), ai_draft_field],
                ),
            ),
            actions=actions,
        )
        page.show_dialog(dialog)

    # ============================================
    #  Render d'une card deal
    # ============================================
    def _deal_card(d):
        color = STAGE_COLORS.get(d["stage"], C.accent)
        label = STAGE_LABELS.get(d["stage"], d["stage"])
        m = f"{d['montant']:,.0f}" if d.get("montant") else ""
        return ft.Container(
            padding=14, border_radius=18, bgcolor=C.bg_elevated, ink=True,
            on_click=lambda e, _d=d: open_edit_dialog(_d),
            border=ft.Border(top=ft.BorderSide(1, C.border), bottom=ft.BorderSide(1, C.border), left=ft.BorderSide(3, color), right=ft.BorderSide(1, C.border)),
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(d["client"], color=C.text, weight=ft.FontWeight.W_700, size=FONT.body, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Container(
                                padding=ft.Padding(left=8, top=2, right=8, bottom=2), border_radius=999,
                                bgcolor=ft.Colors.with_opacity(0.16, color),
                                content=ft.Text(label, size=FONT.micro, color=color, weight=ft.FontWeight.W_700),
                            ),
                        ],
                    ),
                    ft.Text(d.get("intitule", ""), color=C.text_muted, size=FONT.small, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Row(
                        spacing=10,
                        controls=[
                            *([ft.Text(f"💰 {m}", color=C.text_subtle, size=FONT.micro)] if m else []),
                            *([ft.Text(f"📧 {d['contact_email']}", color=C.text_subtle, size=FONT.micro, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)] if d.get("contact_email") else []),
                            ft.Text(f"Maj : {d.get('updated_at','')[:10]}", color=C.text_subtle, size=FONT.micro),
                        ],
                    ),
                ],
            ),
        )

    # ============================================
    #  Refresh & Tabs
    # ============================================
    def refresh():
        deals_col.controls.clear()
        if state["tab"] == "followup":
            items = deals_needing_followup(days=7)
            empty_msg = "✅ Aucun dossier en attente de relance (>7 jours)."
        else:
            items = list_deals()
            empty_msg = "Aucun dossier. Tape + pour en créer un."

        if not items:
            deals_col.controls.append(
                ft.Container(padding=24, alignment=ft.Alignment.CENTER, content=ft.Text(empty_msg, color=C.text_subtle, italic=True, size=FONT.small))
            )
        else:
            for d in items: deals_col.controls.append(_deal_card(d))
        page.update()

    def set_tab(t):
        state["tab"] = t
        refresh()

    def tab_pill(label, value):
        active = state["tab"] == value
        return ft.Container(
            padding=ft.Padding(left=14, top=8, right=14, bottom=8), border_radius=999,
            bgcolor=C.accent_strong if active else C.bg_subtle, ink=True,
            on_click=lambda e, v=value: (set_tab(v), refresh_tabs()),
            content=ft.Text(label, size=FONT.small, color="#FFFFFF" if active else C.text_muted, weight=ft.FontWeight.W_700 if active else ft.FontWeight.W_500),
        )

    tabs_row = ft.Row(spacing=8)
    def refresh_tabs():
        tabs_row.controls.clear()
        tabs_row.controls.append(tab_pill("Tous", "all"))
        tabs_row.controls.append(tab_pill("À relancer", "followup"))
        page.update()

    refresh_tabs()

    add_btn = ft.IconButton(icon=ft.Icons.ADD_ROUNDED, icon_color="#FFFFFF", bgcolor=C.accent_strong, tooltip="Nouveau dossier", on_click=lambda e: open_edit_dialog(None))

    view = ft.View(route="/business", padding=0, bgcolor=C.bg, scroll=ft.ScrollMode.AUTO)
    view.navigation_bar = build_navbar(page, selected=nav_index_for("/business"))
    view.appbar = T.appbar("Affaires", back_route="/", page=page, actions=[add_btn, ft.Container(width=8)])

    view.controls = [
        ft.Container(
            padding=ft.Padding(left=20, top=8, right=20, bottom=24),
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Text("Dossiers commerciaux", size=FONT.display, color=C.text, weight=ft.FontWeight.W_700),
                    tabs_row, deals_col,
                ],
            ),
        ),
    ]

    refresh()
    return view