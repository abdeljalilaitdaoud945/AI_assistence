import flet as ft
from datetime import datetime
import calendar
import threading
from services.calendar_service import get_events

def build(page: ft.Page) -> ft.View:
    today = datetime.today()
    state = {
        "year": today.year,
        "month": today.month,
        "selected": today.day
    }

    month_label = ft.Text(
        "", 
        size=14, 
        weight=ft.FontWeight.BOLD, 
        color=ft.Colors.WHITE
    )

    calendar_body = ft.Column(spacing=4, expand=False)

    events_column = ft.Column(
        [],
        spacing=8,
        scroll=ft.ScrollMode.AUTO,
        expand=True
    )

    loading = ft.ProgressRing(
        visible=False,
        width=12,
        height=12,
        stroke_width=2,
        color="#38BDF8"
    )

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
                    ft.Text(result, color="#64748B", size=11, italic=True)
                )
            else:
                events = result.split("\n---\n")
                for event in events:
                    events_column.controls.append(
                        ft.Container(
                            content=ft.Text(event, color=ft.Colors.WHITE, size=11),
                            bgcolor="#1E293B",
                            padding=10,
                            border_radius=8,
                            border=ft.Border(left=ft.BorderSide(3, "#10B981")),
                            shadow=ft.BoxShadow(
                                blur_radius=4,
                                color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK)
                            )
                        )
                    )
            page.update()

        threading.Thread(target=fetch).start()

    def on_day_click(e):
        day = e.control.data
        if not day: return
        state["selected"] = day
        date_str = f"{state['year']}-{state['month']:02d}-{day:02d}"
        render_calendar()
        load_events(date_str)

    def render_calendar():
        month_label.value = f"{calendar.month_name[state['month']].capitalize()} {state['year']}"
        calendar_body.controls.clear()

        weekdays_row = ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        for d in ["L", "M", "M", "J", "V", "S", "D"]:
            weekdays_row.controls.append(
                ft.Container(
                    width=28, 
                    alignment=ft.Alignment(0, 0),
                    content=ft.Text(d, size=10, weight=ft.FontWeight.BOLD, color="#94A3B8")
                )
            )
        calendar_body.controls.append(weekdays_row)

        first_weekday, days_in_month = calendar.monthrange(state["year"], state["month"])
        current_row = ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        for _ in range(first_weekday):
            current_row.controls.append(ft.Container(width=28, height=28))

        for day in range(1, days_in_month + 1):
            is_today = (day == today.day and state["month"] == today.month and state["year"] == today.year)
            is_selected = (day == state["selected"])

            bg_color = ft.Colors.TRANSPARENT
            txt_color = ft.Colors.WHITE
            border = None

            if is_selected:
                bg_color = "#EC4899"
            elif is_today:
                txt_color = "#38BDF8"
                border = ft.Border(*[ft.BorderSide(1, "#38BDF8")]*4)

            current_row.controls.append(
                ft.Container(
                    width=28, 
                    height=28,
                    alignment=ft.Alignment(0, 0),
                    bgcolor=bg_color,
                    border=border,
                    border_radius=14, 
                    content=ft.Text(
                        str(day),
                        size=11,
                        color=txt_color,
                        weight=ft.FontWeight.BOLD if (is_selected or is_today) else ft.FontWeight.NORMAL
                    ),
                    data=day,
                    on_click=on_day_click,
                )
            )

            if len(current_row.controls) == 7:
                calendar_body.controls.append(current_row)
                current_row = ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        if len(current_row.controls) > 0 and len(current_row.controls) < 7:
            while len(current_row.controls) < 7:
                current_row.controls.append(ft.Container(width=28, height=28))
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

    async def go_back(e):
        await page.push_route("/rdv")
 
    btn_style = ft.ButtonStyle(padding=0)

    nav_mois = ft.Row(
        [
            ft.IconButton(ft.Icons.CHEVRON_LEFT, icon_color=ft.Colors.WHITE, icon_size=16, width=24, height=24, style=btn_style, on_click=prev_month),
            month_label,
            ft.IconButton(ft.Icons.CHEVRON_RIGHT, icon_color=ft.Colors.WHITE, icon_size=16, width=24, height=24, style=btn_style, on_click=next_month),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    bloc_calendrier = ft.Container(
        border_radius=15,
        bgcolor="#111827",
        padding=12,
        shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK)),
        content=ft.Column(
            [nav_mois, ft.Container(height=5), calendar_body],
            spacing=0,
        ),
    )

    bloc_evenements = ft.Container(
        expand=True, 
        padding=15,
        border_radius=15,
        bgcolor="#111827",
        shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK)),
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Événements", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        loading,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                events_column,
            ],
            spacing=10,
        ),
    )

    header = ft.Row(
        [
            ft.IconButton(icon=ft.Icons.ARROW_BACK_IOS_NEW, icon_color=ft.Colors.WHITE, icon_size=14, width=24, height=24, style=btn_style, on_click=go_back),
            ft.Text("Mon Calendrier", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        ],
        alignment=ft.MainAxisAlignment.START,
    )

    render_calendar()
    date_selected_str = f"{state['year']}-{state['month']:02d}-{state['selected']:02d}"
    load_events(date_selected_str)

    return ft.View(
        route="/calendrier",
        padding=15,
        bgcolor="#0B1220",
        controls=[
            ft.Column(
                [
                    header, 
                    ft.Container(height=5), 
                    bloc_calendrier, 
                    bloc_evenements
                ],
                expand=True,
                spacing=10,
            )
        ],
    )