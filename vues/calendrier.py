"""
Vue Calendrier — calendrier mensuel avec suppression d'événements.
"""

import calendar as cal_mod
import threading
from datetime import datetime

import flet as ft

from vues import theme as T
from vues.theme import C, FONT
from vues.navbar import build_navbar, nav_index_for
from services.calendar_service import get_events, delete_event


def build(page: ft.Page) -> ft.View:
    today = datetime.today()
    state = {"year": today.year, "month": today.month, "selected": today.day,
             "current_date_str": ""}

    month_label = ft.Text(
        "", size=FONT.h3, weight=ft.FontWeight.W_700, color=C.text,
    )
    calendar_body = ft.Column(spacing=6, expand=False)
    events_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO,
                              expand=True)
    loading = ft.ProgressRing(visible=False, width=14, height=14,
                              stroke_width=2, color=C.accent)

    # ============================================================
    # Helpers : format date d'un événement
    # ============================================================
    def _format_event_time(ev):
        """Retourne 'HH:MM - HH:MM' ou 'Journée entière' selon le type."""
        start = ev.get("start", "")
        end = ev.get("end", "")
        # Format ISO complet => HH:MM
        try:
            if "T" in start:
                dt_s = datetime.fromisoformat(start.replace("Z", "+00:00"))
                dt_e = datetime.fromisoformat(end.replace("Z", "+00:00"))
                return f"{dt_s.strftime('%H:%M')} - {dt_e.strftime('%H:%M')}"
        except Exception:
            pass
        return "Journée entière"

    # ============================================================
    # Suppression d'un événement (avec dialog de confirmation)
    # ============================================================
    def confirm_delete(ev):
        title = ev.get("summary", "Sans titre")
        ev_id = ev.get("id")

        def do_delete(e):
            page.pop_dialog()
            loading.visible = True
            page.update()

            def work():
                try:
                    delete_event(ev_id)
                    msg = f"✅ « {title} » supprimé"
                    msg_color = C.success
                except Exception as ex:
                    msg = f"❌ Erreur suppression : {ex}"
                    msg_color = C.danger
                finally:
                    loading.visible = False
                page.show_dialog(ft.SnackBar(
                    ft.Text(msg, color=msg_color), duration=2500))
                # Recharge la liste d'événements pour la date courante
                load_events(state["current_date_str"])

            threading.Thread(target=work, daemon=True).start()

        dialog = ft.AlertDialog(
            modal=False, bgcolor=C.bg_elevated,
            title=ft.Row(spacing=8, controls=[
                ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED,
                        color=C.warning, size=22),
                ft.Text("Supprimer l'événement ?",
                        color=C.text, weight=ft.FontWeight.W_700,
                        size=FONT.h3),
            ]),
            content=ft.Container(
                width=360,
                content=ft.Column(spacing=10, tight=True, controls=[
                    ft.Text(
                        f"Tu vas supprimer définitivement :",
                        color=C.text_muted, size=FONT.small),
                    ft.Container(
                        padding=12,
                        bgcolor=C.bg_subtle,
                        border_radius=10,
                        content=ft.Column(spacing=4, controls=[
                            ft.Text(title, color=C.text,
                                    weight=ft.FontWeight.W_600,
                                    size=FONT.body),
                            ft.Text(_format_event_time(ev),
                                    color=C.text_subtle, size=FONT.micro),
                        ]),
                    ),
                    ft.Text("Cette action est irréversible.",
                            color=C.danger, italic=True, size=FONT.micro),
                ]),
            ),
            actions=[
                ft.TextButton("Annuler",
                              on_click=lambda _e: page.pop_dialog()),
                ft.TextButton(
                    "Supprimer",
                    on_click=do_delete,
                    style=ft.ButtonStyle(color=C.danger),
                ),
            ],
        )
        page.show_dialog(dialog)

    # ============================================================
    # Carte d'un événement (avec tous les détails + bouton poubelle)
    # ============================================================
    def _event_card(ev):
        title = ev.get("summary", "Sans titre")
        time_str = _format_event_time(ev)
        location = ev.get("location", "")
        hangout = ev.get("hangoutLink", "")
        description = ev.get("description", "")
        attendees = ev.get("attendees", []) or []
        status = ev.get("status", "")

        details = [
            # Titre
            ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.EVENT_OUTLINED, color=C.accent, size=14),
                    ft.Text(title, color=C.text, size=FONT.body,
                            weight=ft.FontWeight.W_700,
                            max_lines=2, expand=True,
                            overflow=ft.TextOverflow.ELLIPSIS),
                ],
            ),
            # Horaire
            ft.Row(spacing=6, controls=[
                ft.Icon(ft.Icons.SCHEDULE_ROUNDED,
                        color=C.text_subtle, size=12),
                ft.Text(time_str, color=C.text_subtle, size=FONT.micro),
            ]),
        ]

        # Lieu
        if location:
            details.append(ft.Row(
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Icon(ft.Icons.PLACE_OUTLINED,
                            color=C.text_subtle, size=12),
                    ft.Text(location, color=C.text_subtle, size=FONT.micro,
                            max_lines=2, expand=True,
                            overflow=ft.TextOverflow.ELLIPSIS),
                ]))

        # Description (résumée à ~140 chars pour ne pas écraser la carte)
        if description:
            desc_short = (description[:140] + "…"
                          if len(description) > 140 else description)
            details.append(ft.Row(
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Icon(ft.Icons.NOTES_ROUNDED,
                            color=C.text_subtle, size=12),
                    ft.Text(desc_short, color=C.text_muted,
                            size=FONT.micro,
                            max_lines=3, expand=True,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            selectable=True),
                ]))

        # Participants (avec chips si présents)
        if attendees:
            noms = []
            for a in attendees[:6]:  # max 6 chips
                noms.append(a.get("displayName") or a.get("email", "")
                            or "?")
            chip_row = ft.Row(
                spacing=4, wrap=True, run_spacing=4,
                controls=[T.chip(n) for n in noms if n],
            )
            if len(attendees) > 6:
                chip_row.controls.append(T.chip(f"+{len(attendees) - 6}"))
            details.append(ft.Row(
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Icon(ft.Icons.GROUP_OUTLINED,
                            color=C.text_subtle, size=12),
                    ft.Container(expand=True, content=chip_row),
                ]))

        # Lien Meet cliquable
        if hangout:
            async def _open_meet(e, _url=hangout):
                await page.launch_url(_url)
            details.append(ft.Row(
                spacing=6, controls=[
                    ft.Icon(ft.Icons.VIDEOCAM_OUTLINED,
                            color=C.info, size=12),
                    ft.TextButton(
                        "Rejoindre Google Meet",
                        on_click=_open_meet,
                        style=ft.ButtonStyle(
                            color=C.info,
                            padding=ft.Padding(0, 0, 0, 0),
                        ),
                    ),
                ]))

        # Statut (Confirmé / En attente / Annulé)
        if status:
            status_map = {
                "confirmed": ("✅ Confirmé", C.success),
                "tentative": ("⏳ En attente", C.warning),
                "cancelled": ("❌ Annulé", C.danger),
            }
            txt, col = status_map.get(status, (None, None))
            if txt:
                details.append(ft.Container(
                    padding=ft.Padding(left=6, top=2, right=6, bottom=2),
                    border_radius=999,
                    bgcolor=ft.Colors.with_opacity(0.15, col),
                    content=ft.Text(txt, color=col, size=10,
                                    weight=ft.FontWeight.W_700),
                ))

        delete_btn = ft.IconButton(
            icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
            icon_color=C.danger,
            icon_size=18,
            tooltip="Supprimer cet événement",
            on_click=lambda e, _ev=ev: confirm_delete(_ev),
        )

        return T.card(
            accent=True, padding=14,
            content=ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Column(expand=True, spacing=8, controls=details),
                    delete_btn,
                ],
            ),
        )

    # ============================================================
    # Chargement des événements pour la date sélectionnée
    # ============================================================
    def load_events(date_str):
        state["current_date_str"] = date_str
        loading.visible = True
        events_column.controls.clear()
        page.update()

        def fetch():
            try:
                result = get_events(date=date_str)
            except Exception as e:
                loading.visible = False
                events_column.controls.append(
                    ft.Container(
                        padding=16, alignment=ft.Alignment.CENTER,
                        content=ft.Text(f"Erreur : {e}",
                                        color=C.danger, size=FONT.small),
                    )
                )
                page.update()
                return

            loading.visible = False
            events_column.controls.clear()

            # get_events(date) renvoie une LISTE DE STRINGS formatées
            # (texte formaté pour la rétro-compatibilité). On a besoin des
            # OBJETS pour pouvoir supprimer. On rappelle l'API directement.
            events_data = _fetch_events_raw(date_str)

            if not events_data:
                events_column.controls.append(
                    ft.Container(
                        padding=16, alignment=ft.Alignment.CENTER,
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=8,
                            controls=[
                                ft.Icon(ft.Icons.EVENT_BUSY_OUTLINED,
                                        color=C.text_subtle, size=28),
                                ft.Text("Aucun événement ce jour-là",
                                        color=C.text_subtle, italic=True,
                                        size=FONT.small),
                            ],
                        ),
                    )
                )
            else:
                for ev in events_data:
                    events_column.controls.append(_event_card(ev))
            page.update()

        threading.Thread(target=fetch, daemon=True).start()

    # ============================================================
    # Récupération des événements bruts (dicts avec id) pour la suppression
    # ============================================================
    def _fetch_events_raw(date_str):
        """Appelle l'API Google directement pour obtenir les dicts complets."""
        try:
            from googleapiclient.discovery import build
            from services.google_auth import get_credentials
            creds = get_credentials()
            service = build("calendar", "v3", credentials=creds)
            start = f"{date_str}T00:00:00Z"
            end = f"{date_str}T23:59:59Z"
            events = service.events().list(
                calendarId="primary", timeMin=start, timeMax=end,
                singleEvents=True, orderBy="startTime"
            ).execute()
            items = events.get("items", [])
            return [{
                "id": e.get("id"),
                "summary": e.get("summary", "Sans titre"),
                "start": e["start"].get("dateTime", e["start"].get("date")),
                "end": e["end"].get("dateTime", e["end"].get("date")),
                "location": e.get("location", ""),
                "hangoutLink": e.get("hangoutLink", ""),
                "description": e.get("description", ""),
                "attendees": e.get("attendees", []),
                "status": e.get("status", ""),
            } for e in items]
        except Exception as ex:
            print(f"[calendrier] _fetch_events_raw error: {ex}")
            return []

    def on_day_click(e):
        day = e.control.data
        if not day:
            return
        state["selected"] = day
        date_str = f"{state['year']}-{state['month']:02d}-{day:02d}"
        render_calendar()
        load_events(date_str)

    def render_calendar():
        month_label.value = (
            f"{cal_mod.month_name[state['month']].capitalize()} {state['year']}"
        )
        calendar_body.controls.clear()

        # En-têtes des jours
        weekdays_row = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        for d in ["L", "M", "M", "J", "V", "S", "D"]:
            weekdays_row.controls.append(
                ft.Container(
                    width=36, alignment=ft.Alignment.CENTER,
                    content=ft.Text(d, size=FONT.micro,
                                    weight=ft.FontWeight.W_600,
                                    color=C.text_subtle),
                )
            )
        calendar_body.controls.append(weekdays_row)

        first_weekday, days_in_month = cal_mod.monthrange(
            state["year"], state["month"]
        )
        current_row = ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        for _ in range(first_weekday):
            current_row.controls.append(ft.Container(width=36, height=36))

        for day in range(1, days_in_month + 1):
            is_today = (day == today.day and state["month"] == today.month
                        and state["year"] == today.year)
            is_selected = (day == state["selected"])

            if is_selected:
                bg_color = C.accent_strong
                txt_color = "#FFFFFF"
                border = None
            elif is_today:
                bg_color = ft.Colors.with_opacity(0.18, C.accent)
                txt_color = C.accent
                border = None
            else:
                bg_color = None
                txt_color = C.text
                border = None

            current_row.controls.append(
                ft.Container(
                    width=36, height=36,
                    alignment=ft.Alignment.CENTER,
                    bgcolor=bg_color,
                    border=border,
                    border_radius=999,
                    content=ft.Text(
                        str(day), size=FONT.small, color=txt_color,
                        weight=ft.FontWeight.W_700 if (is_selected or is_today)
                                else ft.FontWeight.W_500,
                    ),
                    data=day,
                    ink=True,
                    on_click=on_day_click,
                )
            )

            if len(current_row.controls) == 7:
                calendar_body.controls.append(current_row)
                current_row = ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        if 0 < len(current_row.controls) < 7:
            while len(current_row.controls) < 7:
                current_row.controls.append(ft.Container(width=36, height=36))
            calendar_body.controls.append(current_row)

        page.update()

    def prev_month(e):
        if state["month"] == 1:
            state["month"], state["year"] = 12, state["year"] - 1
        else:
            state["month"] -= 1
        state["selected"] = 1
        render_calendar()
        events_column.controls.clear()
        page.update()

    def next_month(e):
        if state["month"] == 12:
            state["month"], state["year"] = 1, state["year"] + 1
        else:
            state["month"] += 1
        state["selected"] = 1
        render_calendar()
        events_column.controls.clear()
        page.update()

    nav_mois = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.IconButton(
                icon=ft.Icons.CHEVRON_LEFT_ROUNDED,
                icon_color=C.text_muted, icon_size=18,
                on_click=prev_month,
            ),
            month_label,
            ft.IconButton(
                icon=ft.Icons.CHEVRON_RIGHT_ROUNDED,
                icon_color=C.text_muted, icon_size=18,
                on_click=next_month,
            ),
        ],
    )

    bloc_calendrier = T.card(
        padding=16,
        content=ft.Column(spacing=10, controls=[nav_mois, calendar_body]),
    )

    bloc_evenements = T.card(
        padding=16, expand=True,
        content=ft.Column(spacing=10, controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("Événements", size=FONT.h3,
                            weight=ft.FontWeight.W_700, color=C.text),
                    loading,
                ],
            ),
            events_column,
        ]),
    )

    render_calendar()
    date_selected_str = f"{state['year']}-{state['month']:02d}-{state['selected']:02d}"
    load_events(date_selected_str)

    view = ft.View(
        route="/calendrier", padding=0, bgcolor=C.bg,
        scroll=ft.ScrollMode.AUTO,
    )
    view.navigation_bar = build_navbar(
        page, selected=nav_index_for("/calendrier"))
    view.appbar = T.appbar("Calendrier", back_route="/rdv", page=page)

    view.controls = [
        ft.Container(
            padding=ft.Padding(left=20, top=8, right=20, bottom=24),
            content=ft.Column(
                spacing=14, expand=True,
                controls=[bloc_calendrier, bloc_evenements],
            ),
        ),
    ]

    return view