# AI Coding Instructions for AWS-Medical

## Project Overview
AWS-Medical is a Python application that converts medical audio recordings into structured clinical SOAP notes using AWS services:

- **Transcription Pipeline**: Audio → transcribed text (via AWS Transcribe)
- **Clinical Analysis**: Transcripts → medical entity extraction (via AWS Comprehend Medical)
- **Documentation Generation**: Extracted data → SOAP notes (via Bedrock Nova)

The project is modularized under `src/`, with **common utilities** in `src/common/`. The agent should maintain clean, testable, and reusable code.

---

## Architecture & Data Flow

### Core Components
1. **`src/transcription/`** – Audio processing  
   - `live.py`: Real-time transcription via AWS Transcribe Streaming  
   - `batch.py`: Batch transcription of medical audio files (.m4a) with speaker diarization  

2. **`src/clinical_notes/soap/`** – Clinical documentation generation  
   - `generator.py`: Bedrock (Nova) integration to generate SOAP notes from encounter JSON  
   - System prompts enforce Australian GP conventions and prevent hallucination  

3. **`src/clinical_notes/decision_support.py`** – Non-diagnostic decision support
   - `generate_decision_support_prompts()`: Surfaces clinical context, risk factors, and decision points
   - Never diagnoses; uses `amazon.nova-2-lite-v1:0` (temperature: 0.3)
   - Output: JSON with "prompts" list (3-5 items starting with "Consider...", "No red flags...", "Document...")
   - Safety: System prompt enforces NO diagnosis, NO predictions, only context surfacing

4. **`src/clinical_notes/patient_artefacts.py`** – Patient-ready plain English documents
   - `generate_patient_handout()`: 150-200 word take-home advice (no medical jargon)
   - `generate_after_visit_summary()`: Friendly letter summarizing today's visit
   - `generate_followup_checklist()`: Checkbox-based patient action items
   - All use `amazon.nova-2-lite-v1:0` (temperature: 0.2, conservative)
   - Output: Plain text (not medical jargon); handout/summary ~150-200 words each; checklist has ☐ checkboxes
   - Safety: All enforce plain language, no medical terminology, patient-actionable items only

5. **`src/common/`** – Shared utilities  
   - `aws.py`: Cached AWS client factories (Bedrock, Transcribe, Comprehend Medical, S3)  
   - `io.py`: JSON file I/O helpers, ID generation, and save functions for all pipeline outputs

---

### Data Flow Example

Audio File (S3)
→ batch.start_medical_transcription_job()
→ medical_analysis_results_{timestamp}.json (entities, speakers)
→ generate_soap_note()
→ soap_output.json (structured clinical note)

---

## Key Guidelines

### 1. Utility Functions & Common Modules
- Any function, class, or code snippet reused in multiple scripts should be **moved to `src/common/`**.  
- The agent should **scan for duplicated or utility-like code** (file I/O, AWS calls, JSON manipulation, logging) and consolidate it into common scripts.  
- Avoid hardcoding references to existing common scripts; treat them as **examples of what belongs in `src/common/`**.  

### 2. AWS Clients
- Centralize all AWS clients in `src/common/aws.py`.  
- Use `@lru_cache` to cache clients.  
- Pass `region_name=` param to override default `ap-southeast-2`.  
- Typical clients: Bedrock runtime, Transcribe, Comprehend Medical, S3.  

### 3. IO & File Handling
- Centralize all JSON file read/write, logging, and reusable helpers in `src/common/io.py`.  
- Refactor duplicate file operations in scripts to use these utilities.  

### 4. Code Quality
- Follow **PEP8** style guidelines.  
- Apply **Black formatting**: enforces consistent style (indentation, line breaks, spacing).  
- Include **type hints and docstrings** for all functions and classes.  

### 5. Modularity & Single Responsibility
- Each script/module should do one thing and pass structured objects or JSON to other modules.  
- Avoid tight coupling between transcription, comprehension, and SOAP generation.

### 6. Testing
- Add unit tests for all new or refactored functions in a `tests/` folder.  
- Test common utilities independently from the pipeline.

### 7. Documentation
- Update `README.md` whenever functionality changes.  
- Include instructions on module usage, data formats, and AWS setup.

---

## Pipeline Tasks

1. **Transcription & Comprehension**  
   - Batch or live transcription → AWS Comprehend Medical → structured JSON.  
   - Identify AWS calls and file I/O → move to common modules.

2. **SOAP Note Generation**  
   - Input: structured transcription JSON  
   - Output: `soap_output.json`  
   - Ensure logic is modular, testable, and reusable.

3. **Live Transcription**  
   - Integrate live streaming with full pipeline  
   - Generate partial SOAP notes optionally in real time

