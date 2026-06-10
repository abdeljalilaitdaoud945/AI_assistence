"""
Vue Rendez-vous — dashboard journée + bouton "agenda complet".
Style Arc cohérent.
"""

import threading
from datetime import datetime

import flet as ft

from vues import theme as T
from vues.theme import C, FONT
from vues.navbar import build_navbar, nav_index_for
from services.calendar_service import get_today_events


def build(page: ft.Page) -> ft.View:

    dashboard_column = ft.Column(
        spacing=12, expand=True, scroll=ft.ScrollMode.AUTO,
    )
    loading = ft.ProgressRing(visible=False, width=14, height=14,
                              stroke_width=2, color=C.accent)

    async def open_calendar(e):
        await page.push_route("/calendrier")

    def event_card(time_str, summary, color):
        return T.card(
            accent=True,
            padding=14,
            content=ft.Row(
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=44,
                        content=ft.Text(
                            time_str.split(" ")[0] if " " in time_str else time_str,
                            color=C.accent, size=FONT.body,
                            weight=ft.FontWeight.W_700,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ),
                    ft.Container(
                        width=1, height=32,
                        bgcolor=C.border,
                    ),
                    ft.Column(
                        spacing=2, expand=True,
                        controls=[
                            ft.Text(summary, color=C.text, size=FONT.body,
                                    weight=ft.FontWeight.W_600,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(time_str, color=C.text_subtle,
                                    size=FONT.micro),
                        ],
                    ),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED,
                            color=C.text_subtle, size=18),
                ],
            ),
        )

    def load_real_events():
        loading.visible = True
        page.update()

        def fetch():
            dashboard_column.controls.clear()

            # ---- En-tête de section ----
            today_str = datetime.now().strftime("%A %d %B").capitalize()
            dashboard_column.controls.append(
                ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text("Aujourd'hui", size=FONT.display,
                                color=C.text, weight=ft.FontWeight.W_700),
                        ft.Text(today_str, color=C.text_subtle,
                                size=FONT.body),
                    ],
                )
            )

            # ---- Bouton "Agenda complet" ----
            dashboard_column.controls.append(
                ft.Container(
                    margin=ft.Margin(left=0, top=8, right=0, bottom=8),
                    content=T.card(
                        on_click=open_calendar,
                        accent=True,
                        padding=16,
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Row(
                                    spacing=12,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    controls=[
                                        ft.Container(
                                            width=36, height=36,
                                            border_radius=12,
                                            bgcolor=ft.Colors.with_opacity(0.18, C.accent),
                                            alignment=ft.Alignment.CENTER,
                                            content=ft.Icon(
                                                ft.Icons.CALENDAR_MONTH_ROUNDED,
                                                color=C.accent, size=20,
                                            ),
                                        ),
                                        ft.Column(
                                            spacing=2,
                                            controls=[
                                                ft.Text("Agenda complet",
                                                        color=C.text,
                                                        size=FONT.body,
                                                        weight=ft.FontWeight.W_600),
                                                ft.Text("Vue mensuelle",
                                                        color=C.text_subtle,
                                                        size=FONT.micro),
                                            ],
                                        ),
                                    ],
                                ),
                                ft.Icon(ft.Icons.ARROW_FORWARD_IOS_ROUNDED,
                                        color=C.text_subtle, size=14),
                            ],
                        ),
                    ),
                )
            )

            # ---- Section "Programme du jour" ----
            dashboard_column.controls.append(
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("Programme du jour", size=FONT.h2,
                                color=C.text, weight=ft.FontWeight.W_700),
                        loading,
                    ],
                )
            )

            # ---- Fetch real events ----
            try:
                events = get_today_events()
                now = datetime.now().astimezone()

                if not events:
                    dashboard_column.controls.append(
                        T.card(
                            content=ft.Column(
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=10,
                                controls=[
                                    ft.Container(height=4),
                                    ft.Icon(ft.Icons.EVENT_BUSY_OUTLINED,
                                            color=C.text_subtle, size=26),
                                    ft.Text("Aucun événement aujourd'hui.",
                                            color=C.text_subtle, italic=True,
                                            size=FONT.small),
                                    ft.Container(height=4),
                                ],
                            ),
                        )
                    )
                else:
                    upcoming_count = 0
                    for i, e in enumerate(events):
                        raw_start = e["start"].get("dateTime",
                                                   e["start"].get("date", ""))
                        raw_end = e["end"].get("dateTime",
                                               e["end"].get("date", ""))
                        try:
                            dt_start = datetime.fromisoformat(
                                raw_start.replace("Z", "+00:00")).astimezone()
                            dt_end = datetime.fromisoformat(
                                raw_end.replace("Z", "+00:00")).astimezone()
                            if dt_end < now:
                                continue
                            time_str = (f"{dt_start.strftime('%H:%M')} – "
                                        f"{dt_end.strftime('%H:%M')}")
                        except Exception:
                            time_str = "Toute la journée"

                        upcoming_count += 1
                        summary = e.get("summary", "Sans titre")
                        dashboard_column.controls.append(
                            event_card(time_str, summary, C.accent)
                        )

                    if upcoming_count == 0:
                        dashboard_column.controls.append(
                            T.card(
                                content=ft.Row(
                                    spacing=10,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    controls=[
                                        ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE,
                                                color=C.success, size=20),
                                        ft.Text(
                                            "Journée terminée. Plus aucun RDV à venir.",
                                            color=C.success, size=FONT.small,
                                            weight=ft.FontWeight.W_600,
                                        ),
                                    ],
                                ),
                            )
                        )

            except Exception as ex:
                dashboard_column.controls.append(
                    T.card(content=ft.Text(
                        f"Erreur de synchronisation : {ex}",
                        color=C.danger, size=FONT.small,
                    ))
                )

            loading.visible = False
            page.update()

        threading.Thread(target=fetch, daemon=True).start()

    load_real_events()

    async def push_settings(e):
        await page.push_route("/settings")

    actions = [
        ft.IconButton(
            icon=ft.Icons.REFRESH_ROUNDED,
            icon_color=C.text_muted, icon_size=18,
            tooltip="Rafraîchir",
            on_click=lambda e: load_real_events(),
        ),
        ft.IconButton(
            icon=ft.Icons.TUNE_ROUNDED,
            icon_color=C.text_muted, icon_size=18,
            tooltip="Paramètres",
            on_click=push_settings,
        ),
        ft.Container(width=8),
    ]

    view = ft.View(
        route="/rdv", padding=0, bgcolor=C.bg,
    )
    view.navigation_bar = build_navbar(page, selected=nav_index_for("/rdv"))
    view.appbar = T.appbar("Rendez-vous", actions=actions)

    view.controls = [
        ft.Container(
            padding=ft.Padding(left=20, top=8, right=20, bottom=24),
            content=dashboard_column,
        ),
    ]

    return view