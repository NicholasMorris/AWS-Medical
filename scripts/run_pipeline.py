#!/usr/bin/env python3
"""Run the full pipeline (non-mocked).

This script ensures the repository root is on `sys.path` so `src` imports
work regardless of the current working directory, then runs the SOAP pipeline
with optional decision support and patient artefacts steps.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure repository root is on sys.path so `src` package imports resolve.
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.clinical_notes.soap import run as soap_run


def main(decision_support: bool = True, patient_artefacts: bool = True) -> str:
    """Run the full pipeline and return the output path from `soap_run.main()`.

    Note: This will call real AWS services (Bedrock, Comprehend Medical, Transcribe)
    using the environment's AWS credentials and region configuration.
    """
    return soap_run.main(decision_support=decision_support, patient_artefacts=patient_artefacts)


if __name__ == "__main__":
    out = main(decision_support=True, patient_artefacts=True)
    print("Pipeline run completed. SOAP output path:", out)
