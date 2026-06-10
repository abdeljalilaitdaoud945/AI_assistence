"""
Vue Mails — Arc style, cards CLIQUABLES qui ouvrent un modal détail
avec le corps complet du mail et un générateur de réponses IA.
"""

import re
import threading

import flet as ft

from vues import theme as T
from vues.theme import C, FONT
from vues.navbar import build_navbar, nav_index_for
from services.email_service import get_emails_data, get_email_full, generate_email_reply, send_email


# ============================================================
# Helpers
# ============================================================

def _clean_text(s):
    if not s:
        return ""
    s = re.sub(r"\s+", " ", s)
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&")
          .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"'))
    return s.strip()


def _parse_sender(raw):
    if not raw:
        return ("?", "")
    m = re.match(r'\s*"?([^"<]+?)"?\s*<\s*([^>]+)\s*>\s*$', raw)
    if m:
        return (m.group(1).strip() or m.group(2).strip(),
                m.group(2).strip())
    return (raw.strip(), raw.strip())


def _initial(name):
    name = (name or "?").strip()
    if not name:
        return "?"
    parts = name.split()
    if len(parts) >= 2 and parts[0] and parts[1]:
        return (parts[0][0] + parts[1][0]).upper()
    return name[0].upper()


def _avatar(name, size=36):
    palette = [C.accent, C.info, C.success, C.warning,
               "#F472B6", "#22D3EE", "#FB7185"]
    color = palette[abs(hash(name)) % len(palette)] if name else C.accent
    return ft.Container(
        width=size, height=size, border_radius=size,
        bgcolor=ft.Colors.with_opacity(0.18, color),
        alignment=ft.Alignment.CENTER,
        content=ft.Text(_initial(name), color=color,
                        weight=ft.FontWeight.W_700,
                        size=int(size / 2.5)),
    )

def _mail_card(mail, on_click=None):
    raw_sender = mail.get("expediteur", "")
    display, _email = _parse_sender(raw_sender)
    subject = _clean_text(mail.get("sujet", "")) or "(sans sujet)"
    snippet = _clean_text(mail.get("snippet", ""))
    unread = mail.get("unread", True)

    return T.card(
        on_click=on_click,
        padding=16,
        content=ft.Row(
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                _avatar(display),
                ft.Column(
                    expand=True, spacing=4,
                    controls=[
                        ft.Row(
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Text(display, color=C.text, size=FONT.body,
                                        weight=ft.FontWeight.W_700,
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                        expand=True),
                                *([ft.Container(width=8, height=8,
                                                border_radius=999,
                                                bgcolor=C.accent)]
                                  if unread else []),
                            ],
                        ),
                        ft.Text(subject, color=C.text, size=FONT.body,
                                weight=ft.FontWeight.W_500,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(snippet, color=C.text_muted, size=FONT.small,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS),
                    ],
                ),
            ],
        ),
    )


# ============================================================
# Modal détail
# ============================================================

