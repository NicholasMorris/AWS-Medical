from datetime import datetime
from pathlib import Path
import json
import re
import html as _html
try:
    import markdown as _markdown
except Exception:
    _markdown = None
from htmltools import HTML
from shiny import App, reactive, render, ui

OUTPUTS_DIR = Path(__file__).resolve().parents[1] / "data" / "outputs"


def _format_timestamp(ts: int | None) -> str:
    if not isinstance(ts, (int, float)):
        return "Unknown"
    try:
        return datetime.utcfromtimestamp(ts).strftime("%b %d · %H:%M UTC")
    except Exception:
        return "Unknown"


def _scan_analysis_choices() -> dict[str, str]:
    files = sorted(OUTPUTS_DIR.glob("medical_analysis_results_*.json"), reverse=True)
    choices: dict[str, str] = {}
    for path in files:
        label = path.name
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            encounter = payload.get("encounter_id") or "unknown"
            timestamp = payload.get("timestamp")
            label = f"{encounter[:8]} · { _format_timestamp(timestamp)}"
        except Exception:
            pass
        choices[str(path.name)] = str(label)
    return choices


def _load_json(path: Path | None) -> dict | None:
    if not path or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _latest_file(prefix: str, encounter_id: str | None) -> Path | None:
    if not encounter_id:
        return None
    pattern = f"{prefix}_{encounter_id}_*.json"
    matches = sorted(OUTPUTS_DIR.glob(pattern), reverse=True)
    return matches[0] if matches else None


ANALYSIS_CHOICES = _scan_analysis_choices()
DEFAULT_SELECTION = next(iter(ANALYSIS_CHOICES), None)

CSS = """
:root {
    --bg-start: #030712;
    --bg-end: #0c1d3a;
    --card: rgba(9, 19, 45, 0.9);
    --border: rgba(255, 255, 255, 0.08);
    --accent: #fb923c;
    --accent-soft: rgba(251, 146, 60, 0.15);
    --text-muted: rgba(255, 255, 255, 0.7);
}
body {
    margin: 0;
    background: radial-gradient(circle at top, #0b325e, transparent 55%),
        linear-gradient(180deg, var(--bg-start), var(--bg-end));
    color: #f8fafc;
    font-family: "Space Grotesk", "Inter", system-ui, sans-serif;
    min-height: 100vh;
}
.hero {
    padding: 40px 48px;
    border-radius: 24px;
    background: linear-gradient(135deg, rgba(15, 118, 255, 0.25), rgba(3, 10, 27, 0.8));
    margin: 24px 48px 0px;
    box-shadow: 0 25px 60px rgba(2, 6, 23, 0.6);
    border: 1px solid var(--border);
}
.control-row {
    margin-top: 18px;
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
}
.control-row .shiny-input-select,
.control-row .shiny-input-checkbox {
    flex: 1 1 320px;
    max-width: 420px;
}
.content-grid {
    margin: 32px 48px 48px;
    display: grid;
    /* Stack panes vertically by default for better readability */
    grid-template-columns: 1fr;
    gap: 24px;
}

@media (min-width: 1100px) {
    .content-grid {
        /* two-column layout on wide screens */
        grid-template-columns: 1fr 1fr;
    }
}
.panel {
    padding: 24px;
    border-radius: 20px;
    background: var(--card);
    border: 1px solid var(--border);
    box-shadow: 0 25px 35px rgba(2, 6, 23, 0.5);
}
.panel span {
    color: var(--text-muted);
}
.entity-item {
    padding: 12px;
    border-radius: 10px;
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.04);
    margin-bottom: 8px;
}
.entity-type {
    font-weight: 700;
    color: var(--accent);
    margin-right: 8px;
}
.speaker-badge {
    display: inline-block;
    background: rgba(255,255,255,0.03);
    padding: 6px 10px;
    border-radius: 999px;
    border: 1px solid rgba(255,255,255,0.04);
    margin-right: 8px;
    font-size: 0.85rem;
}
.decision-card {
    padding: 12px;
    border-radius: 12px;
    background: linear-gradient(180deg, rgba(251,146,60,0.06), rgba(251,146,60,0.02));
    border: 1px solid rgba(251,146,60,0.12);
    margin-bottom: 8px;
}
.checklist {
    list-style: none;
    padding-left: 0;
}
.checklist li::before {
    content: "☐";
    display: inline-block;
    width: 1.2em;
    margin-right: 8px;
    color: var(--accent);
}
.meta-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px;
    margin-bottom: 16px;
    font-size: 0.95rem;
}
.meta-grid .meta-item {
    padding: 12px;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.08);
}
.text-block {
    max-height: 320px;
    overflow: auto;
    margin-top: 12px;
}
.text-block pre,
.mono-block {
    font-family: "Space Mono", "JetBrains Mono", monospace;
    background: rgba(255, 255, 255, 0.04);
    color: #e6eef8;
    padding: 16px;
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    overflow-x: auto;
    line-height: 1.45;
}
.analysis-grid {
    margin-top: 24px;
    display: grid;
    grid-template-columns: 1fr;
    gap: 24px;
}
.soap-grid {
    display: grid;
    /* Force vertical stacking so SOAP sections appear one per row */
    grid-template-columns: 1fr;
    gap: 16px;
    margin-top: 16px;
}
.soap-section {
    border-radius: 16px;
    border: 1px solid rgba(255, 255, 255, 0.05);
    padding: 12px;
    background: rgba(255, 255, 255, 0.02);
    color: #e6eef8;
}
.decision-list {
    list-style: decimal inside;
    padding-left: 0;
    margin-top: 12px;
}
.decision-list li {
    padding: 8px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.decision-list li:last-child {
    border-bottom: none;
}
.placeholder-panel {
    text-align: center;
    padding-top: 40px;
    color: rgba(248, 250, 252, 0.6);
}
.badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    border-radius: 999px;
    border: 1px solid var(--accent);
    background: var(--accent-soft);
    font-size: 0.85rem;
    color: var(--accent);
}
"""


