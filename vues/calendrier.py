"""
Vue Calendrier — calendrier mensuel sobre Arc-style.
"""

import calendar as cal_mod
import threading
from datetime import datetime

import flet as ft

from vues import theme as T
from vues.theme import C, FONT
from vues.navbar import build_navbar, nav_index_for
from services.calendar_service import get_events


def build(page: ft.Page) -> ft.View:
    today = datetime.today()
    state = {"year": today.year, "month": today.month, "selected": today.day}

    month_label = ft.Text(
        "", size=FONT.h3, weight=ft.FontWeight.W_700, color=C.text,
    )
    calendar_body = ft.Column(spacing=6, expand=False)
    events_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO,
                              expand=True)
    loading = ft.ProgressRing(visible=False, width=14, height=14,
                              stroke_width=2, color=C.accent)

    def load_events(date_str):
        loading.visible = True
        page.update()

        def fetch():
            try:
                result = get_events(date_str)
            except Exception as e:
                result = f"Erreur : {e}"
            loading.visible = False
            events_column.controls.clear()

            if "Aucun" in result or "Erreur" in result:
                events_column.controls.append(
                    ft.Container(
                        padding=16,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Text(result, color=C.text_subtle,
                                        size=FONT.small, italic=True),
                    )
                )
            else:
                events = result.split("\n---\n")
                for event in events:
                    events_column.controls.append(
                        T.card(
                            accent=True,
                            padding=12,
                            content=ft.Text(event.strip(), color=C.text,
                                            size=FONT.small,
                                            selectable=True),
                        )
                    )
            page.update()

        threading.Thread(target=fetch, daemon=True).start()

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