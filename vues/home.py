"""
Home — refonte Arc-inspired
  - Typo sobre, grande, généreux espacement
  - Hero header avec date / salutation
  - 1 gros graphique marché (sparkline)
  - 4 cards : Bourse / Mails / RDV / Documents (chacune avec une viz)
  - Section "Aujourd'hui" : prochains RDV

Données live chargées en threads pour ne pas geler l'UI.
"""

import threading
from datetime import datetime

import flet as ft

from vues import theme as T
from vues.theme import C, FONT
from vues.navbar import build_navbar

from services.stock_service import get_stock_data, get_stock_history
from services.email_service import get_emails_data
from services.calendar_service import list_upcoming_events
from services.pdf_history import list_history
from services.google_auth import get_user_info


def build(page: ft.Page) -> ft.View:

    # ============================================================
    # Hero — salutation + date
    # ============================================================
    name = "Bonjour"
    try:
        info = get_user_info()
        if info:
            display = info.get("name") or info.get("email", "").split("@")[0]
            if display:
                first = display.split()[0]
                name = f"Bonjour {first}"
    except Exception:
        pass

    now = datetime.now()
    months = ["janvier","février","mars","avril","mai","juin","juillet",
              "août","septembre","octobre","novembre","décembre"]
    days = ["lundi","mardi","mercredi","jeudi","vendredi","samedi","dimanche"]
    date_str = f"{days[now.weekday()]} {now.day} {months[now.month-1]} {now.year}"

    hero = ft.Container(
        padding=ft.Padding(left=0, top=8, right=0, bottom=20),
        content=ft.Column(
            spacing=4,
            controls=[
                ft.Text(date_str.capitalize(), size=FONT.small,
                        color=C.text_subtle, weight=ft.FontWeight.W_500),
                ft.Text(name, size=FONT.display, color=C.text,
                        weight=ft.FontWeight.W_700),
            ],
        ),
    )

    # ============================================================
    # BIG MARKET SPARKLINE — pleine largeur
    # ============================================================
    market_title = ft.Text("S&P 500", size=FONT.body,
                           color=C.text_muted, weight=ft.FontWeight.W_500)
    market_price = ft.Text("—", size=FONT.h1, color=C.text,
                           weight=ft.FontWeight.W_700)
    market_chg = T.accent_chip("—")
    market_chart = ft.Container(
        height=80, alignment=ft.Alignment.CENTER,
        content=ft.ProgressRing(width=18, height=18,
                                stroke_width=2, color=C.accent),
    )

    market_card = T.card(
        padding=20,
        content=ft.Column(
            spacing=14,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Column(spacing=2, controls=[
                            market_title, market_price,
                        ]),
                        market_chg,
                    ],
                ),
                market_chart,
            ],
        ),
    )

    def load_market():
        try:
            d = get_stock_data("^GSPC")
            hist = get_stock_history("^GSPC", "1mo")
            if d.get("error") or d.get("price") is None:
                market_price.value = "Indisponible"
                market_chg.content.value = "—"
                market_chart.content = ft.Text("Pas de données",
                                               color=C.text_subtle,
                                               size=FONT.small)
            else:
                pct = d["change_percent"]
                sign = "+" if pct >= 0 else ""
                color = C.success if pct >= 0 else C.danger
                market_title.value = f"S&P 500 · {d['name']}"
                market_price.value = f"{d['price']:,.2f}"
                market_chg.content.value = f"{sign}{pct:.2f}%"
                market_chg.bgcolor = ft.Colors.with_opacity(0.15, color)
                market_chg.content.color = color
                market_chart.content = T.sparkline(
                    hist, color=color, width=600, height=80
                )
            page.update()
        except Exception as e:
            market_price.value = "Erreur"
            market_chart.content = ft.Text(str(e)[:60],
                                           color=C.danger, size=FONT.small)
            page.update()

    # ============================================================
    # 4 CARDS
    # ============================================================

    # ---- Bourse mini (Nasdaq) ----
    nasdaq_val = ft.Text("—", size=FONT.h3,
                         color=C.text, weight=ft.FontWeight.W_700)
    nasdaq_chg = ft.Text("—", size=FONT.small, color=C.text_subtle,
                         weight=ft.FontWeight.W_600)
    nasdaq_chart = ft.Container(
        height=52,
        content=ft.ProgressRing(width=12, height=12,
                                stroke_width=2, color=C.accent),
    )

    async def go_bourse(e):
        await page.push_route("/bourse")

    bourse_card = T.card(
        on_click=go_bourse,
        padding=16,
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(spacing=8, controls=[
                            ft.Icon(ft.Icons.SHOW_CHART_ROUNDED,
                                    color=C.accent, size=14),
                            ft.Text("Bourse", color=C.text_muted,
                                    size=FONT.small,
                                    weight=ft.FontWeight.W_500),
                        ]),
                        ft.Icon(ft.Icons.ARROW_OUTWARD_ROUNDED,
                                color=C.text_subtle, size=14),
                    ],
                ),
                nasdaq_val, nasdaq_chg, nasdaq_chart,
            ],
        ),
    )

    def load_bourse_mini():
        try:
            d = get_stock_data("^IXIC")
            hist = get_stock_history("^IXIC", "1mo")
            if d.get("error") or d.get("price") is None:
                nasdaq_val.value = "—"
                nasdaq_chg.value = "Indisponible"
                nasdaq_chart.content = ft.Container()
            else:
                pct = d["change_percent"]
                sign = "+" if pct >= 0 else ""
                color = C.success if pct >= 0 else C.danger
                nasdaq_val.value = f"{d['price']:,.0f}"
                nasdaq_chg.value = f"Nasdaq · {sign}{pct:.2f}%"
                nasdaq_chg.color = color
                nasdaq_chart.content = T.sparkline(hist, color=color,
                                                   width=220, height=52)
            page.update()
        except Exception:
            nasdaq_val.value = "—"
            nasdaq_chg.value = "Erreur"
            page.update()

    # ---- Mails — ring chart ----
    mails_ring_holder = ft.Container(
        height=84,
        alignment=ft.Alignment.CENTER,
        content=ft.ProgressRing(width=14, height=14,
                                stroke_width=2, color=C.accent),
    )
    mails_sub = ft.Text("—", color=C.text_subtle, size=FONT.micro)

    async def go_mails(e):
        await page.push_route("/mails")

    mails_card = T.card(
        on_click=go_mails,
        padding=16,
        content=ft.Column(
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(spacing=8, controls=[
                            ft.Icon(ft.Icons.MAIL_OUTLINE_ROUNDED,
                                    color=C.accent, size=14),
                            ft.Text("Mails", color=C.text_muted,
                                    size=FONT.small,
                                    weight=ft.FontWeight.W_500),
                        ]),
                        ft.Icon(ft.Icons.ARROW_OUTWARD_ROUNDED,
                                color=C.text_subtle, size=14),
                    ],
                ),
                ft.Container(
                    alignment=ft.Alignment.CENTER,
                    content=mails_ring_holder,
                ),
                mails_sub,
            ],
        ),
    )

    def load_mails_count():
        try:
            unread_list = get_emails_data(limit=30, unread_only=True)
            unread = len(unread_list) if unread_list else 0
            try:
                total_list = get_emails_data(limit=30, unread_only=False)
                total = len(total_list) if total_list else max(unread, 1)
            except Exception:
                total = max(unread, 1)
            mails_ring_holder.content = T.ring_chart(
                value=unread, total=max(total, 1),
                color=C.accent, size=84, stroke=7,
                label=str(unread),
            )
            mails_sub.value = ("non lu" if unread == 1 else f"non lus")
            if unread == 0:
                mails_sub.value = "boîte à jour"
            else:
                mails_sub.value = f"{unread} non lu" + ("s" if unread > 1 else "")
            page.update()
        except Exception:
            mails_ring_holder.content = ft.Text("—",
                                                color=C.text_subtle,
                                                size=FONT.small)
            mails_sub.value = "Erreur"
            page.update()

    # ---- RDV — dots timeline ----
    rdv_timeline_holder = ft.Container(
        height=84,
        alignment=ft.Alignment.CENTER,
        content=ft.ProgressRing(width=14, height=14,
                                stroke_width=2, color=C.accent),
    )
    rdv_sub = ft.Text("—", color=C.text_subtle, size=FONT.micro)

    async def go_rdv(e):
        await page.push_route("/rdv")

    rdv_card = T.card(
        on_click=go_rdv,
        padding=16,
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(spacing=8, controls=[
                            ft.Icon(ft.Icons.EVENT_AVAILABLE_ROUNDED,
                                    color=C.accent, size=14),
                            ft.Text("Rendez-vous", color=C.text_muted,
                                    size=FONT.small,
                                    weight=ft.FontWeight.W_500),
                        ]),
                        ft.Icon(ft.Icons.ARROW_OUTWARD_ROUNDED,
                                color=C.text_subtle, size=14),
                    ],
                ),
                rdv_timeline_holder, rdv_sub,
            ],
        ),
    )

    def _events_safe(max_results=4):
        """Récupère les events sous forme structurée si possible, sinon []"""
        from services.calendar_service import get_events
        try:
            events = get_events(max_results=max_results) or []
            return events if isinstance(events, list) else []
        except Exception:
            return []

    def load_rdv():
        try:
            events = _events_safe(4)
            if not events:
                rdv_timeline_holder.content = ft.Text(
                    "Pas de RDV prévu", color=C.text_subtle,
                    size=FONT.small, italic=True,
                )
                rdv_sub.value = "—"
            else:
                nodes = []
                for i, ev in enumerate(events[:4]):
                    label = "?"
                    if isinstance(ev, dict):
                        start = ev.get("start") or ev.get("dateTime") or ""
                        try:
                            d = datetime.fromisoformat(str(start)[:19])
                            label = d.strftime("%d/%m")
                        except Exception:
                            label = str(start)[:5]
                    nodes.append({"label": label, "accent": i == 0})
                rdv_timeline_holder.content = T.dots_timeline(
                    nodes, width=220, height=70, color=C.accent
                )
                rdv_sub.value = (f"{len(events)} à venir"
                                 if len(events) > 1 else "1 à venir")
            page.update()
        except Exception:
            rdv_timeline_holder.content = ft.Text("—",
                                                  color=C.text_subtle,
                                                  size=FONT.small)
            rdv_sub.value = "Erreur"
            page.update()

    # ---- Documents ----
    docs_count = ft.Text("—", size=FONT.display, color=C.text,
                         weight=ft.FontWeight.W_700)
    docs_last = ft.Text("—", size=FONT.micro, color=C.text_subtle,
                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
    docs_caption = ft.Text("analysés", size=FONT.small,
                           color=C.text_muted, weight=ft.FontWeight.W_500)

    async def go_docs(e):
        await page.push_route("/pdf")

    docs_card = T.card(
        on_click=go_docs,
        padding=16,
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(spacing=8, controls=[
                            ft.Icon(ft.Icons.DESCRIPTION_OUTLINED,
                                    color=C.accent, size=14),
                            ft.Text("Documents", color=C.text_muted,
                                    size=FONT.small,
                                    weight=ft.FontWeight.W_500),
                        ]),
                        ft.Icon(ft.Icons.ARROW_OUTWARD_ROUNDED,
                                color=C.text_subtle, size=14),
                    ],
                ),
                ft.Container(height=8),
                docs_count, docs_caption,
                ft.Container(height=4),
                docs_last,
            ],
        ),
    )

    def load_docs():
        try:
            hist = list_history()
            docs_count.value = str(len(hist))
            if hist:
                last = hist[0]
                docs_last.value = f"Dernier : {(last.get('filename') or '')[:30]}"
            else:
                docs_last.value = "Aucun CR analysé"
            page.update()
        except Exception:
            docs_count.value = "—"
            docs_last.value = ""
            page.update()

    # ============================================================
    # Grid 4 cards
    # ============================================================
    grid = ft.ResponsiveRow(
        spacing=12, run_spacing=12,
        controls=[
            ft.Container(col={"xs": 6, "md": 3}, content=bourse_card),
            ft.Container(col={"xs": 6, "md": 3}, content=mails_card),
            ft.Container(col={"xs": 6, "md": 3}, content=rdv_card),
            ft.Container(col={"xs": 6, "md": 3}, content=docs_card),
        ],
    )

    # ============================================================
    # Section Prochains RDV
    # ============================================================
    next_rdv_col = ft.Column(spacing=8)
    next_rdv_col.controls.append(
        ft.Container(
            padding=20, alignment=ft.Alignment.CENTER,
            content=ft.ProgressRing(width=14, height=14,
                                    stroke_width=2, color=C.accent),
        )
    )

    def load_next_rdv():
        try:
            events = _events_safe(4)
            next_rdv_col.controls.clear()
            if not events:
                next_rdv_col.controls.append(
                    ft.Container(
                        padding=18,
                        content=ft.Text(
                            "Pas de prochain rendez-vous.",
                            color=C.text_subtle, size=FONT.small,
                            italic=True,
                        ),
                    )
                )
            else:
                for ev in events[:4]:
                    summary = "Sans titre"
                    when = ""
                    if isinstance(ev, dict):
                        summary = ev.get("summary") or "Sans titre"
                        start = ev.get("start") or ev.get("dateTime") or ""
                        if start:
                            try:
                                dt = datetime.fromisoformat(str(start)[:19])
                                when = dt.strftime("%a %d %b · %H:%M")
                            except Exception:
                                when = str(start)[:16]
                    next_rdv_col.controls.append(
                        ft.Container(
                            padding=ft.Padding(left=14, top=12,
                                               right=14, bottom=12),
                            border_radius=14,
                            bgcolor=C.bg_elevated,
                            border=ft.Border(
                                top=ft.BorderSide(1, C.border_subtle),
                                bottom=ft.BorderSide(1, C.border_subtle),
                                left=ft.BorderSide(3, C.accent),
                                right=ft.BorderSide(1, C.border_subtle),
                            ),
                            content=ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Column(spacing=2, expand=True,
                                              controls=[
                                                  ft.Text(summary,
                                                          color=C.text,
                                                          size=FONT.body,
                                                          weight=ft.FontWeight.W_600,
                                                          max_lines=1,
                                                          overflow=ft.TextOverflow.ELLIPSIS),
                                                  ft.Text(when,
                                                          color=C.text_subtle,
                                                          size=FONT.micro),
                                              ]),
                                    ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED,
                                            color=C.text_subtle, size=18),
                                ],
                            ),
                        )
                    )
            page.update()
        except Exception:
            page.update()

    # ============================================================
    # AppBar minimal
    # ============================================================
    async def go_settings(e):
        await page.push_route("/settings")

    appbar = ft.AppBar(
        title=ft.Container(),
        bgcolor=C.bg,
        elevation=0,
        actions=[
            ft.IconButton(
                icon=ft.Icons.TUNE_ROUNDED,
                icon_color=C.text_muted, icon_size=20,
                on_click=go_settings,
            ),
            ft.Container(width=8),
        ],
    )

    # ============================================================
    # Assemblage
    # ============================================================
    view = ft.View(
        route="/", padding=0, bgcolor=C.bg, scroll=ft.ScrollMode.AUTO,
    )
    view.appbar = appbar
    view.navigation_bar = build_navbar(page, selected=0)

    view.controls = [
        T.page_root(
            ft.Container(
                padding=ft.Padding(left=20, top=8, right=20, bottom=24),
                content=ft.Column(
                    spacing=18,
                    controls=[
                        hero,
                        market_card,
                        grid,
                        T.section_header("Prochains rendez-vous"),
                        next_rdv_col,
                    ],
                ),
            )
        ),
    ]

    # Lancer les chargements en parallèle
    for fn in (load_market, load_bourse_mini, load_mails_count,
               load_rdv, load_docs, load_next_rdv):
        threading.Thread(target=fn, daemon=True).start()

    return view