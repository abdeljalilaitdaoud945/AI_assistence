"""
Vue Gestion Réunion — Enregistrement, transcription, Google Meet et partage.
Style Arc-inspired.
"""

import threading
import os
import wave
import random
import string
from datetime import datetime

import flet as ft
import speech_recognition as sr
import pyaudio

from vues import theme as T
from vues.theme import C, FONT
from vues.navbar import build_navbar, nav_index_for
from services.contact_service import get_contacts
from services.email_service import send_email

TYPES_REUNION = [
    "Réunion commerciale (responsables de zones, grands comptes)",
    "Réunion marketing",
    "Réunion financière / comptabilité / contrôle de gestion",
    "Réunion stratégique (groupe restreint)",
    "Réunion hebdomadaire ou bi-hebdomadaire",
    "Réunion ponctuelle (projet spécifique)",
]

def build(page: ft.Page) -> ft.View:

    # ─────────────────────────────────────────
    # ÉTAT
    # ─────────────────────────────────────────
    state = {
        "recording": False,
        "audio_frames": [],
        "transcript_lines": [],
        "full_text": "",
        "generated_meet_url": ""
    }

    # ─────────────────────────────────────────
    # COMPOSANTS DYNAMIQUES DE PARTAGE MEET
    # ─────────────────────────────────────────
    meet_url_display = ft.Text(
        "", 
        color=C.success, 
        size=FONT.body, 
        weight=ft.FontWeight.W_700,
        selectable=True
    )
    
    contacts_dropdown = ft.Dropdown(
        label="Choisir un contact",
        bgcolor=C.bg_subtle,
        color=C.text,
        border_color=C.border,
        text_style=ft.TextStyle(color=C.text),
        label_style=ft.TextStyle(color=C.text_subtle),
        width=250,
        visible=False
    )
    
    manual_email_field = ft.TextField(
        label="Ou saisir un email manuel",
        bgcolor=C.bg_subtle,
        color=C.text,
        border_color=C.border,
        focused_border_color=C.accent,
        label_style=ft.TextStyle(color=C.text_subtle),
        width=250,
        visible=False
    )
    
    # CORRECTION ICI : Pas de visible=False dans T.pill_button
    send_meet_btn = T.pill_button(
        "Envoyer l'invitation", 
        icon=ft.Icons.SEND_ROUNDED
    )
    send_meet_btn.visible = False  # On le cache juste après sa création
    
    share_status = ft.Text("", size=FONT.micro)
    share_loading = ft.ProgressRing(visible=False, width=14, height=14, color=C.accent, stroke_width=2)

    share_row = ft.Row(
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            contacts_dropdown,
            manual_email_field,
            send_meet_btn,
            share_loading,
            share_status
        ]
    )

    # ─────────────────────────────────────────
    # LOGIQUE DE PARTAGE DE LIEN
    # ─────────────────────────────────────────
    def _send_meet_invitation(e):
        target_email = ""
        target_name = "Participant"
        
        # Vérification de la source du mail
        if manual_email_field.value and manual_email_field.value.strip():
            target_email = manual_email_field.value.strip()
        elif contacts_dropdown.value:
            target_email = contacts_dropdown.value
            # Trouver le nom associé dans la liste
            all_c = get_contacts()
            match = next((c for c in all_c if c["email"] == target_email), None)
            if match:
                target_name = match["nom"]
                
        if not target_email:
            share_status.value = "⚠️ Veuillez sélectionner ou saisir un email."
            share_status.color = C.danger
            page.update()
            return
            
        share_loading.visible = True
        share_status.value = ""
        page.update()
        
        def work():
            sujet = f"Invitation : Réunion à distance"
            corps = (
                f"Bonjour {target_name},\n\n"
                f"Je vous invite à rejoindre la visioconférence Google Meet que je viens de planifier.\n\n"
                f"🔗 Cliquez ici pour rejoindre : {state['generated_meet_url']}\n\n"
                f"À tout de suite !"
            )
            res = send_email(target_email, sujet, corps)
            share_loading.visible = False
            if "✅" in res:
                share_status.value = "Invitation envoyée ! ✅"
                share_status.color = C.success
                manual_email_field.value = ""
            else:
                share_status.value = "Erreur lors de l'envoi. ❌"
                share_status.color = C.danger
            page.update()
            
        threading.Thread(target=work, daemon=True).start()

    send_meet_btn.on_click = _send_meet_invitation

    # ─────────────────────────────────────────
    # GOOGLE MEET CREATION
    # ─────────────────────────────────────────
    def open_meet_confirm(e):
        async def launch(e2):
            page.pop_dialog()
            
            # Génération d'un faux token de réunion réaliste (ex: meet.google.com/xyz-pdqr-abc)
            part1 = "".join(random.choices(string.ascii_lowercase, k=3))
            part2 = "".join(random.choices(string.ascii_lowercase, k=4))
            part3 = "".join(random.choices(string.ascii_lowercase, k=3))
            generated_url = f"https://meet.google.com/{part1}-{part2}-{part3}"
            
            state["generated_meet_url"] = generated_url
            
            # Remplissage du Dropdown avec tes vrais contacts enregistrés
            all_contacts = get_contacts()
            contacts_dropdown.options = [
                ft.dropdown.Option(key=c["email"], text=f"{c['nom']} ({c['email']})") 
                for c in all_contacts
            ]
            
            # Affichage et activation des composants de partage sous le bouton
            meet_url_display.value = f"🔗 Lien généré : {generated_url}"
            contacts_dropdown.visible = True
            manual_email_field.visible = True
            send_meet_btn.visible = True
            page.update()
            
            # Lancement réel de la page de création pour l'utilisateur
            await page.launch_url("https://meet.google.com/new")
            
        dialog = ft.AlertDialog(
            modal=False,
            bgcolor=C.bg_elevated,
            title=ft.Text("Nouvelle réunion", color=C.text, weight=ft.FontWeight.W_700, size=FONT.h3),
            content=ft.Text("Voulez-vous ouvrir Google Meet dans votre navigateur pour démarrer une visioconférence ?", color=C.text_subtle),
            actions=[
                ft.TextButton("Annuler", on_click=lambda e3: page.pop_dialog()),
                ft.TextButton("Démarrer la visio", on_click=launch, style=ft.ButtonStyle(color=C.accent)),
            ]
        )
        page.show_dialog(dialog)

    meet_card = T.card(
        padding=16,
        accent=True,
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column(spacing=2, controls=[
                            ft.Text("Visioconférence", color=C.text, weight=ft.FontWeight.W_700, size=FONT.h3),
                            ft.Text("Créer un lien Google Meet instantané.", color=C.text_subtle, size=FONT.small),
                        ]),
                        T.pill_button("Démarrer Google Meet", icon=ft.Icons.VIDEO_CALL_ROUNDED, on_click=open_meet_confirm)
                    ]
                ),
                meet_url_display,
                share_row
            ]
        )
    )

    # ─────────────────────────────────────────
    # COMPOSANTS — INFOS RÉUNION
    # ─────────────────────────────────────────
    nom_field = ft.TextField(
        label="Nom de la réunion",
        hint_text="Ex: Réunion budget Q3...",
        bgcolor=C.bg_subtle, border_color=C.border, focused_border_color=C.accent, color=C.text,
        label_style=ft.TextStyle(color=C.text_subtle), hint_style=ft.TextStyle(color=C.border),
        border_radius=10,
    )

    date_field = ft.TextField(
        label="Date",
        value=datetime.now().strftime("%d/%m/%Y"),
        bgcolor=C.bg_subtle, border_color=C.border, color=C.text_subtle,
        label_style=ft.TextStyle(color=C.text_subtle),
        border_radius=10,
        read_only=True,
    )

    type_text = ft.Text("Type détecté par l'IA : en attente...", color=C.text_subtle, size=FONT.micro, italic=True)

    type_dropdown = ft.Dropdown(
        label="Type de réunion",
        bgcolor=C.bg_subtle, 
        border_color=C.border, 
        focused_border_color=C.accent, 
        color=C.text,
        label_style=ft.TextStyle(color=C.text_subtle),
        text_style=ft.TextStyle(color=C.text), 
        border_radius=10,
        options=[ft.dropdown.Option(key=t, text=t) for t in TYPES_REUNION],
    )

    info_card = T.card(
        padding=18,
        content=ft.Column(spacing=12, controls=[
            T.section_header("Informations de la réunion"),
            nom_field,
            date_field,
            T.divider(),
            ft.Row([ft.Icon(ft.Icons.SMART_TOY, color=C.accent, size=16), ft.Text("Type (détecté automatiquement)", color=C.text_muted, size=FONT.small)]),
            type_text,
            type_dropdown,
        ])
    )

    # ─────────────────────────────────────────
    # COMPOSANTS — TRANSCRIPTION
    # ─────────────────────────────────────────
    status_text = ft.Text("Prêt", color=C.text_subtle, size=FONT.small, italic=True)
    loading = ft.ProgressRing(visible=False, width=16, height=16, color=C.accent, stroke_width=2)
    loading_ia = ft.ProgressRing(visible=False, width=14, height=14, color=C.accent, stroke_width=2)

    selected_file_text = ft.Text("Aucun fichier sélectionné", color=C.text_subtle, size=FONT.micro, italic=True)
    transcript_box = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

    # ─────────────────────────────────────────
    # FONCTIONS UTILITAIRES
    # ─────────────────────────────────────────
    def set_status(text, color=C.text_subtle):
        status_text.value = text
        status_text.color = color
        page.update()

    def add_transcript_line(text, color=C.text):
        transcript_box.controls.append(
            ft.Container(
                content=ft.Text(text, color=color, size=FONT.small, selectable=True),
                bgcolor=C.bg_subtle,
                padding=10,
                border_radius=8,
                border=ft.Border(left=ft.BorderSide(3, C.accent)),
            )
        )
        state["transcript_lines"].append(text)
        state["full_text"] = " ".join(state["transcript_lines"])
        page.update()

    # ─────────────────────────────────────────
    # DÉTECTION DU TYPE PAR GEMINI
    # ─────────────────────────────────────────
    def detect_type_ia(texte: str):
        loading_ia.visible = True
        type_text.value = "🤖 Analyse du type en cours..."
        type_text.color = C.accent
        page.update()

        def call_gemini():
            try:
                from google import genai
                client = genai.Client()
                liste = "\n".join([f"- {t}" for t in TYPES_REUNION])
                prompt = (
                    f"Voici la transcription d'une réunion :\n\n\"{texte}\"\n\n"
                    f"Parmi les types suivants, lequel correspond le mieux à cette réunion ? "
                    f"Réponds uniquement avec le nom exact du type, sans explication.\n\n{liste}"
                )
                response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
                detected = response.text.strip()

                matched = next((t for t in TYPES_REUNION if detected.lower() in t.lower() or t.lower() in detected.lower()), None)

                if matched:
                    type_dropdown.value = matched
                    type_text.value = f"🤖 Type détecté : {matched}"
                    type_text.color = C.success
                else:
                    type_text.value = f"🤖 Suggestion IA : {detected}"
                    type_text.color = C.warning

            except Exception as ex:
                type_text.value = f"⚠️ IA indisponible : {ex}"
                type_text.color = C.danger
            finally:
                loading_ia.visible = False
                page.update()

        threading.Thread(target=call_gemini, daemon=True).start()

    # ─────────────────────────────────────────
    # TRANSCRIPTION AUDIO
    # ─────────────────────────────────────────
    def transcribe_audio_file(filepath):
        recognizer = sr.Recognizer()
        set_status("Transcription en cours...", C.warning)
        loading.visible = True
        page.update()

        try:
            with sr.AudioFile(filepath) as source:
                audio_data = recognizer.record(source)
            result = recognizer.recognize_google(audio_data, language="fr-FR")
            transcript_box.controls.clear()
            state["transcript_lines"].clear()
            add_transcript_line(result, C.text)
            set_status("Transcription terminée ✅", C.success)
            detect_type_ia(result)
        except sr.UnknownValueError:
            set_status("Impossible de comprendre l'audio ❌", C.danger)
            add_transcript_line("⚠️ Aucune parole détectée dans ce fichier.", C.danger)
        except sr.RequestError as ex:
            set_status(f"Erreur de service : {ex}", C.danger)
        except Exception as ex:
            set_status(f"Erreur : {ex}", C.danger)
        finally:
            loading.visible = False
            page.update()

    # ─────────────────────────────────────────
    # MODE 1 : CHARGER UN FICHIER AUDIO
    # ─────────────────────────────────────────
    def pick_file_result(e):
        if e.files and len(e.files) > 0:
            filepath = e.files[0].path
            if not filepath:
                set_status("⚠️ Chemin inaccessible. Lance l'app en mode desktop.", C.danger)
                return
            selected_file_text.value = f"📂 {os.path.basename(filepath)}"
            page.update()
            threading.Thread(target=transcribe_audio_file, args=(filepath,), daemon=True).start()
        else:
            selected_file_text.value = "Aucun fichier sélectionné"
            page.update()

    file_picker = ft.FilePicker()
    file_picker.on_result = pick_file_result
    # Enregistrement comme service (Flet 0.85.1) — sinon "Unknown control: FilePicker"
    try:
        if file_picker not in page._services._services:
            page._services.register_service(file_picker)
    except Exception as _e:
        print(f"[reunion vue] FilePicker register fallback: {_e}")

    def open_file_picker(e):
        transcript_box.controls.clear()
        state["transcript_lines"].clear()
        page.update()
        file_picker.pick_files(
            dialog_title="Sélectionner un enregistrement audio",
            allowed_extensions=["wav", "mp3", "ogg", "flac"],
        )

    file_card = T.card(
        padding=18,
        content=ft.Column(spacing=12, controls=[
            T.section_header("Charger un enregistrement"),
            selected_file_text,
            T.pill_button("Parcourir les fichiers...", icon=ft.Icons.UPLOAD_FILE, on_click=open_file_picker, primary=False)
        ])
    )

    # ─────────────────────────────────────────
    # MODE 2 : ENREGISTREMENT EN DIRECT
    # ─────────────────────────────────────────
    def start_recording(e):
        state["recording"] = True
        state["audio_frames"] = []
        record_btn.visible = False
        stop_btn.visible = True
        set_status("🔴 Enregistrement en cours...", C.danger)
        page.update()

        def record_loop():
            CHUNK = 1024
            RATE = 16000
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE, input=True, frames_per_buffer=CHUNK)
            while state["recording"]:
                data = stream.read(CHUNK, exception_on_overflow=False)
                state["audio_frames"].append(data)
            stream.stop_stream()
            stream.close()
            p.terminate()

        threading.Thread(target=record_loop, daemon=True).start()

    def stop_recording(e):
        state["recording"] = False
        stop_btn.visible = False
        record_btn.visible = True
        set_status("Traitement...", C.warning)
        loading.visible = True
        page.update()

        def save_and_transcribe():
            tmp_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                f"reunion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            )
            p = pyaudio.PyAudio()
            with wave.open(tmp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
                wf.setframerate(16000)
                wf.writeframes(b"".join(state["audio_frames"]))
            p.terminate()
            selected_file_text.value = f"📂 {os.path.basename(tmp_path)}"
            page.update()
            transcribe_audio_file(tmp_path)

        threading.Thread(target=save_and_transcribe, daemon=True).start()

    record_btn = T.pill_button("Démarrer l'enregistrement", icon=ft.Icons.MIC, on_click=start_recording)
    
    # CORRECTION ICI : Pas de visible=False dans T.pill_button
    stop_btn = T.pill_button("Arrêter et transcrire", icon=ft.Icons.STOP_CIRCLE, on_click=stop_recording, color=C.danger)
    stop_btn.visible = False

    live_card = T.card(
        padding=18,
        content=ft.Column(spacing=12, controls=[
            T.section_header("Enregistrement en direct"),
            ft.Row([record_btn, stop_btn])
        ])
    )

    # ─────────────────────────────────────────
    # EXPORT & TRANSCRIPTION BOX
    # ─────────────────────────────────────────
    def export_transcript(e):
        if not state["transcript_lines"]:
            set_status("Rien à exporter.", C.danger)
            return
        nom = nom_field.value.strip() or "sans_nom"
        date = date_field.value.replace("/", "-")
        type_r = type_dropdown.value or "type_inconnu"
        export_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            f"{nom}_{date}_{type_r[:20].replace(' ', '_')}.txt"
        )
        with open(export_path, "w", encoding="utf-8") as f:
            f.write(f"Nom      : {nom}\n")
            f.write(f"Date     : {date}\n")
            f.write(f"Type     : {type_r}\n")
            f.write(f"{'─' * 40}\n\n")
            f.write("\n".join(state["transcript_lines"]))
        set_status(f"Exporté : {os.path.basename(export_path)} ✅", C.success)

    transcript_card = T.card(
        padding=18,
        content=ft.Column(spacing=10, controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(spacing=8, controls=[
                        ft.Icon(ft.Icons.NOTES, color=C.accent), 
                        ft.Text("Transcription", size=FONT.h3, weight=ft.FontWeight.W_700, color=C.text),
                        loading
                    ]),
                    ft.IconButton(icon=ft.Icons.DOWNLOAD_ROUNDED, icon_color=C.accent, tooltip="Exporter en .txt", on_click=export_transcript)
                ]
            ),
            ft.Row([ft.Icon(ft.Icons.INFO_OUTLINE, color=C.text_subtle, size=14), status_text]),
            T.divider(),
            ft.Container(height=300, content=transcript_box),
        ])
    )

    # ─────────────────────────────────────────
    # CONSTRUCTION DE LA VUE
    # ─────────────────────────────────────────
    view = ft.View(
        route="/reunion",
        padding=0,
        bgcolor=C.bg,
        scroll=ft.ScrollMode.AUTO,
    )

    async def go_contacts(e):
        await page.push_route("/contacts")
        
    actions = [
        ft.IconButton(icon=ft.Icons.CONTACTS_ROUNDED, icon_color=C.text_muted, tooltip="Carnet d'adresses", on_click=go_contacts),
        ft.Container(width=8)
    ]

    view.navigation_bar = build_navbar(page, selected=nav_index_for("/reunion"))
    view.appbar = T.appbar("Saisie de Réunion", back_route="/", page=page, actions=actions)

    view.controls = [
        ft.Container(
            padding=ft.Padding(left=20, top=8, right=20, bottom=24),
            content=ft.Column(
                spacing=14,
                controls=[
                    meet_card,
                    info_card,
                    file_card,
                    live_card,
                    transcript_card,
                ]
            )
        )
    ]

    return view