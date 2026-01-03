# AI Coding Instructions for AWS-Medical

## Project Overview
AWS-Medical is a Python application that converts medical audio recordings into structured clinical SOAP notes using AWS services:
- **Transcription Pipeline**: Audio → transcribed text (via AWS Transcribe)
- **Clinical Analysis**: Transcripts → medical entity extraction (via AWS Comprehend Medical)
- **Documentation Generation**: Extracted data → SOAP notes (via Claude on Bedrock)

## Architecture & Data Flow

### Core Components
1. **`src/transcription/`** - Audio processing (live and batch)
   - `live.py`: Real-time transcription via AWS Transcribe Streaming with sounddevice microphone input
   - `batch.py`: Batch transcription of medical audio (.m4a files) with speaker diarization

2. **`src/clinical_notes/soap/`** - Clinical documentation generation
   - `generator.py`: Claude Bedrock integration to generate SOAP notes from encounter JSON
   - Uses system prompt enforcing Australian GP conventions, no hallucination

3. **`src/common/`** - Shared utilities
   - `aws.py`: Cached AWS client factories (Bedrock, Transcribe, Comprehend Medical, S3)
   - `io.py`: JSON file I/O helpers

### Data Flow Example
```
Audio File (S3) 
  → batch.start_medical_transcription_job() 
  → medical_analysis_results_{timestamp}.json (entities, speakers)
  → generate_soap_note() 
  → soap_output.json (structured clinical note)
```

## Key Technical Patterns

### AWS Clients
All AWS clients are cached with `@lru_cache` in `src/common/aws.py`. Default region is `ap-southeast-2`.
- Use `get_bedrock_runtime()`, `get_transcribe_client()`, `get_comprehend_medical_client()`, `get_s3_client()`
- Pass `region_name=` param to override default region

### Live Transcription (live.py)
- Uses `sounddevice.RawInputStream` callback to capture PCM16 audio chunks
- Asyncio-based sender/receiver: audio chunks → queue → async `audio_sender()` → Transcribe stream
- Signal handlers catch Ctrl+C to gracefully end stream and shutdown
- Configuration at top of file: `SAMPLE_RATE=16000`, `CHUNK_MS=100`, `LANGUAGE_CODE="en-AU"`
- Handler class `TranscriptCollector` collects partial (interim) and final results separately

### Batch Transcription (batch.py)
- Core function: `medical_transcription_with_comprehend()` orchestrates entire pipeline
- Starts medical transcription job with speaker diarization (`MaxSpeakerLabels`)
- Polls job status every 10 seconds until COMPLETED/FAILED
- Downloads transcript JSON from S3, parses speaker segments and items
- Runs Comprehend Medical analysis on transcript text
- Returns combined dict with transcription + medical entities

### SOAP Note Generation (generator.py)
- Model: Claude 3.5 Sonnet (`anthropic.claude-3-sonnet-20240229-v1:0`)
- Temperature: 0.2 (conservative, low hallucination)
- Takes encounter JSON (from medical transcription) → outputs SOAP JSON with keys: `subjective`, `objective`, `assessment`, `plan`
- System prompt explicitly forbids inventing symptoms; enforces Australian GP conventions

## Developer Workflow

### Setup
```bash
uv pip install -e .
```
Dependencies in `pyproject.toml`: sounddevice, boto3, amazon-transcribe, aiofile

### Key Files to Modify
- **New transcription features**: Add to `src/transcription/` (live.py for streaming, batch.py for batch jobs)
- **SOAP note improvements**: Modify `generate_soap_note()` prompt or add post-processing in `generator.py`
- **New AWS services**: Add cached client factory to `aws.py`, import in relevant module
- **Data format changes**: Update `src/common/io.py` and corresponding callers

### Testing / Running
- `python src/transcription/live.py` - Start live transcription with microphone
- `python src/clinical_notes/soap/run.py` - Generate SOAP note from existing JSON in `data/outputs/`
- `python -c "from src.common.aws import get_bedrock_runtime; print(get_bedrock_runtime())"` - Verify AWS setup

## Important Conventions

### Medical Transcription Settings
- Medical specialty fixed at `"PRIMARYCARE"` (only current option)
- Audio format: `.m4a` files only (batch transcription)
- Speaker diarization: `MaxSpeakerLabels` typically 2 (patient + clinician)
- Always enable `ShowSpeakerLabels: True` in settings for conversation analysis

### SOAP Note Generation Constraints
- **Never hallucinate**: Only use data explicitly in encounter JSON
- **Preserve negatives**: Document "no vomiting" if stated
- **Conservative language**: Use "likely", "consistent with" instead of certainties
- **Australian context**: Follow GP documentation standards (see system prompt in generator.py)
- Output always valid JSON

### Region & Locale
- Default region: `ap-southeast-2` (Sydney, Australia)
- Language code: `en-AU` (Australian English) for transcription
- Adjust in respective files if needed (e.g., `live.py` line 11, `batch.py` parameter)

## Common Integration Points

### Adding Medical Entity Enrichment
1. Call `get_comprehend_medical_client()` in batch.py
2. Pass transcribed text to `detect_entities_v2()` (example already in batch.py)
3. Merge entity results into encounter JSON before passing to `generate_soap_note()`

### Extending SOAP Note Fields
1. Modify the `user_prompt` in `generator.py` to request additional sections
2. Update return JSON keys in expected structure
3. Test with `python src/clinical_notes/soap/run.py` against sample input

### Error Handling Patterns
- Transcription job failures: Check `FailureReason` in status response (batch.py line ~85)
- S3 URI parsing: Handle both HTTPS URL and `s3://` URI formats (batch.py line ~115)
- Bedrock model errors: Check response structure and `invoke_model()` exceptions

## Debugging Tips

1. **AWS credential issues**: Ensure AWS CLI is configured with correct credentials (container has AWS CLI pre-installed)
2. **Transcription timeouts**: Batch jobs can take 10-20 minutes; check S3 logs for job status
3. **SOAP JSON parsing**: Bedrock response wraps actual JSON in `content[0].text`; see generator.py line ~70
4. **Audio format errors**: Batch only accepts `.m4a`; live transcription requires 16kHz PCM16 mono
