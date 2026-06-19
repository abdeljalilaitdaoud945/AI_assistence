"""
Home — refonte ERP-first
  - Hero header (date + salutation)
  - Bloc ERP HERO pleine largeur (CA YTD, jauge objectif, KPI inline, alertes)
  - Grid de 5 cards (Affaires, Mails, RDV, Documents, Bourse — démotée)
  - Section "Prochains rendez-vous"

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
    months = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
              "août", "septembre", "octobre", "novembre", "décembre"]
    days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    date_str = f"{days[now.weekday()]} {now.day} {months[now.month - 1]} {now.year}"

    hero = ft.Container(
        padding=ft.Padding(left=0, top=8, right=0, bottom=20),
        content=ft.Column(
            spacing=4,
            controls=[
                ft.Text(
                    date_str.capitalize(),
                    size=FONT.small,
                    color=C.text_subtle,
                    weight=ft.FontWeight.W_500,
                ),
                ft.Text(
                    name,
                    size=FONT.display,
                    color=C.text,
                    weight=ft.FontWeight.W_700,
                ),
            ],
        ),
    )

    # ============================================================
    # ERP HERO — pleine largeur, dominant
    # ============================================================
    erp_label = ft.Text(
        "Pilotage de la performance",
        size=FONT.small,
        color=C.text_muted,
        weight=ft.FontWeight.W_600,
    )
    erp_subtitle = ft.Text(
        "Données SI consolidées",
        size=FONT.micro,
        color=C.text_subtle,
    )

    erp_ca_big = ft.Text(
        "—",
        size=FONT.display + 4,
        color=C.text,
        weight=ft.FontWeight.W_700,
    )
    erp_ca_unit = ft.Text(
        "MAD",
        size=FONT.body,
        color=C.text_subtle,
        weight=ft.FontWeight.W_500,
    )
    erp_obj_caption = ft.Text(
        "—",
        size=FONT.small,
        color=C.text_subtle,
        weight=ft.FontWeight.W_500,
    )

    erp_status_chip = T.accent_chip("Chargement…")

    # Jauge de progression CA realisé / objectif (responsive via expand)
    erp_progress_fill = ft.Container(
        expand=1,  # ajusté dynamiquement dans load_erp
        height=8,
        bgcolor=C.accent,
        border_radius=4,
    )
    erp_progress_rest = ft.Container(
        expand=99,  # ajusté dynamiquement dans load_erp
        height=8,
        bgcolor=ft.Colors.with_opacity(0.08, C.text),
        border_radius=4,
    )
    erp_progress_track = ft.Container(
        height=8,
        border_radius=4,
        content=ft.Row(
            spacing=2,
            controls=[erp_progress_fill, erp_progress_rest],
        ),
    )
    erp_progress_label = ft.Text(
        "—",
        size=FONT.micro,
        color=C.text_subtle,
        weight=ft.FontWeight.W_500,
    )

    # Petits KPI inline (Marge, Trésorerie, Factures, Occupation)
    erp_kpi_marge_val = ft.Text("—", size=FONT.h3, color=C.text, weight=ft.FontWeight.W_700)
    erp_kpi_treso_val = ft.Text("—", size=FONT.h3, color=C.text, weight=ft.FontWeight.W_700)
    erp_kpi_facts_val = ft.Text("—", size=FONT.h3, color=C.text, weight=ft.FontWeight.W_700)
    erp_kpi_team_val = ft.Text("—", size=FONT.h3, color=C.text, weight=ft.FontWeight.W_700)

    def _kpi_box(label_text, value_widget):
        return ft.Container(
            expand=True,
            padding=ft.Padding(left=12, top=10, right=12, bottom=10),
            border_radius=12,
            bgcolor=ft.Colors.with_opacity(0.04, C.text),
            border=ft.Border(
                top=ft.BorderSide(1, C.border_subtle),
                bottom=ft.BorderSide(1, C.border_subtle),
                left=ft.BorderSide(1, C.border_subtle),
                right=ft.BorderSide(1, C.border_subtle),
            ),
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Text(
                        label_text,
                        size=FONT.micro,
                        color=C.text_subtle,
                        weight=ft.FontWeight.W_500,
                    ),
                    value_widget,
                ],
            ),
        )

    erp_kpi_row = ft.ResponsiveRow(
        spacing=10,
        run_spacing=10,
        controls=[
            ft.Container(col={"xs": 6, "md": 3}, content=_kpi_box("Marge", erp_kpi_marge_val)),
            ft.Container(col={"xs": 6, "md": 3}, content=_kpi_box("Trésorerie", erp_kpi_treso_val)),
            ft.Container(col={"xs": 6, "md": 3}, content=_kpi_box("Impayés", erp_kpi_facts_val)),
            ft.Container(col={"xs": 6, "md": 3}, content=_kpi_box("Occupation", erp_kpi_team_val)),
        ],
    )

    # Bandeau alertes (visible seulement si problème)
    erp_alert_banner = ft.Container(visible=False)

    async def go_erp(e):
        await page.push_route("/erp")

    erp_open_btn = ft.Container(
        on_click=go_erp,
        ink=True,
        padding=ft.Padding(left=14, top=8, right=14, bottom=8),
        border_radius=999,
        bgcolor=ft.Colors.with_opacity(0.12, C.accent),
        content=ft.Row(
            spacing=6,
            tight=True,
            controls=[
                ft.Text(
                    "Ouvrir le pilotage",
                    size=FONT.small,
                    color=C.accent,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Icon(ft.Icons.ARROW_FORWARD_ROUNDED, color=C.accent, size=14),
            ],
        ),
    )

    erp_hero_card = T.card(
        on_click=go_erp,
        padding=22,
        content=ft.Column(
            spacing=18,
            controls=[
                # Ligne titre + CTA
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(
                            spacing=10,
                            controls=[
                                ft.Container(
                                    width=32,
                                    height=32,
                                    border_radius=10,
                                    bgcolor=ft.Colors.with_opacity(0.12, C.accent),
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Icon(
                                        ft.Icons.INSIGHTS_ROUNDED,
                                        color=C.accent,
                                        size=18,
                                    ),
                                ),
                                ft.Column(
                                    spacing=0,
                                    controls=[erp_label, erp_subtitle],
                                ),
                            ],
                        ),
                        erp_open_btn,
                    ],
                ),
                # Grand chiffre CA
                ft.Column(
                    spacing=6,
                    controls=[
                        ft.Row(
                            vertical_alignment=ft.CrossAxisAlignment.END,
                            spacing=8,
                            controls=[
                                erp_ca_big,
                                ft.Container(
                                    padding=ft.Padding(left=0, top=0, right=0, bottom=10),
                                    content=erp_ca_unit,
                                ),
                                ft.Container(width=8),
                                erp_status_chip,
                            ],
                        ),
                        ft.Text(
                            "Chiffre d'affaires YTD",
                            size=FONT.small,
                            color=C.text_muted,
                            weight=ft.FontWeight.W_500,
                        ),
                    ],
                ),
                # Jauge objectif
                ft.Column(
                    spacing=6,
                    controls=[
                        erp_progress_track,
                        erp_progress_label,
                    ],
                ),
                # Bandeau alertes
                erp_alert_banner,
                # KPI inline
                erp_kpi_row,
            ],
        ),
    )

    def _fmt_money(n):
        if n is None:
            return "—"
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n / 1_000:.0f}k"
        return str(int(n))

    def load_erp():
        try:
            from services.erp_service import get_erp_data
            data = get_erp_data() or {}
            fin = data.get("finance", {}) or {}
            ops = data.get("operations", {}) or {}

            ca = fin.get("chiffre_affaires", {}) or {}
            marge = fin.get("marge_globale", {}) or {}
            treso = fin.get("tresorerie", {}) or {}
            facts = fin.get("factures_impayees", {}) or {}

            realise = ca.get("realise_ytd") or ca.get("realise") or 0
            objectif = ca.get("objectif_ytd") or ca.get("objectif") or 0
            tendance = ca.get("tendance_mensuelle", "")

            erp_ca_big.value = _fmt_money(realise)
            erp_ca_unit.value = ca.get("devise", "MAD")
            erp_obj_caption.value = (
                f"Objectif {_fmt_money(objectif)} {ca.get('devise', 'MAD')}"
                if objectif else ""
            )

            # Chip tendance
            if tendance:
                low = tendance.lower()
                if "hausse" in low or "+" in tendance:
                    chip_color = C.success
                elif "baisse" in low or "-" in tendance:
                    chip_color = C.danger
                else:
                    chip_color = C.warning
                erp_status_chip.bgcolor = ft.Colors.with_opacity(0.15, chip_color)
                erp_status_chip.content.color = chip_color
                erp_status_chip.content.value = tendance
            else:
                erp_status_chip.content.value = "—"

            # Jauge progression (responsive via expand ratios)
            if objectif and objectif > 0:
                ratio = max(0.0, min(1.0, realise / objectif))
                pct = ratio * 100
                # 100 unités de granularité — min 1 pour éviter expand=0
                fill_units = max(1, int(round(pct)))
                rest_units = max(1, 100 - fill_units)
                erp_progress_fill.expand = fill_units
                erp_progress_rest.expand = rest_units
                if ratio >= 0.9:
                    erp_progress_fill.bgcolor = C.success
                elif ratio >= 0.6:
                    erp_progress_fill.bgcolor = C.warning
                else:
                    erp_progress_fill.bgcolor = C.danger
                erp_progress_label.value = (
                    f"{pct:.0f}% de l'objectif atteint  ·  Reste {_fmt_money(objectif - realise)} "
                    f"{ca.get('devise', 'MAD')}"
                )
            else:
                erp_progress_label.value = ""

            # KPI Marge
            m_real = marge.get("realise", 0)
            m_obj = marge.get("objectif", 0)
            erp_kpi_marge_val.value = f"{m_real}%"
            erp_kpi_marge_val.color = C.danger if (m_obj and m_real < m_obj) else C.success

            # KPI Trésorerie
            t_disp = treso.get("disponible", 0)
            t_seuil = treso.get("seuil_alerte", 0)
            erp_kpi_treso_val.value = f"{_fmt_money(t_disp)}"
            if t_seuil and t_disp < t_seuil:
                erp_kpi_treso_val.color = C.danger
            else:
                erp_kpi_treso_val.color = C.text

            # KPI Factures impayées
            f_tot = facts.get("montant_total", 0)
            erp_kpi_facts_val.value = f"{_fmt_money(f_tot)}"
            erp_kpi_facts_val.color = C.warning if f_tot > 0 else C.text

            # KPI Occupation équipes
            occup = ops.get("taux_occupation_equipes", 0)
            erp_kpi_team_val.value = f"{occup:.0f}%" if isinstance(occup, (int, float)) else "—"
            if isinstance(occup, (int, float)):
                if occup >= 90:
                    erp_kpi_team_val.color = C.danger  # surchauffe
                elif occup >= 75:
                    erp_kpi_team_val.color = C.success
                else:
                    erp_kpi_team_val.color = C.warning

            # Bandeau alertes intelligent
            alerts = []
            if treso.get("statut", "").lower() == "critique" or (t_seuil and t_disp < t_seuil):
                alerts.append(("Trésorerie sous le seuil critique", ft.Icons.WARNING_AMBER_ROUNDED, C.danger))
            retards = ops.get("projets_en_retard", []) or []
            if retards:
                total_impact = sum((r.get("impact_estime", 0) or 0) for r in retards)
                alerts.append((
                    f"{len(retards)} projets en retard  ·  Impact {_fmt_money(total_impact)} "
                    f"{ca.get('devise', 'MAD')}",
                    ft.Icons.SCHEDULE_ROUNDED,
                    C.warning,
                ))

            if alerts:
                erp_alert_banner.content = ft.Column(
                    spacing=8,
                    controls=[
                        ft.Container(
                            padding=ft.Padding(left=12, top=10, right=12, bottom=10),
                            border_radius=10,
                            bgcolor=ft.Colors.with_opacity(0.10, col),
                            border=ft.Border(
                                top=ft.BorderSide(1, ft.Colors.with_opacity(0.25, col)),
                                bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.25, col)),
                                left=ft.BorderSide(3, col),
                                right=ft.BorderSide(1, ft.Colors.with_opacity(0.25, col)),
                            ),
                            content=ft.Row(
                                spacing=10,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Icon(icon, color=col, size=16),
                                    ft.Text(
                                        msg,
                                        size=FONT.small,
                                        color=C.text,
                                        weight=ft.FontWeight.W_500,
                                        expand=True,
                                    ),
                                ],
                            ),
                        )
                        for (msg, icon, col) in alerts
                    ],
                )
                erp_alert_banner.visible = True
            else:
                erp_alert_banner.visible = False

            page.update()
        except Exception as e:
            erp_ca_big.value = "Erreur"
            erp_ca_unit.value = ""
            erp_obj_caption.value = str(e)[:60]
            page.update()

    # ============================================================
    # GRID 5 cards (Affaires, Mails, RDV, Documents, Bourse)
    # ============================================================

    # ---- Mails — ring chart ----
    mails_ring_holder = ft.Container(
        height=84,
        alignment=ft.Alignment.CENTER,
        content=ft.ProgressRing(width=14, height=14, stroke_width=2, color=C.accent),
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
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.Icon(ft.Icons.MAIL_OUTLINE_ROUNDED, color=C.accent, size=14),
                                ft.Text(
                                    "Mails",
                                    color=C.text_muted,
                                    size=FONT.small,
                                    weight=ft.FontWeight.W_500,
                                ),
                            ],
                        ),
                        ft.Icon(ft.Icons.ARROW_OUTWARD_ROUNDED, color=C.text_subtle, size=14),
                    ],
                ),
                ft.Container(alignment=ft.Alignment.CENTER, content=mails_ring_holder),
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
                value=unread,
                total=max(total, 1),
                color=C.accent,
                size=84,
                stroke=7,
                label=str(unread),
            )
            if unread == 0:
                mails_sub.value = "boîte à jour"
            else:
                mails_sub.value = f"{unread} non lu" + ("s" if unread > 1 else "")
            page.update()
        except Exception:
            mails_ring_holder.content = ft.Text("—", color=C.text_subtle, size=FONT.small)
            mails_sub.value = "Erreur"
            page.update()

    # ---- RDV — dots timeline ----
    rdv_timeline_holder = ft.Container(
        height=84,
        alignment=ft.Alignment.CENTER,
        content=ft.ProgressRing(width=14, height=14, stroke_width=2, color=C.accent),
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
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.Icon(ft.Icons.EVENT_AVAILABLE_ROUNDED, color=C.accent, size=14),
                                ft.Text(
                                    "Rendez-vous",
                                    color=C.text_muted,
                                    size=FONT.small,
                                    weight=ft.FontWeight.W_500,
                                ),
                            ],
                        ),
                        ft.Icon(ft.Icons.ARROW_OUTWARD_ROUNDED, color=C.text_subtle, size=14),
                    ],
                ),
                rdv_timeline_holder,
                rdv_sub,
            ],
        ),
    )

    def _events_safe(max_results=4):
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
                    "Pas de RDV prévu",
                    color=C.text_subtle,
                    size=FONT.small,
                    italic=True,
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
                rdv_sub.value = f"{len(events)} à venir" if len(events) > 1 else "1 à venir"
            page.update()
        except Exception:
            rdv_timeline_holder.content = ft.Text("—", color=C.text_subtle, size=FONT.small)
            rdv_sub.value = "Erreur"
            page.update()

    # ---- Documents ----
    docs_count = ft.Text("—", size=FONT.display, color=C.text, weight=ft.FontWeight.W_700)
    docs_last = ft.Text(
        "—",
        size=FONT.micro,
        color=C.text_subtle,
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
    )
    docs_caption = ft.Text(
        "analysés",
        size=FONT.small,
        color=C.text_muted,
        weight=ft.FontWeight.W_500,
    )

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
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.Icon(ft.Icons.DESCRIPTION_OUTLINED, color=C.accent, size=14),
                                ft.Text(
                                    "Documents",
                                    color=C.text_muted,
                                    size=FONT.small,
                                    weight=ft.FontWeight.W_500,
                                ),
                            ],
                        ),
                        ft.Icon(ft.Icons.ARROW_OUTWARD_ROUNDED, color=C.text_subtle, size=14),
                    ],
                ),
                ft.Container(height=8),
                docs_count,
                docs_caption,
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

    # ---- Affaires ----
    biz_count = ft.Text("—", size=FONT.display, color=C.text, weight=ft.FontWeight.W_700)
    biz_sub = ft.Text("—", size=FONT.micro, color=C.text_subtle)

    async def go_biz(e):
        await page.push_route("/business")

    biz_card = T.card(
        on_click=go_biz,
        padding=16,
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.Icon(ft.Icons.BUSINESS_CENTER_OUTLINED, color=C.accent, size=14),
                                ft.Text(
                                    "Affaires",
                                    color=C.text_muted,
                                    size=FONT.small,
                                    weight=ft.FontWeight.W_500,
                                ),
                            ],
                        ),
                        ft.Icon(ft.Icons.ARROW_OUTWARD_ROUNDED, color=C.text_subtle, size=14),
                    ],
                ),
                ft.Container(height=4),
                biz_count,
                ft.Text(
                    "dossiers",
                    size=FONT.small,
                    color=C.text_muted,
                    weight=ft.FontWeight.W_500,
                ),
                ft.Container(height=2),
                biz_sub,
            ],
        ),
    )

    def load_biz():
        try:
            from services.business_tracker import list_deals, deals_needing_followup
            deals = list_deals()
            followup = deals_needing_followup(7)
            biz_count.value = str(len(deals))
            biz_sub.value = f"{len(followup)} à relancer" if followup else "à jour"
            page.update()
        except Exception:
            biz_count.value = "—"
            biz_sub.value = ""
            page.update()

    # ---- Bourse mini (Nasdaq) — DEMOTÉE en petite carte ----
    nasdaq_val = ft.Text("—", size=FONT.h3, color=C.text, weight=ft.FontWeight.W_700)
    nasdaq_chg = ft.Text(
        "—",
        size=FONT.small,
        color=C.text_subtle,
        weight=ft.FontWeight.W_600,
    )
    nasdaq_chart = ft.Container(
        height=52,
        content=ft.ProgressRing(width=12, height=12, stroke_width=2, color=C.accent),
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
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.Icon(ft.Icons.SHOW_CHART_ROUNDED, color=C.accent, size=14),
                                ft.Text(
                                    "Bourse",
                                    color=C.text_muted,
                                    size=FONT.small,
                                    weight=ft.FontWeight.W_500,
                                ),
                            ],
                        ),
                        ft.Icon(ft.Icons.ARROW_OUTWARD_ROUNDED, color=C.text_subtle, size=14),
                    ],
                ),
                nasdaq_val,
                nasdaq_chg,
                nasdaq_chart,
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
                nasdaq_chart.content = T.sparkline(hist, color=color, width=220, height=52)
            page.update()
        except Exception:
            nasdaq_val.value = "—"
            nasdaq_chg.value = "Erreur"
            page.update()

    # ============================================================
    # Grid 5 cards
    # ============================================================
    grid = ft.ResponsiveRow(
        spacing=12,
        run_spacing=12,
        controls=[
            ft.Container(col={"xs": 6, "md": 4}, content=biz_card),
            ft.Container(col={"xs": 6, "md": 4}, content=mails_card),
            ft.Container(col={"xs": 6, "md": 4}, content=rdv_card),
            ft.Container(col={"xs": 6, "md": 4}, content=docs_card),
            ft.Container(col={"xs": 6, "md": 4}, content=bourse_card),
        ],
    )

    # ============================================================
    # Section Prochains RDV
    # ============================================================
    next_rdv_col = ft.Column(spacing=8)
    next_rdv_col.controls.append(
        ft.Container(
            padding=20,
            alignment=ft.Alignment.CENTER,
            content=ft.ProgressRing(width=14, height=14, stroke_width=2, color=C.accent),
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
                            color=C.text_subtle,
                            size=FONT.small,
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
                            padding=ft.Padding(left=14, top=12, right=14, bottom=12),
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
                                    ft.Column(
                                        spacing=2,
                                        expand=True,
                                        controls=[
                                            ft.Text(
                                                summary,
                                                color=C.text,
                                                size=FONT.body,
                                                weight=ft.FontWeight.W_600,
                                                max_lines=1,
                                                overflow=ft.TextOverflow.ELLIPSIS,
                                            ),
                                            ft.Text(
                                                when,
                                                color=C.text_subtle,
                                                size=FONT.micro,
                                            ),
                                        ],
                                    ),
                                    ft.Icon(
                                        ft.Icons.CHEVRON_RIGHT_ROUNDED,
                                        color=C.text_subtle,
                                        size=18,
                                    ),
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
                icon_color=C.text_muted,
                icon_size=20,
                on_click=go_settings,
            ),
            ft.Container(width=8),
        ],
    )

    # ============================================================
    # Assemblage
    # ============================================================
    view = ft.View(
        route="/",
        padding=0,
        bgcolor=C.bg,
        scroll=ft.ScrollMode.AUTO,
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
                        erp_hero_card,
                        T.section_header("Vue d'ensemble"),
                        grid,
                        T.section_header("Prochains rendez-vous"),
                        next_rdv_col,
                    ],
                ),
            )
        ),
    ]

    # Lancer les chargements en parallèle — ERP en premier
    for fn in (load_erp, load_bourse_mini, load_mails_count,
               load_rdv, load_docs, load_next_rdv, load_biz):
        threading.Thread(target=fn, daemon=True).start()

    return view