4. **Dashboard / UI**  
   - Consume JSON outputs from SOAP generation  
   - Ensure consistent and parseable JSON structure

---

## Developer Workflow

### Environment Setup
**CRITICAL**: Always use the project's virtual environment (`.venv/`) when running Python commands.

```bash
# Activate the virtual environment
source .venv/bin/activate

# Install dependencies (if needed)
uv pip install -e .
```

Always run Python commands with `.venv/bin/python3` or after activating the venv:
```bash
.venv/bin/python3 -m src.clinical_notes.soap.run
# or
source .venv/bin/activate && python src/transcription/batch.py
```

### Key Files to Modify
- **New transcription features**: Add to `src/transcription/` (live.py for streaming, batch.py for batch jobs)
- **SOAP note improvements**: Modify `generate_soap_note()` prompt or add post-processing in `generator.py`
- **New AWS services**: Add cached client factory to `aws.py`, import in relevant module
- **Data format changes**: Update `src/common/io.py` and corresponding callers

### Testing / Running
```bash
# Activate venv first
source .venv/bin/activate

# Test SOAP generation with latest medical analysis
python -m src.clinical_notes.soap.run

# Test AWS setup
python -c "from src.common.aws import get_bedrock_runtime; print(get_bedrock_runtime())"

# Verify imports work
python -c "from src.common.io import load_json, save_json, generate_encounter_id; print('✓ Imports OK')"

# Run pytest suite
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=src --cov-report=html
```

---

## Important Conventions

### Output File Structure & ID Correlation
- **Medical Analysis Results**: `medical_analysis_results_{encounter_id}_{timestamp}.json`
  - Contains: `encounter_id`, `correlation_id`, `timestamp`, full transcription, medical entities, speaker analysis
  - Auto-generated by `save_medical_analysis_results()` in `src/common/io.py`
  
- **SOAP Output**: `soap_output_{encounter_id}_{timestamp}.json`
  - Wraps SOAP note with: `encounter_id`, `correlation_id`, `timestamp`, `soap_note` (contains subjective, objective, assessment, plan)
  - Auto-generated by `save_soap_note()` in `src/common/io.py`
  - `encounter_id` and `correlation_id` are extracted from medical analysis and passed to `generate_soap_note()`

- **ID Generation**: Use `generate_encounter_id()` and `generate_correlation_id()` from `src/common/io.py` to ensure traceability across the pipeline

### Medical Transcription Settings
- Specialty fixed at `"PRIMARYCARE"`  
- Audio format: `.m4a` (batch), PCM16 mono 16kHz (live)  
- Speaker diarization enabled (`ShowSpeakerLabels=True`)  
- MaxSpeakerLabels typically 2 (patient + clinician)  

### SOAP Note Generation
- **Never hallucinate**: only use data in encounter JSON  
- Preserve negatives explicitly  
- Use conservative language: `"likely"`, `"consistent with"`  
- Follow Australian GP documentation conventions  
- Output always valid JSON  

### Decision Support & Patient Artefacts Safety
- **Non-Diagnostic Rule**: Never suggest diagnosis, prognosis, or clinical predictions
- **Context Surfacing**: Focus on raising questions, surfacing red flags, documenting gaps
- **Plain Language**: Patient documents use NO medical jargon; test with non-clinician readers
- **Decision Support Format**: Prompts start with "Consider...", "No red flags...", "Document..." or similar
- **Patient Handout**: Use simple analogies (e.g., "take a break from screens" not "reduce computer exposure")
- **After-Visit Summary**: Written as friendly letter from GP; include what happened, what to do, when to return
- **Checklist**: Use ☐ checkboxes; include daily actions, weekly check-ins, warning signs
- **Models**: Decision support uses 0.3 temperature (slightly exploratory); patient artefacts use 0.2 (conservative, safe)

### AWS & Locale
- Default region: `ap-southeast-2`  
- Language code: `en-AU`  
- **Nova Model**: `amazon.nova-2-lite-v1:0` used for decision support and patient artefacts (cost-effective, fast)
- **Default SOAP model**: `nova` (Bedrock) is used for SOAP notes by default

---

## Common Integration Points

- New AWS services: add cached client in `aws.py`  
- Transcription & comprehension: move repeated logic to common modules  
- SOAP note fields: modify `user_prompt` in `generator.py` and update expected JSON structure  
- Error handling: centralized logging and exception handling  

---

## Debugging Tips

- AWS credentials: verify with CLI  
- Transcription timeouts: check S3 logs  
- SOAP JSON parsing: Bedrock wraps JSON in `content[0].text`  
- Audio format errors: batch only accepts `.m4a`, live requires 16kHz PCM16 mono  