app_ui = ui.page_fluid(
    ui.tags.style(CSS),
    ui.div(
        ui.div(
            ui.h1("Clinical Encounter Explorer"),
            ui.p(
                "Browse generated analysis, SOAP notes, patient artefacts, and decision support prompts in a single dashboard.",
                class_="text-muted",
            ),
            ui.div(
                ui.input_select(
                    "analysis_choice",
                    "Select encounter",
                    choices=ANALYSIS_CHOICES,
                    selected=DEFAULT_SELECTION,
                    width="100%",
                ),
                class_="control-row",
            ),
        ),
        class_="hero",
    ),
    ui.div(
        ui.output_ui("analysis_pane"),
        ui.div(
            ui.output_ui("soap_pane"),
            ui.output_ui("patient_pane"),
            ui.output_ui("decision_pane"),
            class_="content-grid",
        ),
        class_="analysis-grid",
    ),
)


def server(input, output, session):

    def _render_markdown(text: str):
        """Render markdown text to html Tag. Uses `markdown` library if present,
        otherwise falls back to a simple safe conversion.
        Returns an htmltools HTML-wrapped Tag usable inside Shiny UI.
        """
        if not text:
            return ui.tags.div()
        if _markdown is not None:
            html = _markdown.markdown(str(text), extensions=["extra", "sane_lists"])
            return ui.tags.div(HTML(html), class_="md-body")

        # Fallback: escape, convert bold and bullets, make paragraphs
        s = _html.escape(str(text))
        s = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", s)
        lines = [l.rstrip() for l in s.splitlines()]
        # simple list detection
        if any(re.match(r'^(?:\-|\*|\u2610|\u2022)\s+', l) for l in lines):
            items = []
            for l in lines:
                m = re.match(r'^(?:\-|\*|\u2610|\u2022)\s+(.*)', l)
                if m:
                    items.append(f"<li>{m.group(1)}</li>")
            return ui.tags.div(HTML("<ul>" + "".join(items) + "</ul>"), class_="md-body")
        paras = [p for p in lines if p.strip()]
        html = "".join(f"<p>{p}</p>" for p in paras)
        return ui.tags.div(HTML(html), class_="md-body")
    @reactive.Calc
    def selected_analysis_path() -> Path | None:
        choice = input.analysis_choice()
        if not choice:
            return None
        path = OUTPUTS_DIR / choice
        return path if path.exists() else None

    @reactive.Calc
    def analysis_record() -> dict | None:
        return _load_json(selected_analysis_path())

    @reactive.Calc
    def encounter_id() -> str | None:
        record = analysis_record()
        if not record:
            return None
        return record.get("encounter_id")

    @reactive.Calc
    def soap_path() -> Path | None:
        return _latest_file("soap_output", encounter_id())

    @reactive.Calc
    def soap_record() -> dict | None:
        return _load_json(soap_path())

    @reactive.Calc
    def patient_record() -> dict | None:
        return _load_json(_latest_file("patient_artefacts", encounter_id()))

    @reactive.Calc
    def decision_record() -> dict | None:
        return _load_json(_latest_file("decision_support", encounter_id()))

    @output
    @render.ui
    def analysis_pane():
        record = analysis_record()
        if not record:
            return ui.div(
                ui.h3("Transcript & Entities"),
                ui.p(
                    "Run the pipeline or place a medical_analysis_results_*.json file under data/outputs to explore it here.",
                ),
                class_="panel placeholder-panel",
            )

        transcript = record.get("full_transcript") or record.get("transcript") or "Transcript unavailable."
        if len(transcript) > 1800:
            transcript_display = transcript[:1800].rstrip() + "…"
        else:
            transcript_display = transcript

        entities = record.get("medical_entities", {}).get("entities", [])
        speakers = record.get("speaker_segments", [])
        # Render entities as cards with type and text
        entity_cards = []
        if entities:
            for entity in entities[:20]:
                etype = entity.get("Type") or entity.get("Category") or "Entity"
                text = entity.get("Text") or entity.get("TextValue") or entity.get("text") or "-"
                meta = []
                for k in ("Score", "ScoreHigh", "BeginOffset", "EndOffset"):
                    if k in entity:
                        meta.append(f"{k}: {entity.get(k)}")
                meta_text = " — ".join(meta) if meta else ""
                entity_cards.append(
                    ui.tags.div(
                        ui.tags.div(etype, class_="entity-type"),
                        ui.tags.div(text),
                        ui.tags.div(meta_text, class_="text-muted"),
                        class_="entity-item",
                    )
                )
        else:
            entity_cards = [ui.tags.div("No medical entities extracted", class_="entity-item")]

        # Render speaker highlights as small badges with snippet
        speaker_items = []
        for segment in speakers[:6]:
            sp = segment.get("speaker", "spk")
            start = segment.get("start_time")
            snippet = (segment.get("text", "") or "").strip()
            if snippet:
                snippet = snippet[:200] + ("…" if len(snippet) > 200 else "")
            speaker_items.append(
                ui.tags.div(
                    ui.tags.span(sp, class_="speaker-badge"),
                    ui.tags.span(f"{start}s" if start is not None else ""),
                    ui.tags.div(snippet),
                )
            )

        return ui.div(
            ui.h3("Transcript & Entities"),
            ui.div(
                ui.div(ui.span("Encounter"), ui.div(record.get("encounter_id", "Unknown"), class_="meta-item"), class_="meta-item"),
                ui.div(ui.span("Timestamp"), ui.div(_format_timestamp(record.get("timestamp")), class_="meta-item"), class_="meta-item"),
                ui.div(ui.span("Speakers"), ui.div(str(len(speakers)), class_="meta-item"), class_="meta-item"),
                ui.div(ui.span("Entities"), ui.div(str(len(entities)), class_="meta-item"), class_="meta-item"),
                class_="meta-grid",
            ),
            ui.div(ui.h4("Transcript"), ui.tags.pre(transcript_display, class_="mono-block"), class_="text-block"),
            ui.div(ui.h4("Medical Entities"), ui.div(*entity_cards), class_="panel" if False else None),
            ui.div(ui.h4("Speaker Highlights"), ui.div(*speaker_items), class_="panel"),
            class_="panel",
        )

    @output
    @render.ui
    def soap_pane():
        soap_entry = soap_record()
        if not soap_entry:
            return ui.div(
                ui.h3("SOAP Note"),
                ui.p("SOAP output will appear here after the pipeline runs."),
                class_="panel placeholder-panel",
            )
        note = soap_entry.get("soap_note") or soap_entry
        sections = []
        for section in ["subjective", "objective", "assessment", "plan"]:
            excerpt = note.get(section)
            if excerpt is None:
                body = ui.p("Not documented.")
            elif isinstance(excerpt, str):
                # Render markdown or plain text as HTML
                body = _render_markdown(excerpt)
            elif isinstance(excerpt, list):
                body = ui.tags.ul(*[ui.tags.li(str(x)) for x in excerpt])
            elif isinstance(excerpt, dict):
                # Render key-value pairs
                items = []
                for k, v in excerpt.items():
                    items.append(ui.tags.div(ui.tags.strong(f"{k}: "), ui.tags.span(str(v))))
                body = ui.tags.div(*items)
            else:
                body = ui.p(str(excerpt))

            sections.append(
                ui.div(ui.h4(section.title()), body, class_="soap-section")
            )

        return ui.div(ui.h3("SOAP Note"), ui.div(*sections, class_="soap-grid"), class_="panel")

    @output
    @render.ui
    def patient_pane():
        patient_entry = patient_record()
        if not patient_entry:
            return ui.div(
                ui.h3("Patient Artefacts"),
                ui.p("Patient-friendly handout, checklist, and summary will be generated here once available."),
                class_="panel placeholder-panel",
            )
        # support files where artefacts are nested under "patient_artefacts"
        data_section = patient_entry.get("patient_artefacts") if isinstance(patient_entry, dict) else None
        source = data_section or patient_entry

        narrative_items: list[tuple[str, str]] = []
        mappings = [
            ("patient_handout", "Patient Handout"),
            ("after_visit_summary", "After-Visit Summary"),
            ("followup_checklist", "Follow-Up Checklist"),
        ]
        for key, label in mappings:
            text = None
            if isinstance(source, dict):
                text = source.get(key) or source.get(label.replace(" ", "_").lower())
            # fallback to top-level keys if present
            if not text and isinstance(patient_entry, dict):
                text = patient_entry.get(key) or patient_entry.get(label.replace(" ", "_").lower())
            if text:
                narrative_items.append((label, text))
        if not narrative_items:
            narrative_items = [("Patient Artefacts", "Details pending from the pipeline.")]

        cards = []
        for label, body in narrative_items:
            if label == "Follow-Up Checklist" or "checklist" in label.lower():
                # render checklist items line-by-line, remove markdown bullets and bold markers
                raw_lines = [l.strip() for l in str(body).splitlines() if l.strip()]
                lines = []
                for l in raw_lines:
                    # remove leading bullet markers or markdown bold
                    if l.startswith("- ") or l.startswith("* "):
                        lines.append(l[2:].strip())
                    elif l.startswith("☐") or l.startswith("\u2610"):
                        lines.append(l[1:].strip())
                    elif l.startswith("**") and l.endswith("**"):
                        lines.append(l[2:-2].strip())
                    else:
                        # strip leading enumeration like '1.' or '-'
                        parts = l.lstrip('- ').split('.', 1)
                        if len(parts) > 1 and parts[0].isdigit():
                            lines.append(parts[1].strip())
                        else:
                            lines.append(l)
                checklist = ui.tags.ul(*[ui.tags.li(line) for line in lines], class_="checklist")
                cards.append(ui.div(ui.h4(label), checklist, class_="soap-section"))
            else:
                # Render markdown/HTML for patient-facing text
                body_div = _render_markdown(body)
                cards.append(ui.div(ui.h4(label), body_div, class_="soap-section"))

        return ui.div(ui.h3("Patient Artefacts"), ui.div(*cards, class_="soap-grid"), class_="panel")

    @output
    @render.ui
    def decision_pane():
        decision_entry = decision_record()
        if not decision_entry:
            return ui.div(
                ui.h3("Decision Support"),
                ui.p("Decision prompts appear here once generated."),
                class_="panel placeholder-panel",
            )

        prompts = (
            decision_entry.get("decision_support", {}).get("prompts")
            or decision_entry.get("prompts")
            or []
        )
        if not prompts:
            prompts = ["No prompts produced yet."]

        cards = []
        for p in prompts:
            cards.append(ui.tags.div(ui.tags.p(p), class_="decision-card"))

        return ui.div(ui.h3("Decision Support"), ui.div(*cards), class_="panel")


app = App(app_ui, server)


def run_visualizer(*, host: str = "127.0.0.1", port: int = 8001, debug: bool = True) -> None:
    from shiny import run

    run(app, host=host, port=port, debug=debug)