def open_mail_detail(page, message_id, fallback_subject="", fallback_sender=""):
    body_holder = ft.Container(
        width=420, height=600,
        alignment=ft.Alignment.CENTER,
        content=ft.ProgressRing(color=C.accent),
    )
    tag_chip = ft.Container(visible=False)
    
    # Éléments pour la réponse IA
    tone_dropdown = ft.Dropdown(
        label="Ton de la réponse",
        options=[
            ft.dropdown.Option(key="cordial", text="Cordial"),
            ft.dropdown.Option(key="commercial", text="Commercial"),
            ft.dropdown.Option(key="administratif", text="Administratif"),
            ft.dropdown.Option(key="strategique", text="Stratégique (Ferme)"),
        ],
        value="cordial",
        bgcolor=C.bg_subtle, color=C.text, border_color=C.border,
        label_style=ft.TextStyle(color=C.text_subtle)
    )
    draft_field = ft.TextField(
        label="Brouillon", multiline=True, min_lines=4, max_lines=6,
        bgcolor=C.bg_subtle, color=C.text, border_color=C.border,
        focused_border_color=C.accent, visible=False,
        label_style=ft.TextStyle(color=C.text_subtle)
    )
    reply_loading = ft.ProgressRing(visible=False, width=14, height=14, color=C.accent, stroke_width=2)
    reply_feedback = ft.Text("", color=C.success, size=FONT.micro)

    def _close(e=None):
        page.pop_dialog()

    def _classify(e=None):
        from services.mail_classifier import classify_mail
        tag_chip.content = ft.Row(
            spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.ProgressRing(width=12, height=12, stroke_width=2, color=C.accent),
                ft.Text("Classement IA en cours…", color=C.text_subtle, size=FONT.micro),
            ],
        )
        tag_chip.visible = True
        page.update()

        def work():
            try:
                d = get_email_full(message_id)
                tags = classify_mail(
                    message_id,
                    sender=d.get("sender", fallback_sender),
                    subject=d.get("subject", fallback_subject),
                    body=d.get("body", ""),
                )
                tag_chip.content = ft.Row(
                    spacing=6, wrap=True, run_spacing=4,
                    controls=[
                        T.accent_chip(tags.get("type", "?")),
                        *([T.chip(f"Client : {tags['client']}")] if tags.get("client") else []),
                        *([T.chip(f"Projet : {tags['projet']}")] if tags.get("projet") else []),
                        *([T.accent_chip(
                            tags.get("importance", "normale").upper(),
                            color=(C.danger if tags["importance"] == "critique"
                                   else C.warning if tags["importance"] == "haute"
                                   else C.info)
                        )] if tags.get("importance") not in (None, "normale") else []),
                    ],
                )
                page.update()
            except Exception as ex:
                tag_chip.content = ft.Text(f"Erreur classement : {ex}", color=C.danger, size=FONT.micro)
                page.update()

        threading.Thread(target=work, daemon=True).start()

    dialog = ft.AlertDialog(
        modal=False, bgcolor=C.bg_elevated,
        title=ft.Text(fallback_subject or "Email",
                      color=C.text, weight=ft.FontWeight.W_700,
                      size=FONT.h3, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
        content=body_holder,
        actions=[
            ft.TextButton("Classer (IA)", on_click=_classify),
            ft.TextButton("Fermer", on_click=_close),
        ],
    )
    page.show_dialog(dialog)

    def fetch():
        data = get_email_full(message_id)

        if data.get("error"):
            body_holder.content = ft.Text(f"Erreur : {data['error']}", color=C.danger, size=FONT.small)
            page.update()
            return

        display, email = _parse_sender(data.get("sender", fallback_sender))

        header = ft.Container(
            padding=ft.Padding(left=0, top=0, right=0, bottom=12),
            content=ft.Row(
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    _avatar(display, size=42),
                    ft.Column(
                        expand=True, spacing=2,
                        controls=[
                            ft.Text(display or "?", color=C.text, size=FONT.body,
                                    weight=ft.FontWeight.W_700, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(email or "", color=C.text_subtle, size=FONT.micro,
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            *([ft.Text(data.get("date", ""), color=C.text_subtle, size=FONT.micro)]
                              if data.get("date") else []),
                        ],
                    ),
                ],
            ),
        )

        body_text = data.get("body") or "(message vide)"
        body_view = ft.Container(
            height=200, # Hauteur fixe pour laisser place à la réponse IA
            padding=ft.Padding(left=2, top=8, right=2, bottom=2),
            content=ft.ListView(
                expand=True, spacing=4,
                controls=[ft.Text(body_text, color=C.text, size=FONT.small, selectable=True)],
            ),
        )

        # Logique Réponse IA
        def _generate_draft(e):
            reply_loading.visible = True
            draft_field.visible = False
            send_real_btn.visible = False
            reply_feedback.value = ""
            page.update()

            def work():
                draft = generate_email_reply(data.get("subject", ""), body_text, tone_dropdown.value)
                draft_field.value = draft
                draft_field.visible = True
                reply_loading.visible = False
                send_real_btn.visible = True
                page.update()
            threading.Thread(target=work, daemon=True).start()

        def _send_draft(e):
            if not draft_field.value or not email: return
            reply_loading.visible = True
            page.update()
            def work():
                res = send_email(email, f"Re: {data.get('subject', '')}", draft_field.value)
                reply_loading.visible = False
                reply_feedback.value = res
                reply_feedback.color = C.success if "✅" in res else C.danger
                page.update()
            threading.Thread(target=work, daemon=True).start()

        gen_btn = T.pill_button("Générer Réponse (IA)", icon=ft.Icons.AUTO_AWESOME, on_click=_generate_draft, primary=False)
        
        # LA CORRECTION EST ICI : on instancie d'abord, on cache ensuite.
        send_real_btn = T.pill_button("Envoyer", icon=ft.Icons.SEND, on_click=_send_draft)
        send_real_btn.visible = False

        reply_section = ft.Container(
            padding=14, border_radius=12, bgcolor=ft.Colors.with_opacity(0.3, C.bg_subtle),
            border=ft.Border(top=ft.BorderSide(1, C.border), bottom=ft.BorderSide(1, C.border), left=ft.BorderSide(3, C.accent), right=ft.BorderSide(1, C.border)),
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Text("Réponse Intelligente", color=C.text_muted, size=FONT.small, weight=ft.FontWeight.W_600),
                    ft.Row([tone_dropdown, gen_btn, reply_loading]),
                    draft_field,
                    ft.Row([send_real_btn, reply_feedback])
                ]
            )
        )

        body_holder.content = ft.Column(
            spacing=10, tight=False, expand=True,
            controls=[
                header,
                tag_chip,
                T.divider(),
                body_view,
                reply_section
            ],
        )
        dialog.title = ft.Text(
            data.get("subject", "(sans objet)"),
            color=C.text, weight=ft.FontWeight.W_700, size=FONT.h3,
            max_lines=2, overflow=ft.TextOverflow.ELLIPSIS,
        )
        page.update()

    threading.Thread(target=fetch, daemon=True).start()


