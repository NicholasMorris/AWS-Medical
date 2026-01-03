from shiny import App, ui, reactive, render
from pathlib import Path
import asyncio
import base64
import json
import sys
from uuid import uuid4
from pipeline_runner import run_transcription, generate_soap_and_outputs

# Determine project root so data paths resolve when running under `webapp`
HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
ASSETS = HERE / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

# Ensure the project root is on sys.path so `src` is importable when running from `webapp/`
sys.path.insert(0, str(HERE.parent.resolve()))

CSS = """
body { font-family: Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; margin: 20px; }
.uploader { border: 2px dashed #d0d7de; padding: 20px; border-radius: 8px; background: #fbfdff }
.results { margin-top: 16px; }
.card { background: white; border: 1px solid #e6eef4; padding: 12px; border-radius: 6px; box-shadow: 0 2px 6px rgba(20,20,20,0.03); }
pre { background: #0f172a; color: #e6eef4; padding: 12px; border-radius: 6px; overflow:auto }
"""


app_ui = ui.page_fluid(
    ui.tags.style(CSS),
    ui.h2("AWS-Medical: Clinical Pipeline UI"),
    ui.div(
        ui.input_file("audio", "Upload recording (.m4a or .wav)", multiple=False),
        ui.input_checkbox("dry_run", "Dry run (use sample outputs)", value=True),
        ui.p("Drag & drop or browse. After upload the pipeline runs automatically."),
        class_="uploader card"
    ),
    ui.output_text("status"),
    ui.output_ui("results_ui"),
)


