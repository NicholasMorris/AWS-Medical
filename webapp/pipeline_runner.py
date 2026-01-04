"""Lightweight pipeline runner used by the web UI.

This wrapper attempts to run the full pipeline for a local audio file. It
follows a best-effort approach:

- If an S3 bucket is configured via `AWS_MEDICAL_S3_BUCKET` environment
  variable or `AWS_MEDICAL_CONFIG`, it will attempt to upload and run the
  transcription + Comprehend Medical steps using `src.transcription.batch`.
- Otherwise it will skip transcription and run the SOAP generation step
  against the latest `medical_analysis_results_*.json` present in
  `data/outputs/` using the existing `scripts/run_pipeline.py` entrypoint.

The function exposes a single async-friendly coroutine `run_pipeline_for_file`
that returns a dict of results (transcript, soap_note JSON, patient artefacts,
decision support) for display in the UI.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Dict, Any, Optional


def _has_s3_config() -> bool:
    # Prefer explicit env var; fallback to config file lookup is handled by
    # existing code paths if necessary. Keep the check simple.
    return bool(os.environ.get("AWS_MEDICAL_S3_BUCKET") or os.environ.get("AWS_ACCESS_KEY_ID"))


def _run_blocking(local_path: str) -> Dict[str, Any]:
    """Blocking helper to run the pipeline using existing library code.

    Returns a dict of extracted outputs for the UI.
    """
    # If AWS is configured, try to call the batch processor
    results: Dict[str, Any] = {}
    try:
        if _has_s3_config():
            # Lazy import to avoid requiring AWS libs when UI is used only for viewing
            from src.transcription.batch import process_local_m4a_file
            bucket = os.environ.get("AWS_MEDICAL_S3_BUCKET")
            if not bucket:
                raise RuntimeError("AWS_MEDICAL_S3_BUCKET not set for transcription upload")

            # Use the bucket as both upload and output bucket
            batch_results = process_local_m4a_file(local_path, bucket_name=bucket, output_bucket_name=bucket)

            # Save medical analysis to disk is handled inside batch
            results["transcript"] = batch_results.get("full_transcript")
        else:
            # No AWS credentials; inform user that we will use existing analysis
            results["transcript"] = None

        # Run SOAP generation (uses latest medical_analysis_results_*.json)
        # Use the project's run_pipeline entrypoint
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        import scripts.run_pipeline as rp

        soap_path = rp.main(decision_support=True, patient_artefacts=True)
        # Load outputs if possible
        from src.common.io import load_json

        try:
            soap_json = load_json(soap_path)
            results["soap_note"] = soap_json.get("soap_note") or soap_json
            results["soap_path"] = soap_path
        except Exception:
            results["soap_note"] = None

        # Look for latest patient artefacts and decision support files
        outputs_dir = Path("data/outputs")
        if outputs_dir.exists():
            # naive pick: find any patient_artefacts_ or decision_support_ file
            pa_files = sorted(outputs_dir.glob("patient_artefacts_*.json"), reverse=True)
            ds_files = sorted(outputs_dir.glob("decision_support_*.json"), reverse=True)
            if pa_files:
                try:
                    results["patient_artefacts"] = load_json(str(pa_files[0]))
                except Exception:
                    results["patient_artefacts"] = None
            if ds_files:
                try:
                    results["decision_support"] = load_json(str(ds_files[0]))
                except Exception:
                    results["decision_support"] = None

    except Exception as e:
        if "errors" not in results:
            results["errors"] = []
        results["errors"].append(str(e))

    return results


def run_transcription(local_path: str) -> Optional[str]:
    """Run only the transcription step (best-effort).

    Returns the full transcript string or None if not available.
    """
    try:
        if _has_s3_config():
            from src.transcription.batch import process_local_m4a_file

            bucket = os.environ.get("AWS_MEDICAL_S3_BUCKET")
            if not bucket:
                raise RuntimeError("AWS_MEDICAL_S3_BUCKET not set for transcription upload")

            batch_results = process_local_m4a_file(local_path, bucket_name=bucket, output_bucket_name=bucket)
            return batch_results.get("full_transcript")
        return None
    except Exception:
        return None


def generate_soap_and_outputs(decision_support: bool = True, patient_artefacts: bool = True) -> Dict[str, Any]:
    """Run the SOAP generation (and optional artefacts/decision support) using existing entrypoint.

    Returns a dict with keys: soap_note, soap_path, patient_artefacts, decision_support (where available).
    """
    results: Dict[str, Any] = {}
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import scripts.run_pipeline as rp

    soap_path = rp.main(decision_support=decision_support, patient_artefacts=patient_artefacts)
    from src.common.io import load_json

    try:
        soap_json = load_json(soap_path)
        results["soap_note"] = soap_json.get("soap_note") or soap_json
        results["soap_path"] = soap_path
    except Exception:
        results["soap_note"] = None

    outputs_dir = Path("data/outputs")
    if outputs_dir.exists():
        pa_files = sorted(outputs_dir.glob("patient_artefacts_*.json"), reverse=True)
        ds_files = sorted(outputs_dir.glob("decision_support_*.json"), reverse=True)
        if pa_files:
            try:
                results["patient_artefacts"] = load_json(str(pa_files[0]))
            except Exception:
                results["patient_artefacts"] = None
        if ds_files:
            try:
                results["decision_support"] = load_json(str(ds_files[0]))
            except Exception:
                results["decision_support"] = None

    return results


async def run_pipeline_for_file(local_path: str) -> Dict[str, Any]:
    """Async-friendly wrapper around the blocking pipeline runner.

    This uses a thread via `asyncio.to_thread` so it can be awaited from the
    web UI without blocking the event loop.
    """
    return await asyncio.to_thread(_run_blocking, local_path)
