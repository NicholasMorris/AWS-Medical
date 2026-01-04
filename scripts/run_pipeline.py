#!/usr/bin/env python3
"""Run the full pipeline (non-mocked).

This script ensures the repository root is on `sys.path` so `src` imports
work regardless of the current working directory, then runs the SOAP pipeline
with optional decision support and patient artefacts steps.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

# Ensure repository root is on sys.path so `src` package imports resolve.
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.common.aws import get_s3_client
from src.common.io import save_medical_analysis_results
from src.transcription.batch import (
    medical_transcription_with_comprehend,
    upload_m4a_to_s3,
)
from src.clinical_notes.soap import run as soap_run

DATA_RECORDINGS_DIR = repo_root / "data" / "recordings"
DEFAULT_AUDIO_PATH = DATA_RECORDINGS_DIR / "recording1.m4a"
DEFAULT_REGION = (
    os.getenv("AWS_REGION")
    or os.getenv("AWS_DEFAULT_REGION")
    or "ap-southeast-2"
)


def _ensure_audio_file(path: Path) -> Path:
    resolved = path.expanduser()
    if not resolved.exists():
        raise FileNotFoundError(f"Unable to find audio file at {resolved}")
    return resolved


def run_medical_analysis_from_audio(
    local_audio_path: Path,
    bucket_name: str,
    region_name: str,
    s3_key: Optional[str] = None,
    cleanup_s3_file: bool = False,
    job_name_prefix: str = "run-pipeline-medical",
    specialty: str = "PRIMARYCARE",
    transcription_type: str = "CONVERSATION",
    max_speakers: int = 2,
    show_alternatives: bool = False,
    max_alternatives: int = 2,
) -> str:
    """Upload an audio file to S3, run Transcribe + Comprehend Medical, and save the results."""

    audio_path = _ensure_audio_file(local_audio_path)
    s3_key = s3_key or f"recordings/{audio_path.name}"

    print(f"Uploading {audio_path} to s3://{bucket_name}/{s3_key}...")
    s3_uri = upload_m4a_to_s3(
        local_file_path=str(audio_path),
        bucket_name=bucket_name,
        s3_key=s3_key,
        region_name=region_name,
    )

    print("Running AWS Transcribe medical job and analyzing results...")
    results = medical_transcription_with_comprehend(
        audio_file_uri=s3_uri,
        output_bucket_name=bucket_name,
        job_name_prefix=job_name_prefix,
        specialty=specialty,
        transcription_type=transcription_type,
        max_speakers=max_speakers,
        show_alternatives=show_alternatives,
        max_alternatives=max_alternatives,
        region_name=region_name,
    )

    if cleanup_s3_file:
        print("Cleaning up uploaded audio from S3...")
        s3 = get_s3_client(region_name)
        s3.delete_object(Bucket=bucket_name, Key=s3_key)
        print(f"Removed s3://{bucket_name}/{s3_key}")

    analysis_path = save_medical_analysis_results(results)
    print(f"Medical analysis written to: {analysis_path}")

    return analysis_path


def main(
    decision_support: bool = True,
    patient_artefacts: bool = True,
    analysis_file: Optional[str] = None,
) -> str:
    """Run the SOAP + artefacts pipeline and return the saved SOAP path."""
    return soap_run.main(
        decision_support=decision_support,
        patient_artefacts=patient_artefacts,
        analysis_file=analysis_file,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate SOAP, decision support, and patient artefacts")
    parser.add_argument(
        "--analysis-file",
        help="Use an existing medical_analysis_results JSON file instead of running Transcribe",
        type=str,
    )
    parser.add_argument(
        "--s3-bucket",
        help="S3 bucket used for uploading audio and storing transcription results",
        type=str,
        default=os.getenv("AWS_MEDICAL_S3_BUCKET"),
    )
    parser.add_argument(
        "--s3-region",
        help="AWS region to use for Transcribe and S3 operations",
        type=str,
        default=DEFAULT_REGION,
    )
    parser.add_argument(
        "--s3-key",
        help="Explicit S3 key (path) for the uploaded audio file",
        type=str,
    )
    parser.add_argument(
        "--audio-path",
        help="Local audio file to upload (defaults to data/recordings/recording1.m4a)",
        type=str,
        default=str(DEFAULT_AUDIO_PATH),
    )
    parser.add_argument(
        "--cleanup-s3",
        action="store_true",
        help="Delete the uploaded audio file from S3 after transcription completes",
    )
    parser.set_defaults(decision_support=True, patient_artefacts=True)
    parser.add_argument(
        "--decision-support",
        dest="decision_support",
        action="store_true",
        help="Generate decision support prompts (default)",
    )
    parser.add_argument(
        "--no-decision-support",
        dest="decision_support",
        action="store_false",
        help="Skip decision support prompts",
    )
    parser.add_argument(
        "--patient-artefacts",
        dest="patient_artefacts",
        action="store_true",
        help="Generate patient artefacts (default)",
    )
    parser.add_argument(
        "--no-patient-artefacts",
        dest="patient_artefacts",
        action="store_false",
        help="Skip generating patient artefacts",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Ensure all outputs (SOAP, decision support, patient artefacts) are generated",
    )

    args = parser.parse_args()

    decision_support = args.decision_support
    patient_artefacts = args.patient_artefacts
    if args.all:
        decision_support = True
        patient_artefacts = True

    analysis_path = args.analysis_file
    if not analysis_path:
        if not args.s3_bucket:
            raise RuntimeError(
                "Either --analysis-file or AWS_MEDICAL_S3_BUCKET must be set to run the full pipeline."
            )
        audio_path = _ensure_audio_file(Path(args.audio_path))
        analysis_path = run_medical_analysis_from_audio(
            local_audio_path=audio_path,
            bucket_name=args.s3_bucket,
            region_name=args.s3_region,
            s3_key=args.s3_key,
            cleanup_s3_file=args.cleanup_s3,
        )

    soap_path = main(
        decision_support=decision_support,
        patient_artefacts=patient_artefacts,
        analysis_file=analysis_path,
    )
    print("Pipeline run completed. SOAP output path:", soap_path)