# ============================================================
# Build
# ============================================================

def build(page: ft.Page) -> ft.View:

    loading = ft.ProgressRing(visible=True, width=18, height=18,
                              color=C.accent, stroke_width=2)
    emails_column = ft.Column(spacing=10, expand=True)

    def fetch_mails():
        try:
            emails = get_emails_data(limit=10, unread_only=True)
            emails_column.controls.clear()
            loading.visible = False

            if not emails:
                emails_column.controls.append(
                    ft.Container(
                        padding=24, alignment=ft.Alignment.CENTER,
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=8,
                            controls=[
                                ft.Icon(ft.Icons.INBOX_OUTLINED, color=C.text_subtle, size=28),
                                ft.Text("Aucun nouvel email.", color=C.text_subtle, italic=True, size=FONT.small),
                            ],
                        ),
                    )
                )
            else:
                for m in emails:
                    mid = m.get("id")
                    subj = _clean_text(m.get("sujet", ""))
                    sender = m.get("expediteur", "")
                    emails_column.controls.append(
                        _mail_card(
                            m,
                            on_click=lambda e, _mid=mid, _s=subj, _sd=sender: open_mail_detail(page, _mid, _s, _sd),
                        )
                    )
            page.update()
        except Exception as e:
            loading.visible = False
            emails_column.controls.append(
                ft.Text(f"Erreur : {e}", color=C.danger, size=FONT.small)
            )
            page.update()

    threading.Thread(target=fetch_mails, daemon=True).start()

    async def open_mailtotal(e):
        await page.push_route("/mailtotal")

    async def push_settings(e):
        await page.push_route("/settings")

    actions = [
        ft.IconButton(icon=ft.Icons.INBOX_ROUNDED, icon_color=C.text_muted, icon_size=18, tooltip="Tous les mails", on_click=open_mailtotal),
        ft.IconButton(icon=ft.Icons.TUNE_ROUNDED, icon_color=C.text_muted, icon_size=18, tooltip="Paramètres", on_click=push_settings),
        ft.Container(width=8),
    ]

    view = ft.View(route="/mails", padding=0, bgcolor=C.bg, scroll=ft.ScrollMode.AUTO)
    view.navigation_bar = build_navbar(page, selected=nav_index_for("/mails"))
    view.appbar = T.appbar("Messagerie", actions=actions)

    view.controls = [
        ft.Container(
            padding=ft.Padding(left=20, top=8, right=20, bottom=24),
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text("Boîte de réception", size=FONT.display, color=C.text, weight=ft.FontWeight.W_700),
                            ft.Text("Non lus", size=FONT.small, color=C.text_subtle, weight=ft.FontWeight.W_500),
                        ],
                    ),
                    ft.Row([loading], alignment=ft.MainAxisAlignment.START),
                    emails_column,
                ],
            ),
        ),
    ]
    return view