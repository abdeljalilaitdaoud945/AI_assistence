"""
Vue Bourse — Arc style + sélecteur de marchés (Casablanca / Wall Street /
Paris / Tadawul / Crypto) + watchlist + modal détail enrichi
(52 sem high/low, market cap, PE, EPS, dividende, secteur…).
"""

import json
import threading

import flet as ft

from vues import theme as T
from vues.theme import C, FONT
from vues.navbar import build_navbar, nav_index_for
from services.stock_service import (
    MARKETS,
    fetch_quote,
    get_market_indices,
    get_market_stocks,
    get_stock_data,
    get_stock_history,
    search_symbol,
    fmt_number,
)

WATCHLIST_KEY = "stock_watchlist"
DEFAULT_WATCHLIST = ["AAPL", "MSFT", "TSLA", "NVDA"]


# =====================================================
#  Helpers de formatage
# =====================================================

def _change_color(pct):
    if pct is None:
        return C.text_subtle
    return C.success if pct >= 0 else C.danger


def _price_text(d):
    if d.get("error") or not d.get("price"):
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


# =====================================================
#  Row d'un titre
# =====================================================

def stock_row(d, on_click=None, show_remove=False, on_remove=None,
              show_spark=True):
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

    middle = []
    if show_spark:
        try:
            hist = get_stock_history(d["symbol"], "1mo")
            if hist and len(hist) >= 2:
                middle.append(
                    T.sparkline(hist, color=color, width=90, height=36,
                                fill_below=False)
                )
        except Exception:
            pass

    row_controls = [left] + middle + [right]

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
            spacing=12, controls=row_controls,
        ),
    )


# =====================================================
#  Pilule de marché (Casablanca / Wall Street / …)
# =====================================================

def market_pill(market_id, name, flag, active, on_click):
    return ft.Container(
        padding=ft.Padding(left=12, top=8, right=12, bottom=8),
        border_radius=999,
        bgcolor=C.accent_strong if active else C.bg_subtle,
        border=ft.Border(
            top=ft.BorderSide(1, C.accent_strong if active else C.border),
            bottom=ft.BorderSide(1, C.accent_strong if active else C.border),
            left=ft.BorderSide(1, C.accent_strong if active else C.border),
            right=ft.BorderSide(1, C.accent_strong if active else C.border),
        ),
        ink=True,
        on_click=lambda e, mid=market_id: on_click(mid),
        content=ft.Row(
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(flag, size=FONT.body),
                ft.Text(name, size=FONT.small,
                        color="#FFFFFF" if active else C.text_muted,
                        weight=ft.FontWeight.W_700 if active else ft.FontWeight.W_500),
            ],
        ),
    )


# =====================================================
#  Build
# =====================================================

