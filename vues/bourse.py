"""
Vue Bourse — adaptée au theme Arc-style.

Sparkline via flet.canvas, AlertDialog créés à la volée (jamais ouverts 2x),
page.show_dialog / page.pop_dialog (API Flet 0.85.1 réelle).
"""

import json
import threading

import flet as ft

from vues import theme as T
from vues.theme import C, FONT
from vues.navbar import build_navbar
from services.stock_service import (
    get_market_indices,
    get_stock_data,
    get_stock_history,
    search_symbol,
)

WATCHLIST_KEY = "stock_watchlist"
DEFAULT_WATCHLIST = ["AAPL", "MSFT", "TSLA", "NVDA"]


def _change_color(pct):
    if pct is None:
        return C.text_subtle
    return C.success if pct >= 0 else C.danger


def _price_text(d):
    if d.get("error") or d.get("price") is None:
        return "—"
    p = d["price"]
    cur = d.get("currency", "")
    if p >= 100:
        return f"{p:,.2f} {cur}"
    elif p >= 1:
        return f"{p:.4f} {cur}"
    else:
        return f"{p:.6f} {cur}"


def _change_text(d):
    if d.get("error") or d.get("change_percent") is None:
        return "—"
    sign = "+" if d["change_percent"] >= 0 else ""
    return f"{sign}{d['change_percent']:.2f}%"


def stock_row(d, on_click=None, show_remove=False, on_remove=None,
              show_spark=True):
    """Ligne d'une action / indice : nom + sparkline + prix + variation."""
    pct = d.get("change_percent")
    color = _change_color(pct)
    title = d.get("display_name") or d.get("name") or d.get("symbol")

    left = ft.Column(
        spacing=2, expand=True,
        controls=[
            ft.Text(title, size=FONT.body, weight=ft.FontWeight.W_600,
                    color=C.text, max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS),
            ft.Text(d["symbol"], size=FONT.micro, color=C.text_subtle),
        ],
    )

    right = ft.Column(
        spacing=2, horizontal_alignment=ft.CrossAxisAlignment.END,
        controls=[
            ft.Text(_price_text(d), size=FONT.body,
                    weight=ft.FontWeight.W_700, color=C.text),
            ft.Text(_change_text(d), size=FONT.micro, color=color,
                    weight=ft.FontWeight.W_600),
        ],
    )

    middle_widgets = []
    if show_spark:
        try:
            hist = get_stock_history(d["symbol"], "1mo")
            if hist and len(hist) >= 2:
                middle_widgets.append(
                    T.sparkline(hist, color=color, width=90, height=36,
                                fill_below=False)
                )
        except Exception:
            pass

    row_controls = [left]
    if middle_widgets:
        row_controls.extend(middle_widgets)
    row_controls.append(right)

    if show_remove and on_remove is not None:
        row_controls.append(
            ft.IconButton(
                icon=ft.Icons.STAR_ROUNDED,
                icon_color=C.warning, icon_size=18,
                tooltip="Retirer des favoris",
                on_click=lambda e, s=d["symbol"]: on_remove(s),
            )
        )

    return T.card(
        on_click=(lambda e: on_click(d["symbol"])) if on_click else None,
        padding=14,
        content=ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
            controls=row_controls,
        ),
    )