def server(input, output, session):
    status = reactive.Value("Waiting for upload...")
    results_html = reactive.Value("")
    last_processed_upload = reactive.Value(None)

    @output
    @render.text
    def status_text():
        return status.get()

    @output
    @render.ui
    def results_ui():
        html = results_html.get()
        if html is None:
            return ui.div(ui.em("No results yet."), class_="card")
        if isinstance(html, str) and html.strip() == "":
            return ui.div(ui.em("No results yet."), class_="card")
        return ui.HTML(html)

    @reactive.Effect
    async def _process_file():
        upload_info = input.audio()
        if not upload_info:
            return
        info = upload_info[0] if isinstance(upload_info, list) else upload_info
        if getattr(_process_file, '_running', False):
            return
        key = (getattr(info, 'datapath', None) or
               info.get('datapath') if isinstance(info, dict) else None or
               info.get('file') if isinstance(info, dict) else None or
               info.get('name') if isinstance(info, dict) else None or
               getattr(info, 'name', None) or
               str(info))
        if key and last_processed_upload.get() == key:
            return
        if key:
            last_processed_upload.set(key)
        _process_file._running = True
        try:
            # copy file to recordings directory with unique name
            rec_dir = PROJECT_ROOT / "data" / "recordings"
            rec_dir.mkdir(parents=True, exist_ok=True)
            filename = info.get('name') if isinstance(info, dict) else getattr(info, 'name', None)
            if not filename:
                filename = info.get('filename') if isinstance(info, dict) else 'uploaded_audio.m4a'
            if not filename:
                filename = 'uploaded_audio.m4a'
            dest = rec_dir / f"{uuid4().hex}_{filename}"
            if isinstance(info, dict):
                filedata = info.get('datapath') or info.get('file') or info.get('data')
                if hasattr(filedata, 'read'):
                    with open(dest, "wb") as fh:
                        fh.write(filedata.read())
                elif isinstance(filedata, str):
                    with open(filedata, "rb") as src, open(dest, "wb") as fh:
                        fh.write(src.read())
                else:
                    raise ValueError("Unknown file data type in upload")
            else:
                with open(dest, "wb") as fh:
                    fh.write(info.read())

            progress_steps = [
                ("Uploading audio", "Uploading and saving your audio file..."),
                ("Transcribing", "Transcribing audio (AWS Transcribe)..."),
                ("Medical Analysis", "Extracting medical entities (Comprehend Medical)..."),
                ("SOAP Note", "Generating SOAP note (Bedrock)..."),
                ("Patient Artefacts", "Generating patient artefacts..."),
                ("Decision Support", "Generating decision support prompts...")
            ]
            progress_html = lambda step, msg: f"<div class='card' style='background:#f0f6ff'><b>Step {step+1}/{len(progress_steps)}:</b> {msg}</div>"

            running_cards: list[str] = []

            def render_results() -> None:
                if not running_cards:
                    results_html.set("<div class='card'><em>No results yet.</em></div>")
                    return
                results_html.set("".join(f"<div class='card'>{card}</div>" for card in running_cards))

            def download_button(label: str, filename: str, payload: str) -> str:
                return (f"<a download='{filename}' href='data:application/json;base64,{payload}' class='btn' "
                        "style='margin:8px 0;display:inline-block;background:#2563eb;color:white;padding:6px 16px;"
                        "border-radius:4px;text-decoration:none;font-weight:500'>{label}</a>")

            def add_text_card(title: str, text: str, download_name: str | None = None) -> None:
                download_html = ""
                if download_name:
                    encoded = base64.b64encode(text.encode()).decode()
                    download_html = download_button(f"Download {title}", download_name, encoded)
                running_cards.append(f"<h3>{title}</h3>{download_html}<pre>{text}</pre>")
                render_results()

            def add_message_card(message: str) -> None:
                running_cards.append(f"<p>{message}</p>")
                render_results()

            async def set_status(step_index: int, message: str) -> None:
                status.set(progress_html(step_index, message))
                await asyncio.sleep(0.08)

            def load_json_safe(path: Path) -> dict | None:
                if not path.exists():
                    return None
                try:
                    from src.common.io import load_json

                    return load_json(str(path))
                except Exception:
                    return None

            running_cards.clear()
            render_results()
            await set_status(0, progress_steps[0][1])

            dry_run_enabled = bool(input.dry_run())

            if dry_run_enabled:
                encounter = "cb12c4ce-a45b-4e8e-9a26-173fac708c50_1767469435"
                await set_status(1, progress_steps[1][1])
                med = load_json_safe(PROJECT_ROOT / "data" / "outputs" / f"medical_analysis_results_{encounter}.json")
                transcript = None
                if med:
                    transcript = (med.get('transcript') or med.get('full_transcript') or med.get('transcription'))
                    if not transcript and isinstance(med.get('transcripts'), list) and med['transcripts']:
                        transcript = med['transcripts'][0].get('text')
                if transcript:
                    add_text_card("Transcript", transcript, "transcript.txt")
                else:
                    add_message_card("Transcript not found in the dry-run sample.")
                await set_status(2, progress_steps[2][1])
                if med:
                    add_text_card("Medical Analysis", json.dumps(med, indent=2))
                else:
                    add_message_card("Medical analysis sample not found.")
                await set_status(3, progress_steps[3][1])
                soap_json = load_json_safe(PROJECT_ROOT / "data" / "outputs" / f"soap_output_{encounter}.json")
                if soap_json:
                    soap_note = soap_json.get('soap_note') or soap_json
                    add_text_card("SOAP Note", json.dumps(soap_note, indent=2), "soap_note.json")
                else:
                    add_message_card("SOAP note sample not found.")
                await set_status(4, progress_steps[4][1])
                patient_artefacts = load_json_safe(PROJECT_ROOT / "data" / "outputs" / f"patient_artefacts_{encounter}.json")
                if patient_artefacts:
                    add_text_card("Patient Artefacts", json.dumps(patient_artefacts, indent=2), "patient_artefacts.json")
                else:
                    add_message_card("Patient artefacts sample not found.")
                await set_status(5, progress_steps[5][1])
                decision_support = load_json_safe(PROJECT_ROOT / "data" / "outputs" / f"decision_support_{encounter}.json")
                if decision_support:
                    add_text_card("Decision Support", json.dumps(decision_support, indent=2), "decision_support.json")
                else:
                    add_message_card("Decision support sample not found.")
                status.set("<div class='card' style='background:#e0ffe0;color:#166534'><b>Dry run complete.</b></div>")
                return

            await set_status(1, progress_steps[1][1])
            try:
                transcript = await asyncio.to_thread(run_transcription, str(dest))
            except Exception:
                transcript = None
            if transcript:
                add_text_card("Transcript", transcript, "transcript.txt")
            else:
                add_message_card("Transcript could not be generated.")
            await set_status(2, progress_steps[2][1])
            await set_status(3, progress_steps[3][1])
            try:
                soap_results = await asyncio.to_thread(generate_soap_and_outputs, True, True)
            except Exception as exc:
                status.set(f"<div class='card' style='background:#ffeaea;color:#b91c1c'><b>Pipeline error:</b> {exc}</div>")
                return
            if soap_results.get('soap_note'):
                add_text_card("SOAP Note", json.dumps(soap_results['soap_note'], indent=2), "soap_note.json")
            if soap_results.get('patient_artefacts'):
                add_text_card("Patient Artefacts", json.dumps(soap_results['patient_artefacts'], indent=2), "patient_artefacts.json")
            if soap_results.get('decision_support'):
                add_text_card("Decision Support", json.dumps(soap_results['decision_support'], indent=2), "decision_support.json")
            if soap_results.get('errors'):
                add_message_card(f"Errors: {json.dumps(soap_results['errors'], indent=2)}")
            status.set("<div class='card' style='background:#e0ffe0;color:#166534'><b>Pipeline finished!</b></div>")
        finally:
            _process_file._running = False

        # Only run the pipeline once per upload
        if not getattr(_process_file, '_running', False):
            _process_file._running = True
            asyncio.create_task(_run_and_update())
            def reset_flag():
                _process_file._running = False
            asyncio.get_event_loop().call_later(2, reset_flag)

    return None


app = App(app_ui, server)
