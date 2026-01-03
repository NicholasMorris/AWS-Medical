# AWS-Medical: Audio-to-SOAP Clinical Notes

A Python application that converts medical audio recordings into structured clinical SOAP notes using AWS services and Claude on Bedrock.

**Pipeline**: Audio (S3) → Transcription (AWS Transcribe) → Entity Extraction (AWS Comprehend Medical) → SOAP Notes (Claude Bedrock)

## Features

- **Live Transcription**: Real-time medical audio streaming via AWS Transcribe Streaming
- **Batch Transcription**: Process .m4a files with speaker diarization and medical entity extraction
- **SOAP Note Generation**: Structured clinical documentation from transcription data using Claude 3.5 Sonnet
- **Dynamic ID Correlation**: Encounter and correlation IDs for traceability across the pipeline
- **Australian GP Context**: Clinical prompts follow Australian general practice conventions

## Prerequisites

- Python 3.13+
- AWS Account with credentials configured
- AWS Services enabled:
  - **Transcribe** (medical transcription jobs)
  - **Comprehend Medical** (entity extraction)
  - **Bedrock** (Claude 3.5 Sonnet access)
  - **S3** (audio file storage)

## Installation

### 1. Clone and Setup Virtual Environment

```bash
git clone <repo-url> /workspaces/AWS-Medical
cd /workspaces/AWS-Medical

# Create and activate virtual environment
python3.13 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
# Using uv (recommended)
uv pip install -e .

# Or using pip directly
pip install -e .
```

### 3. Verify Setup

```bash
# Test imports
.venv/bin/python3 -c "from src.common.io import load_json, generate_encounter_id; print('✓ Setup OK')"

# Test AWS connectivity
.venv/bin/python3 -c "from src.common.aws import get_bedrock_runtime; print(get_bedrock_runtime())"
```

## Quick Start

### Generate SOAP Note from Existing Analysis

```bash
source .venv/bin/activate

# Automatically finds latest medical analysis and generates SOAP note
python -m src.clinical_notes.soap.run
```

This will:
1. Find the most recent `medical_analysis_results_*.json` in `data/outputs/`
2. Extract encounter and correlation IDs
3. Generate SOAP note with Claude Bedrock
4. Save as `soap_output_{encounter_id}_{timestamp}.json` with full correlation metadata

### Process Audio File (Batch Transcription)

```bash
# See src/transcription/batch.py for configuration
# Update LOCAL_M4A_FILE, BUCKET_NAME, and REGION before running

.venv/bin/python3 src/transcription/batch.py
```

This will:
1. Upload .m4a file to S3
2. Start AWS Transcribe medical transcription job
3. Extract medical entities with Comprehend Medical
4. Analyze speaker segments
5. Save results as `medical_analysis_results_{encounter_id}_{timestamp}.json`

### Live Transcription

```bash
.venv/bin/python3 src/transcription/live.py
```

Press Ctrl+C to stop and finalize transcription.

## Architecture

### Directory Structure

```
src/
├── app/                    # Entry points
│   └── main.py
├── common/                 # Shared utilities
│   ├── aws.py             # Cached AWS client factories
│   └── io.py              # JSON I/O, ID generation, file helpers
├── clinical_notes/
│   └── soap/              # SOAP note generation
│       ├── generator.py   # Claude Bedrock integration
│       └── run.py         # SOAP generation pipeline
└── transcription/         # Audio processing
    ├── batch.py          # Batch transcription + Comprehend Medical
    └── live.py           # Live streaming transcription
tests/                     # Unit tests (pytest)
data/
├── inputs/               # Input audio files
└── outputs/              # Generated JSON files
```

### Data Flow

```
Audio File (S3)
    ↓
medical_transcription_with_comprehend()
    ├─ AWS Transcribe (speaker diarization)
    ├─ AWS Comprehend Medical (entity extraction)
    └─ Speaker segment analysis
    ↓
save_medical_analysis_results()
    ↓
medical_analysis_results_{encounter_id}_{timestamp}.json
    ├─ encounter_id (UUID)
    ├─ correlation_id (UUID)
    ├─ timestamp (Unix)
    ├─ full_transcript
    ├─ speaker_segments
    ├─ medical_entities
    └─ phi_entities
    ↓
generate_soap_note()
    ├─ Claude Bedrock (temperature: 0.2, conservative)
    └─ Australian GP prompts
    ↓
save_soap_note()
    ↓
soap_output_{encounter_id}_{timestamp}.json
    ├─ encounter_id (matches medical analysis)
    ├─ correlation_id
    ├─ timestamp
    └─ soap_note
        ├─ subjective
        ├─ objective
        ├─ assessment
        └─ plan
```

## Key Modules

### `src/common/io.py`

Centralized I/O utilities with type hints:

