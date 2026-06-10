import flet as ft
import threading
import os
import wave
import pyaudio
import speech_recognition as sr
from datetime import datetime
from vues.navbar import build_navbar


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
    }

    # ─────────────────────────────────────────
    # COMPOSANTS — INFOS RÉUNION
    # ─────────────────────────────────────────

    nom_field = ft.TextField(
        label="Nom de la réunion",
        hint_text="Ex: Réunion budget Q3...",
        color="white",
        label_style=ft.TextStyle(color="#94A3B8"),
        hint_style=ft.TextStyle(color="#475569"),
        bgcolor="#0F172A",
        border_color="#2563EB",
        focused_border_color="#38BDF8",
        cursor_color="white",
        border_radius=10,
    )

    date_field = ft.TextField(
        label="Date",
        value=datetime.now().strftime("%d/%m/%Y"),
        color="white",
        label_style=ft.TextStyle(color="#94A3B8"),
        bgcolor="#0F172A",
        border_color="#334155",
        border_radius=10,
        read_only=True,
    )

    type_text = ft.Text(
        "Type détecté par l'IA : en attente...",
        color="#64748B",
        size=12,
        italic=True,
    )

    type_dropdown = ft.Dropdown(
        label="Type de réunion",
        label_style=ft.TextStyle(color="#94A3B8"),
        bgcolor="#0F172A",
        color="white",
        border_color="#2563EB",
        focused_border_color="#38BDF8",
        border_radius=10,
        options=[ft.dropdown.Option(t) for t in TYPES_REUNION],
    )

    # ─────────────────────────────────────────
    # COMPOSANTS — TRANSCRIPTION
    # ─────────────────────────────────────────

    status_text = ft.Text("Prêt", color="#64748B", size=13, italic=True)
    loading = ft.ProgressRing(visible=False, width=20, height=20, color="#38BDF8", stroke_width=3)
    loading_ia = ft.ProgressRing(visible=False, width=16, height=16, color="#A78BFA", stroke_width=2)

    selected_file_text = ft.Text(
        "Aucun fichier sélectionné",
        color="#64748B",
        size=12,
        italic=True,
    )

    transcript_box = ft.Column(
        spacing=8,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    record_btn = ft.ElevatedButton(
        content=ft.Row([
            ft.Icon(ft.Icons.MIC, color="white"),
            ft.Text("Démarrer l'enregistrement", color="white", weight=ft.FontWeight.BOLD),
        ], alignment=ft.MainAxisAlignment.CENTER),
        bgcolor="#2563EB",
        height=50,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
    )

    stop_btn = ft.ElevatedButton(
        content=ft.Row([
            ft.Icon(ft.Icons.STOP_CIRCLE, color="white"),
            ft.Text("Arrêter et transcrire", color="white", weight=ft.FontWeight.BOLD),
        ], alignment=ft.MainAxisAlignment.CENTER),
        bgcolor="#DC2626",
        height=50,
        visible=False,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
    )

    # ─────────────────────────────────────────
    # FONCTIONS UTILITAIRES
    # ─────────────────────────────────────────

    def set_status(text, color="#64748B"):
        status_text.value = text
        status_text.color = color
        page.update()

    def add_transcript_line(text, color="#E2E8F0"):
        transcript_box.controls.append(
            ft.Container(
                content=ft.Text(text, color=color, size=13, selectable=True),
                bgcolor="#1E293B",
                padding=10,
                border_radius=8,
                border=ft.Border(left=ft.BorderSide(3, "#2563EB")),
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
        type_text.color = "#A78BFA"
        page.update()

        def call_gemini():
            try:
                from google import genai
                from google.genai import types
                from dotenv import load_dotenv
                load_dotenv()

                client = genai.Client()
                liste = "\n".join([f"- {t}" for t in TYPES_REUNION])
                prompt = (
                    f"Voici la transcription d'une réunion :\n\n\"{texte}\"\n\n"
                    f"Parmi les types suivants, lequel correspond le mieux à cette réunion ? "
                    f"Réponds uniquement avec le nom exact du type, sans explication.\n\n{liste}"
                )
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                )
                detected = response.text.strip()

                # Vérifier si la réponse correspond à un type connu
                matched = next((t for t in TYPES_REUNION if detected.lower() in t.lower() or t.lower() in detected.lower()), None)

                if matched:
                    type_dropdown.value = matched
                    type_text.value = f"🤖 Type détecté : {matched}"
                    type_text.color = "#10B981"
                else:
                    type_text.value = f"🤖 Suggestion IA : {detected}"
                    type_text.color = "#F59E0B"

            except Exception as ex:
                type_text.value = f"⚠️ IA indisponible : {ex}"
                type_text.color = "#EF4444"
            finally:
                loading_ia.visible = False
                page.update()

        threading.Thread(target=call_gemini).start()

    # ─────────────────────────────────────────
    # TRANSCRIPTION AUDIO
    # ─────────────────────────────────────────

    def transcribe_audio_file(filepath):
        recognizer = sr.Recognizer()
        set_status("Transcription en cours...", "#F59E0B")
        loading.visible = True
        page.update()

        try:
            with sr.AudioFile(filepath) as source:
                audio_data = recognizer.record(source)
            result = recognizer.recognize_google(audio_data, language="fr-FR")
            transcript_box.controls.clear()
            state["transcript_lines"].clear()
            add_transcript_line(result, "#E2E8F0")
            set_status("Transcription terminée ✅", "#10B981")
            # Lancer la détection automatique du type
            detect_type_ia(result)
        except sr.UnknownValueError:
            set_status("Impossible de comprendre l'audio ❌", "#EF4444")
            add_transcript_line("⚠️ Aucune parole détectée dans ce fichier.", "#EF4444")
        except sr.RequestError as ex:
            set_status(f"Erreur de service : {ex}", "#EF4444")
        except Exception as ex:
            set_status(f"Erreur : {ex}", "#EF4444")
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
                set_status("⚠️ Chemin inaccessible. Lance l'app en mode desktop (ft.app).", "#EF4444")
                return
            selected_file_text.value = f"📂 {os.path.basename(filepath)}"
            page.update()
            threading.Thread(target=transcribe_audio_file, args=(filepath,)).start()
        else:
            selected_file_text.value = "Aucun fichier sélectionné"
            page.update()

    file_picker = ft.FilePicker()
    file_picker.on_result = pick_file_result

    def open_file_picker(e):
        transcript_box.controls.clear()
        state["transcript_lines"].clear()
        page.update()
        file_picker.pick_files(
            dialog_title="Sélectionner un enregistrement audio",
            allowed_extensions=["wav", "mp3", "ogg", "flac"],
        )

    # ─────────────────────────────────────────
    # MODE 2 : ENREGISTREMENT EN DIRECT
    # ─────────────────────────────────────────

    def start_recording(e):
        state["recording"] = True
        state["audio_frames"] = []
        record_btn.visible = False
        stop_btn.visible = True
        set_status("🔴 Enregistrement en cours...", "#EF4444")
        page.update()

        def record_loop():
            CHUNK = 1024
            RATE = 16000
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
            )
            while state["recording"]:
                data = stream.read(CHUNK, exception_on_overflow=False)
                state["audio_frames"].append(data)
            stream.stop_stream()
            stream.close()
            p.terminate()

        threading.Thread(target=record_loop).start()

    def stop_recording(e):
        state["recording"] = False
        stop_btn.visible = False
        record_btn.visible = True
        set_status("Traitement...", "#F59E0B")
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

        threading.Thread(target=save_and_transcribe).start()

    record_btn.on_click = start_recording
    stop_btn.on_click = stop_recording

    # ─────────────────────────────────────────
    # EXPORT
    # ─────────────────────────────────────────

    def export_transcript(e):
        if not state["transcript_lines"]:
            set_status("Rien à exporter.", "#EF4444")
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
        set_status(f"Exporté : {os.path.basename(export_path)} ✅", "#10B981")

    # ─────────────────────────────────────────
    # CONSTRUCTION DE LA VUE
    # ─────────────────────────────────────────

    view = ft.View(
        route="/gestion_reunion",
        padding=20,
        bgcolor="#0B1220",
        scroll=ft.ScrollMode.AUTO,
    )

    view.navigation_bar = build_navbar(page, selected=4)

    view.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.MIC_EXTERNAL_ON, color="white"),
        leading_width=40,
        title=ft.Text("Gestion Réunion", font_family="PROSTO"),
        center_title=False,
        bgcolor=ft.Colors.BLUE_300,
    )

    view.controls = [

        # ── 1. INFOS RÉUNION ──
        ft.Container(
            padding=20,
            border_radius=15,
            bgcolor="#111827",
            shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK)),
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.EDIT_NOTE, color="#38BDF8"),
                    ft.Text("Informations de la réunion", size=16, weight=ft.FontWeight.BOLD, color="white"),
                ], spacing=10),
                ft.Divider(color="#1E293B"),
                nom_field,
                date_field,
                ft.Divider(color="#1E293B"),
                ft.Row([
                    ft.Icon(ft.Icons.SMART_TOY, color="#A78BFA", size=16),
                    ft.Text("Type (détecté automatiquement)", color="#94A3B8", size=13),
                    loading_ia,
                ], spacing=8),
                type_text,
                type_dropdown,
            ], spacing=12),
        ),

        ft.Container(height=15),

        # ── 2. CHARGER UN FICHIER ──
        ft.Container(
            padding=20,
            border_radius=15,
            bgcolor="#111827",
            shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK)),
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.FOLDER_OPEN, color="#38BDF8"),
                    ft.Text("Charger un enregistrement", size=16, weight=ft.FontWeight.BOLD, color="white"),
                ], spacing=10),
                ft.Divider(color="#1E293B"),
                selected_file_text,
                ft.ElevatedButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.UPLOAD_FILE, color="white"),
                        ft.Text("Parcourir...", color="white", weight=ft.FontWeight.BOLD),
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    bgcolor="#0F172A",
                    height=45,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                        side=ft.BorderSide(1, "#38BDF8"),
                    ),
                    on_click=open_file_picker,
                ),
            ], spacing=12),
        ),

        ft.Container(height=15),

        # ── 3. ENREGISTREMENT EN DIRECT ──
        ft.Container(
            padding=20,
            border_radius=15,
            bgcolor="#111827",
            shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK)),
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.RADIO_BUTTON_CHECKED, color="#EF4444"),
                    ft.Text("Enregistrement en direct", size=16, weight=ft.FontWeight.BOLD, color="white"),
                ], spacing=10),
                ft.Divider(color="#1E293B"),
                record_btn,
                stop_btn,
            ], spacing=12),
        ),

        ft.Container(height=15),

        # ── 4. TRANSCRIPTION ──
        ft.Container(
            padding=20,
            border_radius=15,
            bgcolor="#111827",
            shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK)),
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.NOTES, color="#10B981"),
                    ft.Text("Transcription", size=16, weight=ft.FontWeight.BOLD, color="white"),
                    loading,
                    ft.Container(expand=True),
                    ft.IconButton(
                        icon=ft.Icons.DOWNLOAD,
                        icon_color="#10B981",
                        tooltip="Exporter en .txt",
                        on_click=export_transcript,
                    ),
                ], alignment=ft.MainAxisAlignment.START),
                ft.Row([
                    ft.Icon(ft.Icons.INFO_OUTLINE, color="#64748B", size=14),
                    status_text,
                ]),
                ft.Divider(color="#1E293B"),
                ft.Container(
                    height=300,
                    content=transcript_box,
                ),
            ], spacing=10),
        ),

        ft.Container(height=20),
        file_picker,
    ]

    return view
