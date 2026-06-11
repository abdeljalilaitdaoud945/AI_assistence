"""
Vue ERP — Pilotage de la performance et recommandations IA.
Style Arc-inspired. Mise à jour pour afficher les données enrichies.
"""

import threading
import flet as ft

from vues import theme as T
from vues.theme import C, FONT
from vues.navbar import build_navbar, nav_index_for
from services.erp_service import get_erp_data, generate_erp_recommendations

def build(page: ft.Page) -> ft.View:

    content_col = ft.Column(spacing=14)
    ai_analysis_card = ft.Container(visible=False)

    def refresh():
        try:
            data = get_erp_data()
            fin = data.get("finance", {})
            ops = data.get("operations", {})

            ca = fin.get("chiffre_affaires", {})
            marge = fin.get("marge_globale", {})
            treso = fin.get("tresorerie", {})
            factures = fin.get("factures_impayees", {})

            retards = ops.get("projets_en_retard", [])
            ventes = ops.get("top_ventes_services", [])
            occupation = ops.get("taux_occupation_equipes", 0)

            # ---- Impact financier total des retards (bandeau) ----
            impact_total = sum(r.get("impact_estime", 0) for r in retards)
            impact_banner = ft.Container(
                padding=14,
                border_radius=14,
                bgcolor=ft.Colors.with_opacity(0.12, C.danger),
                border=ft.Border(
                    top=ft.BorderSide(1, C.danger),
                    bottom=ft.BorderSide(1, C.danger),
                    left=ft.BorderSide(3, C.danger),
                    right=ft.BorderSide(1, C.danger),
                ),
                content=ft.Row(
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED,
                                color=C.danger, size=24),
                        ft.Column(
                            spacing=2, expand=True,
                            controls=[
                                ft.Text("Impact financier des retards",
                                        color=C.danger,
                                        weight=ft.FontWeight.W_700,
                                        size=FONT.small),
                                ft.Text(
                                    f"{impact_total:,} MAD exposés sur "
                                    f"{len(retards)} projet(s) en alerte",
                                    color=C.text, size=FONT.body,
                                    weight=ft.FontWeight.W_600),
                            ],
                        ),
                    ],
                ),
            )

            # ---- KPI Row : 4 colonnes (CA, Marge, Trésorerie, Occupation) ----
            kpi_row = ft.ResponsiveRow(
                spacing=12, run_spacing=12,
                controls=[
                    ft.Container(
                        col={"xs": 6, "md": 3},
                        content=T.stat_arc(
                            "CA (YTD)",
                            f"{ca.get('realise_ytd', 0) / 1000000:.1f}M",
                            sub=f"Obj: {ca.get('objectif_ytd', 0) / 1000000:.1f}M",
                            color=C.warning,
                            size=90,
                        ),
                    ),
                    ft.Container(
                        col={"xs": 6, "md": 3},
                        content=T.stat_arc(
                            "Marge",
                            f"{marge.get('realise', 0)}%",
                            sub=f"Obj: {marge.get('objectif', 0)}%",
                            color=(C.danger
                                   if marge.get('realise', 0) < marge.get('objectif', 0)
                                   else C.success),
                            size=90,
                        ),
                    ),
                    ft.Container(
                        col={"xs": 6, "md": 3},
                        content=T.stat_arc(
                            "Trésorerie",
                            f"{treso.get('disponible', 0) / 1000:.0f}K",
                            sub=treso.get("statut", "").upper(),
                            color=(C.danger
                                   if treso.get("statut") == "critique"
                                   else C.success),
                            size=90,
                        ),
                    ),
                    ft.Container(
                        col={"xs": 6, "md": 3},
                        alignment=ft.Alignment.CENTER,
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=6,
                            controls=[
                                T.ring_chart(
                                    value=occupation, total=100,
                                    color=(C.success if occupation >= 80
                                           else C.warning if occupation >= 60
                                           else C.danger),
                                    size=78, stroke=9,
                                    label=f"{occupation}%",
                                ),
                                ft.Text("Occupation équipes",
                                        color=C.text_muted,
                                        size=FONT.micro,
                                        weight=ft.FontWeight.W_600),
                            ],
                        ),
                    ),
                ],
            )

            # ---- Factures impayées ----
            factures_card = T.card(
                padding=14,
                content=ft.Column(spacing=10, controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(spacing=8, controls=[
                                ft.Icon(ft.Icons.RECEIPT_LONG_OUTLINED,
                                        color=C.warning, size=18),
                                ft.Text("Factures impayées",
                                        color=C.text, size=FONT.body,
                                        weight=ft.FontWeight.W_700),
                            ]),
                            ft.Text(
                                f"{factures.get('montant_total', 0):,} MAD",
                                color=C.warning,
                                weight=ft.FontWeight.W_700,
                                size=FONT.body),
                        ],
                    ),
                    ft.Row(
                        wrap=True, spacing=6, run_spacing=6,
                        controls=[
                            T.chip(c) for c in
                            factures.get("clients_principaux", [])
                        ],
                    ),
                ]),
            )

            # ---- Top ventes services (barres horizontales) ----
            ventes_max = max((v.get("ca_genere", 0) for v in ventes), default=1)
            ventes_rows = []
            for v in ventes:
                ca_v = v.get("ca_genere", 0)
                ratio = ca_v / ventes_max if ventes_max else 0
                croiss = v.get("croissance", "")
                is_neg = croiss.strip().startswith("-")
                ventes_rows.append(
                    ft.Column(spacing=4, controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(v.get("service", "—"),
                                        color=C.text, size=FONT.small,
                                        weight=ft.FontWeight.W_600,
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                        expand=True),
                                ft.Row(spacing=8, controls=[
                                    ft.Text(f"{ca_v / 1000000:.1f}M MAD",
                                            color=C.text_subtle,
                                            size=FONT.micro,
                                            weight=ft.FontWeight.W_600),
                                    ft.Container(
                                        padding=ft.Padding(
                                            left=6, top=1, right=6, bottom=1),
                                        border_radius=999,
                                        bgcolor=ft.Colors.with_opacity(
                                            0.18,
                                            C.danger if is_neg else C.success),
                                        content=ft.Text(
                                            croiss,
                                            color=C.danger if is_neg else C.success,
                                            size=10,
                                            weight=ft.FontWeight.W_700),
                                    ),
                                ]),
                            ],
                        ),
                        # Barre de progression
                        ft.Container(
                            height=6, border_radius=999,
                            bgcolor=C.bg_subtle,
                            content=ft.Row(controls=[
                                ft.Container(
                                    width=max(2, int(220 * ratio)),
                                    height=6,
                                    border_radius=999,
                                    bgcolor=C.accent,
                                ),
                            ]),
                        ),
                    ])
                )
            ventes_card = T.card(
                padding=14,
                content=ft.Column(spacing=12, controls=[
                    ft.Row(spacing=8, controls=[
                        ft.Icon(ft.Icons.TRENDING_UP_ROUNDED,
                                color=C.accent, size=18),
                        ft.Text("Top services par CA généré",
                                color=C.text, size=FONT.body,
                                weight=ft.FontWeight.W_700),
                    ]),
                    *ventes_rows,
                ]),
            )

            # ---- Retards (Avec causes) ----
            retards_col = ft.Column(spacing=8)
            for r in retards:
                retards_col.controls.append(
                    T.card(
                        accent=True, padding=14,
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Column(
                                    spacing=4, expand=True,
                                    controls=[
                                        ft.Text(r["projet"], color=C.text,
                                                weight=ft.FontWeight.W_600,
                                                size=FONT.body),
                                        ft.Text(
                                            f"Client: {r['client']} | Cause: {r['cause']}",
                                            color=C.text_subtle,
                                            size=FONT.micro),
                                    ],
                                ),
                                ft.Column(
                                    spacing=2,
                                    horizontal_alignment=ft.CrossAxisAlignment.END,
                                    controls=[
                                        ft.Text(f"{r['retard_jours']}j retard",
                                                color=C.danger,
                                                weight=ft.FontWeight.W_700,
                                                size=FONT.small),
                                        ft.Text(
                                            f"Impact: {r['impact_estime']:,} MAD",
                                            color=C.text_subtle,
                                            size=FONT.micro),
                                    ],
                                ),
                            ],
                        ),
                    )
                )

            content_col.controls = [
                impact_banner,
                ft.Container(height=4),
                ft.Text("Indicateurs Financiers",
                        size=FONT.h2, color=C.text,
                        weight=ft.FontWeight.W_700),
                kpi_row,
                ft.Container(height=8),
                ft.ResponsiveRow(
                    spacing=12, run_spacing=12,
                    controls=[
                        ft.Container(col={"xs": 12, "md": 6},
                                     content=factures_card),
                        ft.Container(col={"xs": 12, "md": 6},
                                     content=ventes_card),
                    ],
                ),
                ft.Container(height=8),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("Opérations : Projets en alerte",
                                size=FONT.h2, color=C.text,
                                weight=ft.FontWeight.W_700),
                        T.accent_chip(str(len(retards)), color=C.danger),
                    ],
                ),
                retards_col,
            ]
            page.update()
        except Exception as e:
            content_col.controls = [
                ft.Text(f"Erreur de chargement: {e}", color=C.danger)
            ]
            page.update()

    def _parse_strategic_note(txt: str) -> dict:
        """Parse la note Gemini en 3 sections (clé = marqueur emoji)."""
        sections = {"🔴": [], "🟠": [], "🟢": []}
        current = None
        for raw in (txt or "").splitlines():
            line = raw.strip()
            if not line:
                continue
            hit = None
            for marker in sections:
                if line.startswith(marker):
                    hit = marker
                    break
            if hit:
                current = hit
                continue
            if current is None:
                continue
            clean = line.lstrip("-•*·").strip()
            if clean:
                sections[current].append(clean)
        return sections

    def _build_strategic_card(marker, title, color, items):
        if not items:
            items = ["(aucun point retourné)"]
        bullets = [
            ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Container(
                        width=4, height=4,
                        margin=ft.Margin(left=0, top=8, right=0, bottom=0),
                        border_radius=999, bgcolor=color),
                    ft.Text(it, color=C.text, size=FONT.small,
                            selectable=True, expand=True, no_wrap=False),
                ],
            ) for it in items
        ]
        return ft.Container(
            padding=14,
            border_radius=14,
            bgcolor=C.bg_subtle,
            border=ft.Border(
                top=ft.BorderSide(1, color),
                bottom=ft.BorderSide(1, color),
                left=ft.BorderSide(3, color),
                right=ft.BorderSide(1, color),
            ),
            content=ft.Column(spacing=10, controls=[
                ft.Row(spacing=8, controls=[
                    ft.Text(marker, size=FONT.body),
                    ft.Text(title, color=color, size=FONT.small,
                            weight=ft.FontWeight.W_700),
                ]),
                ft.Column(spacing=8, controls=bullets),
            ]),
        )

    def do_analysis(e):
        btn_analysis.visible = False
        loading.visible = True
        page.update()

        def work():
            try:
                reco = generate_erp_recommendations()
                parsed = _parse_strategic_note(reco)
                ai_analysis_card.content = T.card(
                    padding=18,
                    border=ft.Border(
                        left=ft.BorderSide(3, C.accent),
                        top=ft.BorderSide(1, C.border),
                        bottom=ft.BorderSide(1, C.border),
                        right=ft.BorderSide(1, C.border),
                    ),
                    content=ft.Column(spacing=12, controls=[
                        ft.Row(spacing=8, controls=[
                            ft.Icon(ft.Icons.AUTO_AWESOME,
                                    color=C.accent, size=20),
                            ft.Text("Note Stratégique du Copilote IA",
                                    color=C.text,
                                    weight=ft.FontWeight.W_700,
                                    size=FONT.h3),
                        ]),
                        _build_strategic_card(
                            "🔴", "Alerte financière",
                            C.danger, parsed["🔴"]),
                        _build_strategic_card(
                            "🟠", "Risques opérationnels",
                            C.warning, parsed["🟠"]),
                        _build_strategic_card(
                            "🟢", "Plan d'action immédiat",
                            C.success, parsed["🟢"]),
                    ]),
                )
            except Exception as ex:
                ai_analysis_card.content = T.card(
                    content=ft.Text(f"Erreur : {ex}",
                                    color=C.danger, size=FONT.small,
                                    selectable=True)
                )
            ai_analysis_card.visible = True
            loading.visible = False
            btn_analysis.visible = True
            page.update()

        threading.Thread(target=work, daemon=True).start()

    btn_analysis = T.pill_button(
        "Générer une Note Stratégique (IA)", 
        icon=ft.Icons.ANALYTICS_OUTLINED, 
        on_click=do_analysis, 
        primary=False
    )
    
    loading = ft.ProgressRing(
        visible=False, 
        width=16, 
        height=16, 
        color=C.accent, 
        stroke_width=2
    )

    view = ft.View(
        route="/erp", 
        padding=0, 
        bgcolor=C.bg, 
        scroll=ft.ScrollMode.AUTO
    )
    
    view.navigation_bar = build_navbar(page, selected=nav_index_for("/erp"))
    view.appbar = T.appbar("Pilotage ERP", back_route="/", page=page)

    view.controls = [
        ft.Container(
            padding=ft.Padding(left=20, top=8, right=20, bottom=24),
            content=ft.Column(
                spacing=14, 
                controls=[
                    ft.Text(
                        "Tableau de Bord de Direction", 
                        size=FONT.display, 
                        color=C.text, 
                        weight=ft.FontWeight.W_700
                    ),
                    ft.Text(
                        "Données SI synchronisées en temps réel.", 
                        size=FONT.small, 
                        color=C.text_subtle
                    ),
                    ft.Container(height=4),
                    content_col,
                    ft.Container(height=12),
                    ft.Row([btn_analysis, loading]),
                    ai_analysis_card
                ]
            )
        )
    ]

    refresh()
    return view