def build(page: ft.Page) -> ft.View:

    prefs = ft.SharedPreferences()
    state = {"watchlist": list(DEFAULT_WATCHLIST)}

    # ---- Conteneurs ----
    indices_col = ft.Column(spacing=8)
    watchlist_col = ft.Column(spacing=8)
    search_results_col = ft.Column(spacing=8, visible=False)
    loading_indices = ft.ProgressRing(width=14, height=14, stroke_width=2,
                                      color=C.accent, visible=True)
    loading_watch = ft.ProgressRing(width=14, height=14, stroke_width=2,
                                    color=C.accent, visible=False)

    # =====================================================
    # Modal détail
    # =====================================================
    def open_detail(symbol):
        body_holder = ft.Container(
            width=320, height=260,
            alignment=ft.Alignment.CENTER,
            content=ft.ProgressRing(color=C.accent),
        )

        def _close(e=None):
            page.pop_dialog()

        dialog = ft.AlertDialog(
            modal=False,
            bgcolor=C.bg_elevated,
            title=ft.Text(symbol, color=C.text,
                          weight=ft.FontWeight.W_700, size=FONT.h2),
            content=body_holder,
            actions=[ft.TextButton("Fermer", on_click=_close)],
        )
        page.show_dialog(dialog)

        def fetch():
            d = get_stock_data(symbol)
            hist = get_stock_history(symbol, "1mo")
            color = _change_color(d.get("change_percent"))

            if d.get("error"):
                body_holder.content = ft.Text(f"Erreur : {d['error']}",
                                              color=C.danger)
            else:
                sign = "+" if (d.get("change_percent") or 0) >= 0 else ""
                body_holder.content = ft.Column(
                    spacing=14, tight=True,
                    controls=[
                        ft.Text(d["name"], size=FONT.h3, color=C.text,
                                weight=ft.FontWeight.W_600),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(_price_text(d), size=FONT.display,
                                        weight=ft.FontWeight.W_700,
                                        color=C.text),
                                T.accent_chip(
                                    f"{sign}{d['change_percent']:.2f}%",
                                    color=color,
                                ),
                            ],
                        ),
                        ft.Text(
                            f"Clôture précédente : "
                            f"{d['previous_close']} {d['currency']}",
                            size=FONT.small, color=C.text_muted,
                        ),
                        ft.Container(height=4),
                        ft.Text("30 derniers jours", size=FONT.micro,
                                color=C.text_subtle),
                        T.sparkline(hist, color=color,
                                    width=300, height=130),
                    ],
                )
            page.update()

        threading.Thread(target=fetch, daemon=True).start()

    # =====================================================
    # Watchlist persistée
    # =====================================================
    async def load_watchlist_from_prefs():
        try:
            raw = await prefs.get(WATCHLIST_KEY)
            if raw:
                data = json.loads(raw)
                if isinstance(data, list) and data:
                    state["watchlist"] = data
        except Exception as ex:
            print(f"[bourse] load watchlist error: {ex}")
        refresh_watchlist()

    async def save_watchlist_async():
        try:
            await prefs.set(WATCHLIST_KEY, json.dumps(state["watchlist"]))
        except Exception as ex:
            print(f"[bourse] save error: {ex}")

    def save_watchlist():
        page.run_task(save_watchlist_async)

    def remove_from_watchlist(symbol):
        if symbol in state["watchlist"]:
            state["watchlist"].remove(symbol)
            save_watchlist()
            refresh_watchlist()

    def add_to_watchlist(symbol):
        symbol = (symbol or "").upper().strip()
        if symbol and symbol not in state["watchlist"]:
            state["watchlist"].append(symbol)
            save_watchlist()
            refresh_watchlist()
            page.show_dialog(
                ft.SnackBar(ft.Text(f"{symbol} ajouté aux favoris"),
                            duration=1800)
            )

    # =====================================================
    # Refresh
    # =====================================================
    def refresh_indices():
        loading_indices.visible = True
        page.update()

        def fetch():
            data = get_market_indices()
            indices_col.controls.clear()
            for d in data:
                indices_col.controls.append(
                    stock_row(d, on_click=open_detail, show_spark=True)
                )
            loading_indices.visible = False
            page.update()

        threading.Thread(target=fetch, daemon=True).start()

    def refresh_watchlist():
        loading_watch.visible = True
        watchlist_col.controls.clear()
        if not state["watchlist"]:
            watchlist_col.controls.append(
                ft.Container(
                    padding=20, alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        "Aucun favori. Cherche une action pour l'ajouter.",
                        color=C.text_subtle, italic=True, size=FONT.small,
                    ),
                )
            )
            loading_watch.visible = False
            page.update()
            return
        page.update()

        def fetch():
            for sym in list(state["watchlist"]):
                d = get_stock_data(sym)
                watchlist_col.controls.append(
                    stock_row(d, on_click=open_detail,
                              show_remove=True, on_remove=remove_from_watchlist,
                              show_spark=True)
                )
                page.update()
            loading_watch.visible = False
            page.update()

        threading.Thread(target=fetch, daemon=True).start()

    # =====================================================
    # Recherche
    # =====================================================
    search_field = ft.TextField(
        hint_text="Rechercher (Apple, BTC, TSLA…)",
        border_radius=14,
        bgcolor=C.bg_subtle,
        border_color=C.border,
        focused_border_color=C.accent,
        color=C.text,
        hint_style=ft.TextStyle(color=C.text_subtle),
        text_size=FONT.body,
        content_padding=ft.Padding(left=14, top=12, right=14, bottom=12),
    )

    def do_search(e=None):
        q = (search_field.value or "").strip()
        if not q:
            search_results_col.visible = False
            page.update()
            return
        search_results_col.controls.clear()
        search_results_col.controls.append(
            ft.Row(spacing=8, controls=[
                ft.ProgressRing(width=14, height=14,
                                stroke_width=2, color=C.accent),
                ft.Text("Recherche…", color=C.text_subtle, size=FONT.small),
            ])
        )
        search_results_col.visible = True
        page.update()

        def fetch():
            res = search_symbol(q)
            search_results_col.controls.clear()
            if not res:
                search_results_col.controls.append(
                    ft.Text(f"Aucun résultat pour '{q}'.",
                            color=C.text_subtle, size=FONT.small, italic=True)
                )
            else:
                for r in res:
                    sym = r["symbol"]
                    search_results_col.controls.append(
                        T.card(
                            on_click=lambda e, s=sym: open_detail(s),
                            padding=12,
                            content=ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Column(
                                        expand=True, spacing=2,
                                        controls=[
                                            ft.Text(r["name"], color=C.text,
                                                    size=FONT.body,
                                                    weight=ft.FontWeight.W_600,
                                                    max_lines=1,
                                                    overflow=ft.TextOverflow.ELLIPSIS),
                                            ft.Text(
                                                f"{sym} • {r['exchange']}",
                                                color=C.text_subtle,
                                                size=FONT.micro,
                                            ),
                                        ],
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.ADD_ROUNDED,
                                        icon_color=C.accent,
                                        tooltip="Ajouter aux favoris",
                                        on_click=lambda e, s=sym: add_to_watchlist(s),
                                    ),
                                ],
                            ),
                        )
                    )
            page.update()

        threading.Thread(target=fetch, daemon=True).start()

    search_field.on_submit = do_search

    search_row = ft.Row(
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(content=search_field, expand=True),
            ft.IconButton(
                icon=ft.Icons.ARROW_FORWARD_ROUNDED,
                icon_color="#FFFFFF",
                bgcolor=C.accent_strong,
                on_click=do_search,
            ),
        ],
    )

    # =====================================================
    # AppBar
    # =====================================================
    refresh_btn = ft.IconButton(
        icon=ft.Icons.REFRESH_ROUNDED,
        icon_color=C.text_muted,
        icon_size=18,
        tooltip="Rafraîchir",
        on_click=lambda e: (refresh_indices(), refresh_watchlist()),
    )

    view = ft.View(
        route="/bourse", padding=0, bgcolor=C.bg,
        scroll=ft.ScrollMode.AUTO,
    )

    view.navigation_bar = build_navbar(page, selected=0)
    view.appbar = T.appbar("Bourse", back_route="/", page=page,
                           actions=[refresh_btn, ft.Container(width=8)])

    view.controls = [
        ft.Container(
            padding=ft.Padding(left=20, top=8, right=20, bottom=24),
            content=ft.Column(
                spacing=14,
                controls=[
                    search_row,
                    search_results_col,
                    T.section_header("Marchés", action=loading_indices),
                    indices_col,
                    T.section_header("Mes favoris", action=loading_watch),
                    watchlist_col,
                ],
            ),
        )
    ]

    refresh_indices()
    page.run_task(load_watchlist_from_prefs)

    return view