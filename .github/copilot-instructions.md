# AI Coding Instructions for AWS-Medical

## Project Overview
AWS-Medical is a Python application that converts medical audio recordings into structured clinical SOAP notes using AWS services:

- **Transcription Pipeline**: Audio → transcribed text (via AWS Transcribe)
- **Clinical Analysis**: Transcripts → medical entity extraction (via AWS Comprehend Medical)
- **Documentation Generation**: Extracted data → SOAP notes (via Claude on Bedrock)

The project is modularized under `src/`, with **common utilities** in `src/common/`. The agent should maintain clean, testable, and reusable code.

---

## Architecture & Data Flow

### Core Components
1. **`src/transcription/`** – Audio processing  
   - `live.py`: Real-time transcription via AWS Transcribe Streaming  
   - `batch.py`: Batch transcription of medical audio files (.m4a) with speaker diarization  

2. **`src/clinical_notes/soap/`** – Clinical documentation generation  
   - `generator.py`: Claude Bedrock integration to generate SOAP notes from encounter JSON  
   - System prompts enforce Australian GP conventions and prevent hallucination  

3. **`src/common/`** – Shared utilities  
   - `aws.py`: Cached AWS client factories (Bedrock, Transcribe, Comprehend Medical, S3)  
   - `io.py`: JSON file I/O helpers and other general-purpose utilities  

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

1. Scan scripts for **reusable patterns** (AWS calls, IO, helper functions).  
2. Move identified utilities to `src/common/`.  
3. Refactor pipeline scripts to call common utilities instead of duplicating code.  
4. Maintain modularity and single responsibility per script.  
5. Add or maintain unit tests in `tests/`.  
6. Apply **Black formatting** and PEP8 compliance.  
7. Update `README.md`.  
8. Integrate full pipeline: transcription → comprehension → SOAP generation → live transcription → dashboard.

---

## Important Conventions

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

### AWS & Locale
- Default region: `ap-southeast-2`  
- Language code: `en-AU`  

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