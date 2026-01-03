#!/usr/bin/env python3
"""Local runner to simulate end-to-end pipeline using sample data and mocked Bedrock responses.

This avoids calling real AWS services and verifies the pipeline wiring from
`src/clinical_notes/soap/run.py` through generator, decision_support, and
patient_artefacts functions.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure repository root is on sys.path so `src` package imports resolve.
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import json
from unittest.mock import MagicMock
from src.clinical_notes.soap import run as soap_run
from src.clinical_notes.soap import generator as soap_generator
from src.clinical_notes import decision_support as ds_module
from src.clinical_notes import patient_artefacts as pa_module

# Create a canned SOAP JSON output
soap_content = {
    "subjective": "Patient reports mild headache.",
    "objective": "No red flags documented.",
    "assessment": "Tension-type headache",
    "plan": "Rest, analgesia, follow up in one week"
}

# Bedrock-style wrapper
response_body = json.dumps({
    "content": [{"type": "text", "text": json.dumps(soap_content)}]
}).encode("utf-8")
mock_soap_response = {"body": MagicMock(read=lambda: response_body)}

# Patient artefacts responses (plain text)
handout_text = "You have a mild headache. Rest and drink fluids. Come back if worse."
pa_response_body = json.dumps({"content": [{"text": handout_text}]}).encode("utf-8")
mock_pa_response = {"body": MagicMock(read=lambda: pa_response_body)}

# Patch bedrock clients used by modules
soap_generator.bedrock.invoke_model = MagicMock(return_value=mock_soap_response)
ds_module.bedrock.invoke_model = MagicMock(return_value=mock_pa_response)
pa_module.bedrock.invoke_model = MagicMock(return_value=mock_pa_response)

# Run pipeline (SOAP + decision support + patient artefacts)
if __name__ == "__main__":
    out = soap_run.main(decision_support=True, patient_artefacts=True)
    print("Pipeline run completed. SOAP output path:", out)
