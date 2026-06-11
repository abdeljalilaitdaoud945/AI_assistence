"""
Vue Assistant IA — chat refait Arc style.
Bulles propres, input avec pilule, micro + envoi groupés.
Fix : la route '/AI' calcule bien selected=3 dans la navbar.
"""

import threading

import flet as ft

from vues import theme as T
from vues.theme import C, FONT
from vues.navbar import build_navbar, nav_index_for
from services.ai_agent import ask_agent


def build(page: ft.Page) -> ft.View:

    if not hasattr(page, "_chat_history"):
        page._chat_history = []

    chat = ft.ListView(expand=True, spacing=14, auto_scroll=True,
                       padding=ft.Padding(left=4, top=8, right=4, bottom=8))
    field = ft.TextField(
        hint_text="Pose une question à l'assistant…",
        expand=True,
        border_radius=999,
        bgcolor=C.bg_subtle,
        border_color=C.border,
        focused_border_color=C.accent,
        color=C.text,
        hint_style=ft.TextStyle(color=C.text_subtle),
        text_size=FONT.body,
        content_padding=ft.Padding(left=18, top=12, right=18, bottom=12),
        on_submit=lambda e: send_message(e),
    )
    loading = ft.ProgressRing(visible=False, width=16, height=16,
                              color=C.accent, stroke_width=2)

    def _bubble(text, is_user):
        # Bubble user : violet accent à droite
        # Bubble assistant : sombre à gauche avec border accent gauche
        if is_user:
            return ft.Row(
                alignment=ft.MainAxisAlignment.END,
                controls=[
                    ft.Container(
                        content=ft.Text(text, selectable=True,
                                        color="#FFFFFF", size=FONT.body),
                        bgcolor=C.accent_strong,
                        padding=ft.Padding(left=14, top=10, right=14, bottom=10),
                        border_radius=18,
                        margin=ft.Margin(left=70, top=0, right=0, bottom=0),
                    ),
                ],
            )
        else:
            return ft.Row(
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Container(
                        width=28, height=28,
                        border_radius=999,
                        bgcolor=ft.Colors.with_opacity(0.18, C.accent),
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(ft.Icons.AUTO_AWESOME,
                                        color=C.accent, size=14),
                    ),
                    ft.Container(
                        content=ft.Text(text, selectable=True,
                                        color=C.text, size=FONT.body),
                        bgcolor=C.bg_elevated,
                        padding=ft.Padding(left=14, top=10, right=14, bottom=10),
                        border_radius=18,
                        border=ft.Border(
                            top=ft.BorderSide(1, C.border),
                            bottom=ft.BorderSide(1, C.border),
                            left=ft.BorderSide(1, C.border),
                            right=ft.BorderSide(1, C.border),
                        ),
                        margin=ft.Margin(left=10, top=0, right=60, bottom=0),
                        expand=True,
                    ),
                ],
            )

    def add_bubble(text, is_user=True, save=True):
        chat.controls.append(_bubble(text, is_user))
        if save:
            page._chat_history.append({"text": text, "is_user": is_user})
            # Limite à 30 messages
            if len(page._chat_history) > 30:
                page._chat_history = page._chat_history[-30:]
        page.update()

    # Restaurer l'historique
    for msg in page._chat_history:
        chat.controls.append(_bubble(msg["text"], msg["is_user"]))

    def send_message(e):
        msg = (field.value or "").strip()
        if not msg:
            return
        field.value = ""
        add_bubble(msg, is_user=True)
        loading.visible = True
        page.update()

        def call_agent():
            try:
                response = ask_agent(msg)
            except Exception as ex:
                response = f"Erreur : {ex}"
            loading.visible = False
            add_bubble(response, is_user=False)

        threading.Thread(target=call_agent, daemon=True).start()

    def clear_chat(e):
        chat.controls.clear()
        page._chat_history.clear()
        page.update()

    # ─────────────────────────────────────────
    # PUSH-TO-TALK : clic = écoute jusqu'au silence → transcription → champ
    # ─────────────────────────────────────────
    voice_state = {"recording": False, "lock": threading.Lock()}

    mic_btn = ft.IconButton(
        icon=ft.Icons.MIC_NONE_ROUNDED,
        icon_color=C.text_muted,
        icon_size=18,
        tooltip="Parler à l'assistant",
    )

    def _set_mic_idle():
        mic_btn.icon = ft.Icons.MIC_NONE_ROUNDED
        mic_btn.icon_color = C.text_muted
        mic_btn.bgcolor = None
        mic_btn.tooltip = "Parler à l'assistant"
        field.hint_text = "Pose une question à l'assistant…"

    def _set_mic_listening():
        mic_btn.icon = ft.Icons.MIC_ROUNDED
        mic_btn.icon_color = "#FFFFFF"
        mic_btn.bgcolor = C.danger
        mic_btn.tooltip = "Écoute en cours… reste silencieux pour terminer"
        field.hint_text = "🎙️ Écoute en cours, parle maintenant…"

    def _set_mic_processing():
        mic_btn.icon = ft.Icons.HOURGLASS_TOP_ROUNDED
        mic_btn.icon_color = C.accent
        mic_btn.bgcolor = None
        mic_btn.tooltip = "Transcription en cours…"
        field.hint_text = "Transcription en cours…"

    def voice_worker():
        try:
            # Import paresseux : si speech_recognition/pyaudio ne sont pas
            # installés, ça plante seulement ici, pas au chargement de l'app
            try:
                import speech_recognition as sr
            except ImportError as ex:
                add_bubble(
                    "Module 'speech_recognition' manquant. "
                    f"Installe-le avec : pip install SpeechRecognition pyaudio\n({ex})",
                    is_user=False, save=False)
                return

            recognizer = sr.Recognizer()
            recognizer.pause_threshold = 1.0  # 1s de silence = fin

            try:
                mic = sr.Microphone()
            except Exception as ex:
                add_bubble(
                    f"Micro indisponible (pyaudio manquant ou non autorisé) : {ex}",
                    is_user=False, save=False)
                return

            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.4)
                try:
                    audio_data = recognizer.listen(
                        source, timeout=8, phrase_time_limit=20)
                except sr.WaitTimeoutError:
                    add_bubble("⏱️ Aucun son détecté, réessaie.",
                               is_user=False, save=False)
                    return

            _set_mic_processing()
            page.update()

            try:
                text = recognizer.recognize_google(
                    audio_data, language="fr-FR")
            except sr.UnknownValueError:
                add_bubble("🤷 Je n'ai pas compris, peux-tu répéter ?",
                           is_user=False, save=False)
                return
            except sr.RequestError as ex:
                add_bubble(f"Erreur reconnaissance vocale : {ex}",
                           is_user=False, save=False)
                return

            if text:
                field.value = (field.value or "") + (
                    " " if field.value else "") + text

        except Exception as ex:
            add_bubble(f"Erreur micro : {ex}",
                       is_user=False, save=False)
        finally:
            voice_state["recording"] = False
            _set_mic_idle()
            page.update()

    def toggle_voice(e):
        with voice_state["lock"]:
            if voice_state["recording"]:
                # Déjà en train d'enregistrer — on ignore (sr.listen gère le silence)
                return
            voice_state["recording"] = True
        _set_mic_listening()
        page.update()
        threading.Thread(target=voice_worker, daemon=True).start()

    mic_btn.on_click = toggle_voice

    send_btn = ft.IconButton(
        icon=ft.Icons.ARROW_UPWARD_ROUNDED,
        icon_color="#FFFFFF",
        bgcolor=C.accent_strong,
        icon_size=18,
        on_click=send_message,
    )

    # Si historique vide, afficher un état "welcome"
    if not page._chat_history:
        chat.controls.append(
            ft.Container(
                padding=ft.Padding(left=10, top=40, right=10, bottom=10),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                    controls=[
                        ft.Container(
                            width=56, height=56,
                            border_radius=999,
                            bgcolor=ft.Colors.with_opacity(0.16, C.accent),
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(ft.Icons.AUTO_AWESOME,
                                            color=C.accent, size=24),
                        ),
                        ft.Text("Assistant", size=FONT.h2, color=C.text,
                                weight=ft.FontWeight.W_700),
                        ft.Text("Demande-lui un point marché, "
                                "un résumé de tes mails, "
                                "ou un récap de tes prochains RDV.",
                                size=FONT.small, color=C.text_subtle,
                                text_align=ft.TextAlign.CENTER),
                    ],
                ),
            )
        )

    # AppBar
    actions = [
        ft.IconButton(
            icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
            icon_color=C.text_muted, icon_size=18,
            tooltip="Effacer le chat",
            on_click=clear_chat,
        ),
        ft.Container(width=8),
    ]

    view = ft.View(
        route="/AI",
        padding=0,
        bgcolor=C.bg,
    )
    view.navigation_bar = build_navbar(page, selected=nav_index_for("/AI"))
    view.appbar = T.appbar("Assistant", actions=actions)

    view.controls = [
        ft.Container(
            expand=True,
            padding=ft.Padding(left=20, top=8, right=20, bottom=8),
            content=ft.Column(
                expand=True,
                controls=[
                    chat,
                    ft.Container(
                        padding=ft.Padding(left=4, top=8, right=4, bottom=4),
                        content=ft.Row(
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                field,
                                mic_btn,
                                loading,
                                send_btn,
                            ],
                        ),
                    ),
                ],
            ),
        ),
    ]

    return view