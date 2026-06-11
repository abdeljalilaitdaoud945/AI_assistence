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
            
            retards = ops.get("projets_en_retard", [])
            ventes = ops.get("top_ventes_services", [])

            # ---- KPI Row (3 colonnes maintenant) ----
            kpi_row = ft.ResponsiveRow(
                spacing=12, 
                run_spacing=12,
                controls=[
                    ft.Container(
                        col={"xs": 12, "md": 4},
                        content=T.stat_arc(
                            "CA (YTD)",
                            f"{ca.get('realise_ytd', 0) / 1000000:.1f}M",
                            sub=f"Obj: {ca.get('objectif_ytd', 0) / 1000000:.1f}M",
                            color=C.warning,
                            size=90
                        )
                    ),
                    ft.Container(
                        col={"xs": 12, "md": 4},
                        content=T.stat_arc(
                            "Marge",
                            f"{marge.get('realise', 0)}%",
                            sub=f"Obj: {marge.get('objectif', 0)}%",
                            color=C.danger if marge.get('realise', 0) < marge.get('objectif', 0) else C.success,
                            size=90
                        )
                    ),
                    ft.Container(
                        col={"xs": 12, "md": 4},
                        content=T.stat_arc(
                            "Trésorerie",
                            f"{treso.get('disponible', 0) / 1000:.0f}K",
                            sub=treso.get("statut", "").upper(),
                            color=C.danger if treso.get("statut") == "critique" else C.success,
                            size=90
                        )
                    )
                ]
            )

            # ---- Retards (Avec causes) ----
            retards_col = ft.Column(spacing=8)
            for r in retards:
                retards_col.controls.append(
                    T.card(
                        accent=True,
                        padding=14,
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Column(
                                    spacing=4, 
                                    expand=True, 
                                    controls=[
                                        ft.Text(
                                            r["projet"], 
                                            color=C.text, 
                                            weight=ft.FontWeight.W_600, 
                                            size=FONT.body
                                        ),
                                        ft.Text(
                                            f"Client: {r['client']} | Cause: {r['cause']}", 
                                            color=C.text_subtle, 
                                            size=FONT.micro
                                        )
                                    ]
                                ),
                                ft.Column(
                                    spacing=2, 
                                    horizontal_alignment=ft.CrossAxisAlignment.END, 
                                    controls=[
                                        ft.Text(
                                            f"{r['retard_jours']}j retard", 
                                            color=C.danger, 
                                            weight=ft.FontWeight.W_700, 
                                            size=FONT.small
                                        ),
                                        ft.Text(
                                            f"Impact: {r['impact_estime']:,} MAD", 
                                            color=C.text_subtle, 
                                            size=FONT.micro
                                        )
                                    ]
                                )
                            ]
                        )
                    )
                )

            content_col.controls = [
                ft.Text(
                    "Indicateurs Financiers", 
                    size=FONT.h2, 
                    color=C.text, 
                    weight=ft.FontWeight.W_700
                ),
                kpi_row,
                ft.Container(height=8),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(
                            "Opérations : Projets en alerte", 
                            size=FONT.h2, 
                            color=C.text, 
                            weight=ft.FontWeight.W_700
                        ),
                        T.accent_chip(str(len(retards)), color=C.danger)
                    ]
                ),
                retards_col
            ]
            page.update()
        except Exception as e:
            content_col.controls = [
                ft.Text(f"Erreur de chargement: {e}", color=C.danger)
            ]
            page.update()

    def do_analysis(e):
        btn_analysis.visible = False
        loading.visible = True
        page.update()

        def work():
            reco = generate_erp_recommendations()
            ai_analysis_card.content = T.card(
                padding=18,
                border=ft.Border(
                    left=ft.BorderSide(3, C.accent), 
                    top=ft.BorderSide(1, C.border), 
                    bottom=ft.BorderSide(1, C.border), 
                    right=ft.BorderSide(1, C.border)
                ),
                content=ft.Column(
                    spacing=10, 
                    controls=[
                        ft.Row(
                            spacing=8, 
                            controls=[
                                ft.Icon(ft.Icons.AUTO_AWESOME, color=C.accent, size=20), 
                                ft.Text(
                                    "Note Stratégique du Copilote IA", 
                                    color=C.text, 
                                    weight=ft.FontWeight.W_700, 
                                    size=FONT.h3
                                )
                            ]
                        ),
                        ft.Text(reco, color=C.text, size=FONT.small, selectable=True)
                    ]
                )
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