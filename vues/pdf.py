"""
Vue Documents (PDFs) — adaptée au theme Arc.

Workflow :
  1. Bouton Local (FilePicker bytes) ou Drive
  2. Extraction pypdf + analyse Gemini structurée
  3. Vue détail : résumé, participants, décisions, RDV, tâches
  4. Bouton "Tout valider" → ajouts au Google Calendar
  5. Historique persistant (pdf_history.json)
"""

import threading

import flet as ft

from vues import theme as T
from vues.theme import C, FONT
from vues.navbar import build_navbar
from services.pdf_service import analyze_pdf_path, analyze_pdf_bytes
from services.pdf_history import list_history, add_entry, delete_entry, get_entry
from services.drive_service import list_pdfs_on_drive, download_pdf_from_drive
from services.calendar_service import create_event


def build(page: ft.Page) -> ft.View:

    state = {"mode": "list", "current_entry": None, "checkboxes": {}}

    # FilePicker — Service auto-enregistré + register explicite par sécurité
    file_picker = ft.FilePicker()
    try:
        if file_picker not in page._services._services:
            page._services.register_service(file_picker)
    except Exception as _e:
        print(f"[pdf vue] FilePicker register fallback: {_e}")

    content_holder = ft.Column(spacing=14, expand=True)
    status_text = ft.Text("", color=C.text_subtle, size=FONT.small)
    main_loading = ft.ProgressRing(width=16, height=16, stroke_width=2,
                                   color=C.accent, visible=False)

    # =====================================================
    # Renders
    # =====================================================
    def render_list():
        state["mode"] = "list"
        state["current_entry"] = None
        content_holder.controls.clear()

        # Boutons d'import — style pilule
        async def _local(e): await on_pick_local(e)
        async def _drive(e): await on_pick_drive(e)

        import_card = T.card(
            padding=18,
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Row(
                        spacing=10,
                        controls=[
                            ft.Icon(ft.Icons.UPLOAD_FILE_OUTLINED,
                                    color=C.accent, size=18),
                            ft.Text("Analyser un compte-rendu",
                                    color=C.text, size=FONT.h3,
                                    weight=ft.FontWeight.W_700),
                        ],
                    ),
                    ft.Text(
                        "Importe un PDF local ou depuis ton Drive. "
                        "L'IA détectera les RDV et tâches à ajouter au calendrier.",
                        color=C.text_muted, size=FONT.small,
                    ),
                    ft.Row(
                        spacing=10,
                        controls=[
                            T.pill_button("Local", icon=ft.Icons.FOLDER_OPEN_OUTLINED,
                                          on_click=_local, expand=True),
                            T.pill_button("Drive", icon=ft.Icons.CLOUD_OUTLINED,
                                          on_click=_drive, primary=False,
                                          expand=True),
                        ],
                    ),
                    ft.Row([status_text, main_loading], spacing=10,
                           vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ],
            ),
        )

        history = list_history()
        history_col = ft.Column(spacing=8)
        if not history:
            history_col.controls.append(
                ft.Container(
                    padding=20,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        "Aucun compte-rendu analysé pour l'instant.",
                        color=C.text_subtle, italic=True, size=FONT.small,
                    ),
                )
            )
        else:
            for entry in history:
                history_col.controls.append(_history_card(entry))

        content_holder.controls.extend([
            import_card,
            T.section_header("Historique",
                             action=T.chip(f"{len(history)} CR")),
            history_col,
        ])
        page.update()

    def _history_card(entry):
        an = entry.get("analysis", {})
        resume = (an.get("resume") or "").strip() or "(pas de résumé)"
        ev = len(an.get("evenements", []))
        ta = len(an.get("taches", []))
        date = entry.get("analyzed_at", "")[:10]
        src = entry.get("source", "?")
        src_icon = ft.Icons.CLOUD_OUTLINED if src == "drive" else ft.Icons.FOLDER_OUTLINED

        return T.card(
            on_click=lambda e, eid=entry["id"]: open_detail_from_history(eid),
            padding=14,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(
                                spacing=8, expand=True,
                                controls=[
                                    ft.Icon(src_icon, color=C.accent, size=14),
                                    ft.Text(
                                        entry.get("filename", "PDF"),
                                        weight=ft.FontWeight.W_600,
                                        color=C.text, size=FONT.body,
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                ],
                            ),
                            ft.IconButton(
                                icon=ft.Icons.CLOSE_ROUNDED,
                                icon_color=C.text_subtle, icon_size=16,
                                tooltip="Supprimer",
                                on_click=lambda e, eid=entry["id"]: _delete(eid),
                            ),
                        ],
                    ),
                    ft.Text(resume[:160] + ("…" if len(resume) > 160 else ""),
                            size=FONT.small, color=C.text_muted, max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Row(
                        spacing=6,
                        controls=[
                            T.chip(date),
                            T.accent_chip(f"{ev} RDV"),
                            T.accent_chip(f"{ta} tâches", color=C.warning),
                        ],
                    ),
                ],
            ),
        )

    def _delete(entry_id):
        delete_entry(entry_id)
        page.show_dialog(ft.SnackBar(ft.Text("Entrée supprimée"),
                                     duration=1500))
        render_list()

    # =====================================================
    # Detail
    # =====================================================
    def open_detail_from_history(entry_id):
        entry = get_entry(entry_id)
        if entry:
            render_detail(entry)

    def render_detail(entry):
        state["mode"] = "detail"
        state["current_entry"] = entry
        state["checkboxes"] = {}

        an = entry.get("analysis", {})
        err = an.get("error")

        content_holder.controls.clear()

        # Header avec back
        content_holder.controls.append(
            ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                        icon_color=C.text_muted, icon_size=16,
                        on_click=lambda e: render_list(),
                    ),
                    ft.Column(
                        expand=True, spacing=2,
                        controls=[
                            ft.Text(entry.get("filename", "PDF"),
                                    size=FONT.h3, weight=ft.FontWeight.W_700,
                                    color=C.text, max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(
                                entry.get("analyzed_at", "")[:19].replace("T", " "),
                                size=FONT.micro, color=C.text_subtle,
                            ),
                        ],
                    ),
                ],
            )
        )

        if err:
            content_holder.controls.append(
                T.card(content=ft.Text(f"Erreur d'analyse : {err}",
                                       color=C.danger, size=FONT.small))
            )
            page.update()
            return

        # Résumé
        if an.get("resume"):
            content_holder.controls.append(
                T.card(content=ft.Column(spacing=8, controls=[
                    ft.Text("Résumé", color=C.text_muted, size=FONT.small,
                            weight=ft.FontWeight.W_600),
                    ft.Text(an["resume"], color=C.text, size=FONT.body,
                            selectable=True),
                ]))
            )

        # Participants
        if an.get("participants"):
            content_holder.controls.append(
                T.card(content=ft.Column(spacing=10, controls=[
                    ft.Text("Participants", color=C.text_muted,
                            size=FONT.small, weight=ft.FontWeight.W_600),
                    ft.Row(wrap=True, spacing=6, run_spacing=6,
                           controls=[T.chip(p) for p in an["participants"]]),
                ]))
            )

        # Décisions
        if an.get("decisions"):
            content_holder.controls.append(
                T.card(content=ft.Column(spacing=10, controls=[
                    ft.Text("Décisions", color=C.text_muted,
                            size=FONT.small, weight=ft.FontWeight.W_600),
                    *[
                        ft.Row(
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                            controls=[
                                ft.Container(
                                    width=6, height=6,
                                    margin=ft.Margin(left=0, top=8,
                                                     right=0, bottom=0),
                                    border_radius=999,
                                    bgcolor=C.success,
                                ),
                                ft.Container(
                                    expand=True,
                                    content=ft.Text(d, color=C.text,
                                                    size=FONT.body,
                                                    selectable=True),
                                ),
                            ],
                        ) for d in an["decisions"]
                    ],
                ]))
            )

        # RDV
        evs = an.get("evenements", []) or []
        if evs:
            ev_items = []
            for i, ev in enumerate(evs):
                cb = ft.Checkbox(value=True, fill_color=C.accent)
                state["checkboxes"][("ev", i)] = cb
                titre = ev.get("titre") or "(sans titre)"
                meta = []
                if ev.get("date"): meta.append(ev["date"])
                if ev.get("heure_debut"):
                    h = ev["heure_debut"]
                    if ev.get("heure_fin"): h += f" – {ev['heure_fin']}"
                    meta.append(h)
                if ev.get("lieu"): meta.append(ev["lieu"])
                ev_items.append(
                    ft.Container(
                        padding=12,
                        border_radius=14,
                        bgcolor=C.bg_subtle,
                        content=ft.Row(
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                            controls=[
                                cb,
                                ft.Column(
                                    expand=True, spacing=4,
                                    controls=[
                                        ft.Text(titre, color=C.text,
                                                size=FONT.body,
                                                weight=ft.FontWeight.W_600),
                                        ft.Text(" · ".join(meta) if meta
                                                else "(pas de date)",
                                                color=C.text_subtle,
                                                size=FONT.micro),
                                        *([ft.Text(ev["description"],
                                                   color=C.text_muted,
                                                   size=FONT.micro,
                                                   max_lines=2,
                                                   overflow=ft.TextOverflow.ELLIPSIS)]
                                          if ev.get("description") else []),
                                    ],
                                ),
                            ],
                        ),
                    )
                )
            content_holder.controls.append(
                T.card(content=ft.Column(spacing=10, controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("RDV détectés", color=C.text_muted,
                                    size=FONT.small,
                                    weight=ft.FontWeight.W_600),
                            T.accent_chip(str(len(evs))),
                        ],
                    ),
                    *ev_items,
                ]))
            )

        # Tâches
        tasks = an.get("taches", []) or []
        if tasks:
            t_items = []
            for i, t in enumerate(tasks):
                cb = ft.Checkbox(value=True, fill_color=C.warning)
                state["checkboxes"][("ta", i)] = cb
                meta = []
                if t.get("deadline"): meta.append(f"⏳ {t['deadline']}")
                t_items.append(
                    ft.Container(
                        padding=12,
                        border_radius=14,
                        bgcolor=C.bg_subtle,
                        content=ft.Row(
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                            controls=[
                                cb,
                                ft.Column(
                                    expand=True, spacing=4,
                                    controls=[
                                        ft.Text(t.get("titre", "(tâche)"),
                                                color=C.text, size=FONT.body,
                                                weight=ft.FontWeight.W_600),
                                        *([ft.Text(" · ".join(meta),
                                                   color=C.text_subtle,
                                                   size=FONT.micro)]
                                          if meta else []),
                                        *([ft.Text(t["description"],
                                                   color=C.text_muted,
                                                   size=FONT.micro,
                                                   max_lines=2,
                                                   overflow=ft.TextOverflow.ELLIPSIS)]
                                          if t.get("description") else []),
                                    ],
                                ),
                            ],
                        ),
                    )
                )
            content_holder.controls.append(
                T.card(content=ft.Column(spacing=10, controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Tâches détectées", color=C.text_muted,
                                    size=FONT.small,
                                    weight=ft.FontWeight.W_600),
                            T.accent_chip(str(len(tasks)), color=C.warning),
                        ],
                    ),
                    *t_items,
                ]))
            )

        if evs or tasks:
            content_holder.controls.append(
                ft.Container(margin=ft.Margin(left=0, top=4, right=0, bottom=8),
                             content=T.pill_button(
                                 "Tout valider · Ajouter au calendrier",
                                 icon=ft.Icons.CHECK_ROUNDED,
                                 on_click=on_validate_all,
                                 expand=True,
                             ))
            )

        # ---- Actions IA / PV ----
        content_holder.controls.append(
            ft.Row(
                spacing=8,
                controls=[
                    T.pill_button(
                        "Challenge IA",
                        icon=ft.Icons.PSYCHOLOGY_OUTLINED,
                        on_click=lambda e: open_challenge_dialog(entry),
                        primary=False, expand=True,
                    ),
                    T.pill_button(
                        "Envoyer PV",
                        icon=ft.Icons.SEND_OUTLINED,
                        on_click=lambda e: open_send_pv_dialog(entry),
                        primary=False, expand=True,
                    ),
                ],
            )
        )
        content_holder.controls.append(ft.Container(height=16))

        page.update()

    # =====================================================
    # Challenge IA
    # =====================================================
    def open_challenge_dialog(entry):
        body_holder = ft.Container(
            width=380, height=380,
            alignment=ft.Alignment.CENTER,
            content=ft.ProgressRing(color=C.accent),
        )
        dialog = ft.AlertDialog(
            modal=False, bgcolor=C.bg_elevated,
            title=ft.Text("Challenge IA", color=C.text,
                          weight=ft.FontWeight.W_700, size=FONT.h3),
            content=body_holder,
            actions=[ft.TextButton(
                "Fermer", on_click=lambda _e: page.pop_dialog())],
        )
        page.show_dialog(dialog)

        def work():
            try:
                from services.meeting_service import challenge_meeting
                resp = challenge_meeting(entry.get("analysis", {}))
            except Exception as e:
                resp = f"Erreur : {e}"
            body_holder.content = ft.Container(
                expand=True,
                content=ft.ListView(
                    expand=True, spacing=4,
                    controls=[ft.Text(resp, color=C.text, size=FONT.small,
                                      selectable=True)],
                ),
            )
            page.update()

        threading.Thread(target=work, daemon=True).start()

    # =====================================================
    # Envoyer PV
    # =====================================================
    def open_send_pv_dialog(entry):
        an = entry.get("analysis", {})
        participants_str = ", ".join(an.get("participants", []) or [])

        f_type = ft.TextField(
            label="Type de réunion", value="Comité de direction",
            bgcolor=C.bg_subtle, border_color=C.border,
            focused_border_color=C.accent, color=C.text,
            label_style=ft.TextStyle(color=C.text_subtle),
        )
        f_animateur = ft.TextField(
            label="Animateur", value="",
            bgcolor=C.bg_subtle, border_color=C.border,
            focused_border_color=C.accent, color=C.text,
            label_style=ft.TextStyle(color=C.text_subtle),
        )
        f_emails = ft.TextField(
            label="Emails des participants (séparés par ,)",
            value="",
            bgcolor=C.bg_subtle, border_color=C.border,
            focused_border_color=C.accent, color=C.text,
            label_style=ft.TextStyle(color=C.text_subtle),
            multiline=True, min_lines=2, max_lines=3,
        )
        f_sujet = ft.TextField(
            label="Sujet du mail",
            value=f"PV — {entry.get('filename', 'Réunion')}",
            bgcolor=C.bg_subtle, border_color=C.border,
            focused_border_color=C.accent, color=C.text,
            label_style=ft.TextStyle(color=C.text_subtle),
        )

        result_text = ft.Text("", color=C.text_subtle, size=FONT.micro)
        ring = ft.ProgressRing(visible=False, width=14, height=14,
                               color=C.accent, stroke_width=2)

        def _send(e):
            emails = [x.strip() for x in (f_emails.value or "").replace(";", ",").split(",")
                      if x.strip()]
            if not emails:
                result_text.value = "❌ Aucun email valide."
                page.update()
                return
            ring.visible = True
            result_text.value = "Envoi en cours…"
            page.update()

            def work():
                try:
                    from services.meeting_service import (
                        generate_pv_html, send_pv_to_participants)
                    html = generate_pv_html(
                        an, type_reunion=f_type.value or "Réunion",
                        animateur=f_animateur.value or "—",
                    )
                    res = send_pv_to_participants(
                        html, emails, subject=f_sujet.value or "PV")
                    result_text.value = res
                except Exception as ex:
                    result_text.value = f"Erreur : {ex}"
                ring.visible = False
                page.update()

            threading.Thread(target=work, daemon=True).start()

        dialog = ft.AlertDialog(
            modal=False, bgcolor=C.bg_elevated,
            title=ft.Text("Envoyer le PV", color=C.text,
                          weight=ft.FontWeight.W_700, size=FONT.h3),
            content=ft.Container(
                width=380,
                content=ft.Column(
                    spacing=10, tight=True,
                    controls=[
                        f_type, f_animateur, f_sujet, f_emails,
                        *([ft.Text(f"Participants détectés : {participants_str}",
                                   color=C.text_subtle, size=FONT.micro,
                                   italic=True)]
                          if participants_str else []),
                        ft.Container(height=4),
                        ft.Row([ring, result_text], spacing=8),
                    ],
                ),
            ),
            actions=[
                ft.TextButton("Annuler",
                              on_click=lambda _e: page.pop_dialog()),
                ft.TextButton("Envoyer", on_click=_send),
            ],
        )
        page.show_dialog(dialog)

    # =====================================================
    # Validation -> Calendrier
    # =====================================================
    def on_validate_all(e=None):
        entry = state.get("current_entry")
        if not entry: return
        an = entry.get("analysis", {})
        evs = an.get("evenements", []) or []
        tasks = an.get("taches", []) or []

        status_text.value = "Ajout en cours…"
        main_loading.visible = True
        page.update()

        def work():
            added, errors = 0, []
            for i, ev in enumerate(evs):
                cb = state["checkboxes"].get(("ev", i))
                if not cb or not cb.value: continue
                title = ev.get("titre") or "Événement"
                date = ev.get("date")
                hs = ev.get("heure_debut") or "09:00"
                he = ev.get("heure_fin") or _add_one_hour(hs)
                if not date:
                    errors.append(f"{title} : pas de date")
                    continue
                try:
                    create_event(title, date, hs, he)
                    added += 1
                except Exception as ex:
                    errors.append(f"{title} : {ex}")

            for i, t in enumerate(tasks):
                cb = state["checkboxes"].get(("ta", i))
                if not cb or not cb.value: continue
                title = "📌 " + (t.get("titre") or "Tâche")
                deadline = t.get("deadline")
                if not deadline:
                    errors.append(f"{title} : pas de deadline (ignoré)")
                    continue
                try:
                    create_event(title, deadline, "09:00", "10:00")
                    added += 1
                except Exception as ex:
                    errors.append(f"{title} : {ex}")

            status_text.value = ""
            main_loading.visible = False
            msg = f"✅ {added} ajouté(s) au calendrier"
            if errors:
                msg += f" · {len(errors)} non ajouté(s)"
            page.show_dialog(ft.SnackBar(ft.Text(msg), duration=3000))
            page.update()

        threading.Thread(target=work, daemon=True).start()

    def _add_one_hour(hhmm):
        try:
            h, m = hhmm.split(":")
            h = (int(h) + 1) % 24
            return f"{h:02d}:{m}"
        except Exception:
            return "10:00"

    # =====================================================
    # Imports
    # =====================================================
    async def on_pick_local(e=None):
        try:
            files = await file_picker.pick_files(
                dialog_title="Choisir un compte-rendu PDF",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["pdf"],
                allow_multiple=False,
                with_data=True,
            )
        except Exception as ex:
            status_text.value = f"Erreur picker : {ex}"
            page.update()
            return
        if not files: return
        f = files[0]
        if f.bytes:
            _analyze_and_show(filename=f.name, source="local", data=f.bytes)
        elif f.path:
            _analyze_and_show(filename=f.name, source="local", path=f.path)
        else:
            status_text.value = "Impossible de lire le fichier."
            page.update()

    async def on_pick_drive(e=None):
        list_col = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
        loading_row = ft.Row(
            spacing=8, controls=[
                ft.ProgressRing(width=14, height=14, stroke_width=2,
                                color=C.accent),
                ft.Text("Chargement de tes PDFs…",
                        color=C.text_subtle, size=FONT.small),
            ]
        )
        body = ft.Container(
            width=380, height=420,
            content=ft.Column(spacing=10,
                              controls=[loading_row, list_col]),
        )
        dialog = ft.AlertDialog(
            modal=False,
            bgcolor=C.bg_elevated,
            title=ft.Text("Tes PDFs sur Drive",
                          color=C.text, weight=ft.FontWeight.W_700),
            content=body,
            actions=[ft.TextButton("Fermer",
                                   on_click=lambda _e: page.pop_dialog())],
        )
        page.show_dialog(dialog)

        def fetch():
            files = list_pdfs_on_drive(max_results=50)
            loading_row.visible = False
            if not files:
                list_col.controls.append(
                    ft.Text("Aucun PDF trouvé sur ton Drive.",
                            color=C.text_subtle, italic=True, size=FONT.small)
                )
            else:
                for f in files:
                    list_col.controls.append(_drive_row(f, dialog))
            page.update()

        threading.Thread(target=fetch, daemon=True).start()

    def _drive_row(f, dialog):
        def _pick(e):
            page.pop_dialog()
            _analyze_and_show(filename=f["name"], source="drive",
                              drive_id=f["id"])
        size_kb = ""
        try:
            if f.get("size"):
                size_kb = f"{int(f.get('size', 0)) // 1024} KB"
        except Exception:
            pass
        mt = f.get("modifiedTime", "")[:10]
        return ft.Container(
            padding=10, border_radius=12, bgcolor=C.bg_subtle,
            ink=True, on_click=_pick,
            content=ft.Row(
                spacing=10,
                controls=[
                    ft.Icon(ft.Icons.PICTURE_AS_PDF, color=C.danger, size=18),
                    ft.Column(expand=True, spacing=2, controls=[
                        ft.Text(f["name"], color=C.text, size=FONT.small,
                                weight=ft.FontWeight.W_600, max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(f"{mt} · {size_kb}",
                                color=C.text_subtle, size=FONT.micro),
                    ]),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED,
                            color=C.text_subtle),
                ],
            ),
        )

    def _analyze_and_show(filename, source, path=None, drive_id=None,
                          data=None):
        status_text.value = f"Analyse de {filename}… (10-30s)"
        main_loading.visible = True
        page.update()

        def work():
            try:
                if source == "drive":
                    d = download_pdf_from_drive(drive_id)
                    if d is None: raise RuntimeError("DL Drive échoué.")
                    analysis = analyze_pdf_bytes(d)
                elif data is not None:
                    analysis = analyze_pdf_bytes(data)
                elif path:
                    analysis = analyze_pdf_path(path)
                else:
                    raise RuntimeError("Aucune source de PDF.")
                entry = add_entry(filename=filename, source=source,
                                  analysis=analysis, drive_id=drive_id)
                status_text.value = ""
                main_loading.visible = False
                render_detail(entry)
            except Exception as ex:
                status_text.value = f"Erreur : {ex}"
                main_loading.visible = False
                page.update()

        threading.Thread(target=work, daemon=True).start()

    # =====================================================
    # Assemblage
    # =====================================================
    refresh_btn = ft.IconButton(
        icon=ft.Icons.REFRESH_ROUNDED,
        icon_color=C.text_muted, icon_size=18,
        tooltip="Rafraîchir",
        on_click=lambda e: render_list(),
    )

    view = ft.View(
        route="/pdf", padding=0, bgcolor=C.bg, scroll=ft.ScrollMode.AUTO,
    )
    view.navigation_bar = build_navbar(page, selected=0)
    view.appbar = T.appbar("Documents", back_route="/", page=page,
                           actions=[refresh_btn, ft.Container(width=8)])

    view.controls = [
        ft.Container(
            padding=ft.Padding(left=20, top=8, right=20, bottom=24),
            content=content_holder,
        ),
    ]

    render_list()
    return view