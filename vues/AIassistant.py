import flet as ft
import threading
import os
from vues.navbar import build_navbar
from services.ai_agent import ask_agent

def build(page: ft.Page) -> ft.View:

    if not hasattr(page, "_chat_history"):
        page._chat_history = []

    chat = ft.ListView(expand=True, spacing=10, auto_scroll=True)
    field = ft.TextField(
        hint_text="Écris un message...",
        expand=True,
        on_submit=lambda e: send_message(e),
    )
    loading = ft.ProgressRing(visible=False, width=20, height=20)
    mic_btn = ft.IconButton(
        ft.Icons.MIC,
        icon_color="white",
        bgcolor="#1E293B",
        on_click=lambda e: start_voice(),
    )

    def add_bubble(text, is_user=True, save=True):
        chat.controls.append(
            ft.Container(
                content=ft.Text(text, selectable=True, color="white"),
                bgcolor="#2563EB" if is_user else "#1E293B",
                padding=12,
                border_radius=12,
                margin=ft.Margin(
                    left=80 if is_user else 0,
                    top=0,
                    right=0 if is_user else 80,
                    bottom=0,
                ),
            )
        )
        if save:
            page._chat_history.append({"text": text, "is_user": is_user})
        page.update()

    for msg in page._chat_history:
        add_bubble(msg["text"], msg["is_user"], save=False)

    def send_message(e):
        msg = field.value.strip()
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

        threading.Thread(target=call_agent).start()

    def start_voice():
        mic_btn.icon = ft.Icons.MIC_OFF
        mic_btn.bgcolor = "#DC2626"
        page.update()

        def listen():
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.Microphone() as source:
                print("Parlez...")
                r.pause_threshold = 1
                r.adjust_for_ambient_noise(source,) 
                audio = r.listen(source, timeout=10)
            try:
                command = r.recognize_google(audio, language="fr-FR")
                print(command)
            except sr.UnknownValueError:
                print("Désolé, je n'ai pas compris.")
            except sr.RequestError as e:
                print("Erreur de service; {0}".format(e))
                threading.Thread(target=listen).start()

    send_btn = ft.IconButton(ft.Icons.SEND, icon_color="white", on_click=send_message)

    def clear_chat(e):
        chat.controls.clear()
        page._chat_history.clear()
        from services.ai_agent import _history
        _history.clear()
        page.update()

    def handle_checked_item_click(e):
        e.control.checked = not e.control.checked
        page.update()

    view = ft.View(
        route=page.route,
        padding=0,
    )

    route_indexes = {"/": 0, "/mails": 1, "/rdv": 2, "AI": 3}
    current_index = route_indexes.get(page.route, 0)

    view.navigation_bar = build_navbar(page, current_index)
    view.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.SMART_TOY),
        leading_width=40,
        title=ft.Text("Assistant IA", font_family="PROSTO"),
        center_title=False,
        bgcolor=ft.Colors.BLUE_300,
        actions=[
            ft.IconButton(ft.Icons.WB_SUNNY_OUTLINED),
            ft.PopupMenuButton(
                items=[
                    ft.PopupMenuItem(
                        content=ft.Text("Effacer le chat"),
                        on_click=clear_chat,
                    ),
                    ft.PopupMenuItem(
                        content=ft.Text("Checked item"),
                        checked=False,
                        on_click=handle_checked_item_click,
                    ),
                ]
            ),
        ],
    )

    view.controls = [
        ft.Container(
            content=ft.Column([
                chat,
                ft.Row(
                    [field, mic_btn, loading, send_btn],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ], expand=True),
            expand=True,
            padding=10,
        )
    ]

    return view