```python
# JSON operations
load_json(file_path: str) -> Any
save_json(data: Any, file_path: str, indent: int = 2) -> None

# ID generation
generate_encounter_id() -> str              # UUID v4
generate_correlation_id() -> str            # UUID v4
get_timestamp() -> int                      # Unix timestamp

# Pipeline saving with automatic ID management
save_medical_analysis_results(
    results: Dict,
    output_dir: str = "data/outputs",
    encounter_id: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> str

save_soap_note(
    soap_data: Dict,
    output_dir: str = "data/outputs",
    encounter_id: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> str
```

### `src/common/aws.py`

Cached AWS client factories:

```python
get_bedrock_runtime(region_name: Optional[str] = None) -> BotoCoreClient
get_transcribe_client(region_name: Optional[str] = None) -> BotoCoreClient
get_comprehend_medical_client(region_name: Optional[str] = None) -> BotoCoreClient
get_s3_client(region_name: Optional[str] = None) -> BotoCoreClient
```

All use `@lru_cache` and default to `ap-southeast-2` region.

### `src/clinical_notes/soap/generator.py`

```python
generate_soap_note(
    encounter_json: Dict,
    encounter_id: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> Dict
```

Returns SOAP note with subjective, objective, assessment, plan sections. Never halluculates; uses only provided encounter data.

## Testing

### Run All Tests

```bash
source .venv/bin/activate

# Run pytest with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/test_io.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Test Structure

```
tests/
├── test_io.py              # Test JSON I/O and ID generation
├── test_aws.py             # Test AWS client caching
└── test_generator.py       # Test SOAP note generation (mocked)
```

### Example Test

```python
# tests/test_io.py
import pytest
from src.common.io import generate_encounter_id, save_json, load_json

def test_generate_encounter_id():
    """Encounter IDs should be valid UUIDs."""
    id1 = generate_encounter_id()
    id2 = generate_encounter_id()
    
    assert len(id1) == 36  # UUID format
    assert id1 != id2      # Each ID is unique

def test_save_and_load_json(tmp_path):
    """Save and load JSON roundtrip should preserve data."""
    test_data = {"key": "value", "nested": {"count": 42}}
    file_path = tmp_path / "test.json"
    
    save_json(test_data, str(file_path))
    loaded = load_json(str(file_path))
    
    assert loaded == test_data
```

## Configuration

### AWS Region

Default region is `ap-southeast-2` (Sydney). Override in function calls:

```python
from src.common.aws import get_bedrock_runtime

# Use different region
bedrock = get_bedrock_runtime(region_name="us-east-1")
```

### Transcription Settings

Medical transcription uses:
- **Specialty**: `PRIMARYCARE` (only option currently)
- **Type**: `CONVERSATION` or `DICTATION`
- **Speaker Diarization**: Enabled, `MaxSpeakerLabels=2`
- **Language**: `en-AU` (Australian English)

### SOAP Generation Settings

Claude model: `anthropic.claude-3-sonnet-20240229-v1:0`
- Temperature: `0.2` (conservative, low hallucination)
- Max tokens: `800`
- System prompt enforces Australian GP conventions

## Common Issues

### AWS Credentials Not Found

```bash
# Check AWS configuration
aws sts get-caller-identity

# Set credentials
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=ap-southeast-2
```

### Bedrock Model Access Denied

Ensure your AWS account has:
1. Bedrock service enabled in target region
2. Access to Claude 3.5 Sonnet model granted
3. Completed Anthropic use case form if new to Bedrock

### Transcription Job Timeout

Medical transcription jobs can take 10-20 minutes depending on audio length. Check S3 bucket for job output.

### Import Errors

Always use `.venv/bin/python3`:

```bash
# ✗ Wrong
python -m src.clinical_notes.soap.run

# ✓ Correct
.venv/bin/python3 -m src.clinical_notes.soap.run
```

## Development

### Code Quality

- **Style**: Follow PEP 8
- **Formatting**: Black formatting applied
- **Type Hints**: All functions include type annotations
- **Docstrings**: All functions have docstrings

### Adding New AWS Services

1. Add cached client factory to `src/common/aws.py`:

```python
@lru_cache
def get_my_service_client(region_name: Optional[str] = None):
    """Returns a cached My Service client."""
    return boto3.client(
        service_name="my-service",
        region_name=region_name or DEFAULT_REGION,
    )
```

2. Import and use in relevant module
3. Add tests in `tests/`

### Adding New Pipeline Steps

1. Create module in appropriate `src/` subdirectory
2. Use common utilities from `src/common/`
3. Follow data flow: structured JSON in, structured JSON out
4. Add type hints and docstrings
5. Add tests in `tests/`
6. Update pipeline documentation

## License

[Your License Here]

## Support

For issues or questions, please refer to the AWS and Claude documentation:
- [AWS Transcribe Medical](https://docs.aws.amazon.com/transcribe/)
- [AWS Comprehend Medical](https://docs.aws.amazon.com/comprehend/latest/dg/what-is-medical.html)
- [AWS Bedrock](https://docs.aws.amazon.com/bedrock/)
- [Claude on Bedrock](https://docs.anthropic.com/bedrock/reference/run-inference)