def build(page: ft.Page) -> ft.View:

    prefs = ft.SharedPreferences()
    state = {
        "watchlist": list(DEFAULT_WATCHLIST),
        "active_market": None,  # None = "Indices", sinon market_id
    }

    # ---- Conteneurs ----
    market_pills_row = ft.Row(spacing=8, wrap=True, run_spacing=8)
    stocks_col = ft.Column(spacing=8)
    watchlist_col = ft.Column(spacing=8)
    search_results_col = ft.Column(spacing=8, visible=False)
    loading_stocks = ft.ProgressRing(width=14, height=14, stroke_width=2,
                                     color=C.accent, visible=True)
    loading_watch = ft.ProgressRing(width=14, height=14, stroke_width=2,
                                    color=C.accent, visible=False)

    # =================================================
    #  MODAL DÉTAIL — riche (week52, market_cap, PE, …)
    # =================================================
    def open_detail(symbol):
        body_holder = ft.Container(
            width=340, height=380,
            alignment=ft.Alignment.CENTER,
            content=ft.ProgressRing(color=C.accent),
        )

        def _close(e=None):
            page.pop_dialog()

        dialog = ft.AlertDialog(
            modal=False, bgcolor=C.bg_elevated,
            title=ft.Text(symbol, color=C.text,
                          weight=ft.FontWeight.W_700, size=FONT.h2),
            content=body_holder,
            actions=[ft.TextButton("Fermer", on_click=_close)],
        )
        page.show_dialog(dialog)

        def fetch():
            q = fetch_quote(symbol)
            hist = get_stock_history(symbol, "1mo")
            color = _change_color(q.change_pct if not q.error else None)

            if q.error:
                body_holder.content = ft.Text(f"Erreur : {q.error}",
                                              color=C.danger)
                page.update()
                return

            sign = "+" if q.is_up else ""

            # Bloc grand prix + variation
            big_price = ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(_price_text({"price": q.price,
                                         "currency": q.currency}),
                            size=FONT.display,
                            weight=ft.FontWeight.W_700, color=C.text),
                    T.accent_chip(f"{sign}{q.change_pct:.2f}%", color=color),
                ],
            )

            # Bloc range jour + 52 sem
            day_range = ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(f"{q.day_low:.2f}", color=C.text_subtle,
                            size=FONT.micro),
                    ft.Container(
                        expand=True,
                        margin=ft.Margin(left=8, top=0, right=8, bottom=0),
                        height=4,
                        border_radius=999,
                        bgcolor=C.bg_subtle,
                    ),
                    ft.Text(f"{q.day_high:.2f}", color=C.text_subtle,
                            size=FONT.micro),
                ],
            )

            # Métriques fondamentales
            def metric(label, value):
                return ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text(label, size=FONT.micro, color=C.text_subtle),
                        ft.Text(value, size=FONT.small, color=C.text,
                                weight=ft.FontWeight.W_600),
                    ],
                )

            metrics_grid = ft.Row(
                spacing=20, wrap=True, run_spacing=10,
                controls=[
                    metric("Cap. marché",
                           fmt_number(q.market_cap) + (f" {q.currency}"
                                                       if q.market_cap else "")),
                    metric("P / E",
                           f"{q.pe_ratio:.2f}" if q.pe_ratio else "—"),
                    metric("EPS",
                           f"{q.eps:.2f}" if q.eps else "—"),
                    metric("Dividende",
                           f"{q.dividend_yield*100:.2f}%"
                           if q.dividend_yield else "—"),
                    metric("Beta",
                           f"{q.beta:.2f}" if q.beta else "—"),
                    metric("Volume", fmt_number(q.volume, 0)),
                ],
            )

            body_holder.content = ft.Column(
                spacing=14, tight=True,
                controls=[
                    ft.Text(q.name, size=FONT.h3, color=C.text,
                            weight=ft.FontWeight.W_600,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS),
                    big_price,
                    ft.Text(f"Clôture préc. : {q.previous_close} {q.currency}",
                            size=FONT.micro, color=C.text_subtle),

                    # Graphique
                    ft.Text("30 derniers jours", size=FONT.micro,
                            color=C.text_subtle),
                    T.sparkline(hist, color=color, width=320, height=110),

                    # Range jour
                    ft.Container(height=4),
                    ft.Text("Range du jour", size=FONT.micro,
                            color=C.text_subtle),
                    day_range,

                    # Range 52 semaines
                    ft.Container(height=4),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("52 sem.", size=FONT.micro,
                                    color=C.text_subtle),
                            ft.Text(f"{q.week52_position_pct:.0f}%",
                                    size=FONT.micro,
                                    color=C.accent,
                                    weight=ft.FontWeight.W_700),
                        ],
                    ),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(f"{q.week52_low:.2f}",
                                    color=C.text_subtle, size=FONT.micro),
                            ft.Text(f"{q.week52_high:.2f}",
                                    color=C.text_subtle, size=FONT.micro),
                        ],
                    ),

                    ft.Container(height=8),
                    T.divider(),
                    ft.Container(height=4),
                    metrics_grid,

                    ft.Container(height=8),
                    ft.Row(spacing=8, wrap=True, run_spacing=6,
                           controls=[
                               T.chip(q.sector or "—"),
                               T.chip(q.exchange or "—"),
                           ]),
                ],
            )
            page.update()

        threading.Thread(target=fetch, daemon=True).start()

    # =================================================
    #  Watchlist
    # =================================================
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

    # =================================================
    #  Refresh stocks (par marché ou indices)
    # =================================================
    def refresh_stocks():
        loading_stocks.visible = True
        stocks_col.controls.clear()
        page.update()

        def fetch():
            market_id = state["active_market"]
            if market_id is None:
                data = get_market_indices()
            else:
                data = get_market_stocks(market_id)
            stocks_col.controls.clear()
            for d in data:
                stocks_col.controls.append(
                    stock_row(d, on_click=open_detail,
                              show_remove=False, show_spark=True)
                )
            loading_stocks.visible = False
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

    # =================================================
    #  Sélecteur de marché (pilules)
    # =================================================
    def render_market_pills():
        market_pills_row.controls.clear()
        # Pilule "Indices" (toutes les indices monde + crypto par défaut)
        market_pills_row.controls.append(
            market_pill(
                None, "Indices", "🌐",
                active=(state["active_market"] is None),
                on_click=select_market,
            )
        )
        for mid, market in MARKETS.items():
            market_pills_row.controls.append(
                market_pill(
                    mid, market["name"], market["flag"],
                    active=(state["active_market"] == mid),
                    on_click=select_market,
                )
            )

    def select_market(market_id):
        state["active_market"] = market_id
        render_market_pills()
        refresh_stocks()

    # =================================================
    #  Recherche
    # =================================================
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

    # =================================================
    #  AppBar
    # =================================================
    refresh_btn = ft.IconButton(
        icon=ft.Icons.REFRESH_ROUNDED,
        icon_color=C.text_muted, icon_size=18,
        tooltip="Rafraîchir",
        on_click=lambda e: (refresh_stocks(), refresh_watchlist()),
    )

    view = ft.View(
        route="/bourse", padding=0, bgcolor=C.bg,
        scroll=ft.ScrollMode.AUTO,
    )
    view.navigation_bar = build_navbar(page, selected=nav_index_for("/bourse"))
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
                    # Section sélecteur de marchés
                    market_pills_row,
                    T.section_header("Cotations", action=loading_stocks),
                    stocks_col,
                    T.section_header("Mes favoris", action=loading_watch),
                    watchlist_col,
                ],
            ),
        ),
    ]

    # Initialisation
    render_market_pills()
    refresh_stocks()
    page.run_task(load_watchlist_from_prefs)

    return view