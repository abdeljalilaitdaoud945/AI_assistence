import flet as ft
from datetime import datetime
import calendar
import threading
from services.calendar_service import get_events

def build(page: ft.Page) -> ft.View:
    today = datetime.today()
    state = {"year": today.year, "month": today.month, "selected": today.day}

    # Titre du mois en blanc
    month_label = ft.Text("", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)

    grid = ft.GridView(
        runs_count=7,
        spacing=8,
        run_spacing=8,
        expand=True
    )

    events_column = ft.Column(
        [],
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
        expand=True
    )

    loading = ft.ProgressRing(
        visible=False,
        width=16,
        height=16,
        stroke_width=2,
        color="#38BDF8" # Bleu néon pour le chargement
    )

    # ================= EVENTS =================
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
                    ft.Text(result, color="#94A3B8", italic=True, size=13)
                )
            else:
                events = result.split("\n---\n")
                for event in events:
                    events_column.controls.append(
                        ft.Container(
                            content=ft.Text(event, color=ft.Colors.WHITE, size=13),
                            bgcolor="#1E293B", # Fond sombre type Glassmorphism
                            padding=15,
                            border_radius=12,
                            # Bordure gauche colorée (Vert néon) pour le style
                            border=ft.border.only(left=ft.BorderSide(4, "#10B981")),
                            # CORRECTION FLET 0.80+ : ft.Colors.BLACK au lieu de "black"
                            shadow=ft.BoxShadow(blur_radius=5, color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK))
                        )
                    )

            page.update()

        threading.Thread(target=fetch).start()

    # ================= CLICK =================
    def on_day_click(e):
        day = e.control.data
        if day:
            state["selected"] = day
            date_str = f"{state['year']}-{state['month']:02d}-{day:02d}"
            render_calendar()
            load_events(date_str)

    # ================= CALENDAR =================
    def render_calendar():
        month_label.value = f"{calendar.month_name[state['month']]} {state['year']}"
        grid.controls.clear()

        # En-têtes des jours en couleur vive
        for d in ["L", "M", "M", "J", "V", "S", "D"]:
            grid.controls.append(
                ft.Container(
                    content=ft.Text(d, size=12, weight=ft.FontWeight.BOLD, color="#38BDF8"),
                    alignment=ft.Alignment.CENTER, # CORRECTION FLET 0.80+
                    height=20,
                )
            )

        first_weekday, days_in_month = calendar.monthrange(
            state["year"], state["month"]
        )
        first_weekday = (first_weekday + 1) % 7

        for _ in range(first_weekday):
            grid.controls.append(ft.Container())

        for day in range(1, days_in_month + 1):
            is_today = (
                day == today.day
                and state["month"] == today.month
                and state["year"] == today.year
            )
            is_selected = day == state["selected"]

            # 🎨 STYLE DARK COLORÉ
            if is_selected:
                bg = "#EC4899" # Rose néon quand sélectionné
                txt = ft.Colors.WHITE
                border = ft.border.all(0, ft.Colors.TRANSPARENT)
            elif is_today:
                bg = "#38BDF8" # Bleu vif pour aujourd'hui
                txt = "#0F172A" # Texte sombre pour faire contraste
                border = ft.border.all(0, ft.Colors.TRANSPARENT)
            else:
                bg = "#111827" # Fond de la carte très sombre
                txt = ft.Colors.WHITE
                border = ft.border.all(1, "#1E293B") # Bordure subtile

            grid.controls.append(
                ft.Container(
                    content=ft.Text(str(day), color=txt, size=13, weight=ft.FontWeight.BOLD if is_selected or is_today else ft.FontWeight.NORMAL),
                    bgcolor=bg,
                    border_radius=10,
                    height=35,  
                    alignment=ft.Alignment.CENTER, # CORRECTION FLET 0.80+
                    data=day,
                    on_click=on_day_click,
                    border=border,
                    shadow=ft.BoxShadow(blur_radius=8, color=bg, spread_radius=1) if is_selected or is_today else None # Effet de lueur (glow)
                )
            )

        page.update()

    # ================= NAV =================
    def prev_month(e):
        if state["month"] == 1:
            state["month"] = 12
            state["year"] -= 1
        else:
            state["month"] -= 1

        state["selected"] = 1
        render_calendar()
        events_column.controls.clear()
        page.update()

    def next_month(e):
        if state["month"] == 12:
            state["month"] = 1
            state["year"] += 1
        else:
            state["month"] += 1

        state["selected"] = 1
        render_calendar()
        events_column.controls.clear()
        page.update()

    # ================= HEADER =================
    header = ft.Container(
        padding=15,
        border_radius=15,
        bgcolor="#111827",
        shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK)), # CORRECTION FLET 0.80+
        content=ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK_ROUNDED,
                    icon_color=ft.Colors.WHITE,
                    icon_size=20,
                    on_click=lambda _: page.go("/rdv"),
                ),
                ft.Text(
                    "Mon Calendrier",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE,
                ),
            ],
            spacing=10,
        ),
    )

    # ================= MONTH NAV =================
    nav_mois = ft.Row(
        [
            ft.IconButton(ft.Icons.CHEVRON_LEFT, icon_color=ft.Colors.WHITE, icon_size=20, on_click=prev_month),
            month_label,
            ft.IconButton(ft.Icons.CHEVRON_RIGHT, icon_color=ft.Colors.WHITE, icon_size=20, on_click=next_month),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    # ================= BLOCS =================
    bloc_calendrier = ft.Container(
        expand=True,
        border_radius=20,
        bgcolor="#111827",
        padding=20,
        shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK)), # CORRECTION FLET 0.80+
        content=ft.Column([nav_mois, grid], spacing=15, expand=True),
    )

    date_selected_str = f"{state['year']}-{state['month']:02d}-{state['selected']:02d}"

    bloc_evenements = ft.Container(
        padding=20,
        border_radius=20,
        bgcolor="#111827",
        height=220,
        shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK)), # CORRECTION FLET 0.80+
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            "Événements du jour",
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.WHITE,
                        ),
                        loading,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                events_column,
            ],
            spacing=12,
            expand=True,
        ),
    )

    # ================= INIT =================
    render_calendar()
    load_events(date_selected_str)

    return ft.View(
        route="/calendrier",
        padding=15,
        bgcolor="#0B1220",  # Fond très sombre comme dans home.py
        controls=[
            ft.Column(
                [header, bloc_calendrier, bloc_evenements],
                expand=True,
                spacing=15,
            )
        ],
    )