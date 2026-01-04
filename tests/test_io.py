"""Tests for src/common/io.py - JSON I/O and ID generation utilities."""

import json
import pytest
from pathlib import Path
import uuid

from src.common.io import (
    load_json,
    save_json,
    generate_encounter_id,
    generate_correlation_id,
    get_timestamp,
    save_medical_analysis_results,
    save_soap_note,
)


class TestIDGeneration:
    """Tests for ID generation functions."""

    def test_generate_encounter_id_returns_valid_uuid(self):
        """Encounter ID should be a valid UUID v4."""
        enc_id = generate_encounter_id()
        
        # Should be a valid UUID
        try:
            uuid.UUID(enc_id)
        except ValueError:
            pytest.fail(f"Generated encounter_id is not a valid UUID: {enc_id}")
        
        assert len(enc_id) == 36  # UUID string format with hyphens

    def test_generate_correlation_id_returns_valid_uuid(self):
        """Correlation ID should be a valid UUID v4."""
        corr_id = generate_correlation_id()
        
        # Should be a valid UUID
        try:
            uuid.UUID(corr_id)
        except ValueError:
            pytest.fail(f"Generated correlation_id is not a valid UUID: {corr_id}")
        
        assert len(corr_id) == 36

    def test_generate_ids_are_unique(self):
        """Generated IDs should be unique."""
        ids = [generate_encounter_id() for _ in range(10)]
        assert len(ids) == len(set(ids))  # All unique

    def test_get_timestamp_returns_positive_integer(self):
        """Timestamp should be a positive Unix timestamp."""
        ts = get_timestamp()
        assert isinstance(ts, int)
        assert ts > 0
        # Sanity check: should be after 2020
        assert ts > 1577836800


class TestJSONOperations:
    """Tests for JSON load/save operations."""

    def test_save_and_load_json_basic(self, tmp_path):
        """Save and load basic JSON data."""
        test_data = {
            "string": "value",
            "number": 42,
            "array": [1, 2, 3],
            "nested": {"key": "value"}
        }
        
        file_path = tmp_path / "test.json"
        save_json(test_data, str(file_path))
        
        loaded_data = load_json(str(file_path))
        assert loaded_data == test_data

    def test_save_json_creates_parent_directories(self, tmp_path):
        """save_json should create parent directories if they don't exist."""
        nested_path = tmp_path / "subdir1" / "subdir2" / "test.json"
        test_data = {"test": "data"}
        
        save_json(test_data, str(nested_path))
        
        assert nested_path.exists()
        assert load_json(str(nested_path)) == test_data

    def test_save_json_with_custom_indent(self, tmp_path):
        """save_json should respect custom indent level."""
        test_data = {"key": "value", "nested": {"inner": "data"}}
        file_path = tmp_path / "test.json"
        
        save_json(test_data, str(file_path), indent=4)
        
        content = file_path.read_text()
        # Check that 4-space indentation is used
        assert "    " in content

    def test_load_json_nonexistent_file_raises_error(self, tmp_path):
        """load_json should raise FileNotFoundError for nonexistent files."""
        with pytest.raises(FileNotFoundError):
            load_json(str(tmp_path / "nonexistent.json"))

    def test_json_roundtrip_with_complex_structure(self, tmp_path):
        """Complex nested JSON should survive roundtrip."""
        test_data = {
            "encounter_id": generate_encounter_id(),
            "correlation_id": generate_correlation_id(),
            "timestamp": get_timestamp(),
            "medical_entities": {
                "entities": [
                    {"type": "MEDICATION", "text": "aspirin"},
                    {"type": "SYMPTOM", "text": "headache"}
                ]
            },
            "speaker_segments": [
                {"speaker": "spk_0", "text": "Hello"},
                {"speaker": "spk_1", "text": "Hi there"}
            ]
        }
        
        file_path = tmp_path / "complex.json"
        save_json(test_data, str(file_path))
        loaded = load_json(str(file_path))
        
        assert loaded == test_data


class TestMedicalAnalysisResultsSaving:
    """Tests for save_medical_analysis_results function."""

    def test_save_medical_analysis_results_creates_file_with_encounter_id(self, tmp_path):
        """save_medical_analysis_results should create file with encounter_id in name."""
        results = {
            "transcription_job_name": "test-job",
            "full_transcript": "Test transcript",
            "speaker_segments": []
        }
        
        output_dir = str(tmp_path)
        output_file = save_medical_analysis_results(results, output_dir=output_dir)
        
        assert Path(output_file).exists()
        assert "medical_analysis_results_" in output_file
        # Should contain encounter_id in filename
        assert len(output_file.split("_")) >= 4  # medical_analysis_results_{uuid}_{timestamp}.json

    def test_save_medical_analysis_results_adds_ids_to_data(self, tmp_path):
        """save_medical_analysis_results should add encounter_id, correlation_id, and timestamp."""
        results = {"transcription_job_name": "test-job"}
        
        output_file = save_medical_analysis_results(results, output_dir=str(tmp_path))
        saved_data = load_json(output_file)
        
        assert "encounter_id" in saved_data
        assert "correlation_id" in saved_data
        assert "timestamp" in saved_data
        assert "transcription_job_name" in saved_data

    def test_save_medical_analysis_results_with_provided_ids(self, tmp_path):
        """save_medical_analysis_results should use provided IDs."""
        enc_id = generate_encounter_id()
        corr_id = generate_correlation_id()
        results = {"transcription_job_name": "test-job"}
        
        output_file = save_medical_analysis_results(
            results,
            output_dir=str(tmp_path),
            encounter_id=enc_id,
            correlation_id=corr_id
        )
        
        saved_data = load_json(output_file)
        assert saved_data["encounter_id"] == enc_id
        assert saved_data["correlation_id"] == corr_id

    def test_save_medical_analysis_results_filename_uses_encounter_id(self, tmp_path):
        """Filename should include the encounter_id for easy identification."""
        enc_id = "test-encounter-12345"
        results = {"transcription_job_name": "test-job"}
        
        output_file = save_medical_analysis_results(
            results,
            output_dir=str(tmp_path),
            encounter_id=enc_id
        )
        
        filename = Path(output_file).name
        assert enc_id in filename
        assert filename.startswith("medical_analysis_results_")


class TestSOAPNoteSaving:
    """Tests for save_soap_note function."""

    def test_save_soap_note_creates_file_with_encounter_id(self, tmp_path):
        """save_soap_note should create file with encounter_id in name."""
        soap_data = {
            "subjective": "Patient reports headache",
            "objective": "Exam normal",
            "assessment": "Tension headache",
            "plan": "Rest and fluids"
        }
        
        output_dir = str(tmp_path)
        output_file = save_soap_note(soap_data, output_dir=output_dir)
        
        assert Path(output_file).exists()
        assert "soap_output_" in output_file

    def test_save_soap_note_wraps_data_with_metadata(self, tmp_path):
        """save_soap_note should wrap SOAP data in metadata structure."""
        soap_data = {
            "subjective": "Patient reports headache",
            "objective": "Exam normal",
            "assessment": "Tension headache",
            "plan": "Rest and fluids"
        }
        
        output_file = save_soap_note(soap_data, output_dir=str(tmp_path))
        saved_data = load_json(output_file)
        
        assert "encounter_id" in saved_data
        assert "correlation_id" in saved_data
        assert "timestamp" in saved_data
        assert "soap_note" in saved_data
        assert saved_data["soap_note"] == soap_data

    def test_save_soap_note_with_correlation_ids(self, tmp_path):
        """save_soap_note should use provided encounter and correlation IDs."""
        enc_id = generate_encounter_id()
        corr_id = generate_correlation_id()
        
        soap_data = {"subjective": "Test"}
        output_file = save_soap_note(
            soap_data,
            output_dir=str(tmp_path),
            encounter_id=enc_id,
            correlation_id=corr_id
        )
        
        saved_data = load_json(output_file)
        assert saved_data["encounter_id"] == enc_id
        assert saved_data["correlation_id"] == corr_id

    def test_soap_and_medical_analysis_correlation(self, tmp_path):
        """SOAP output and medical analysis should share encounter_id for correlation."""
        enc_id = generate_encounter_id()
        corr_id = generate_correlation_id()
        
        # Save medical analysis
        med_results = {"transcription_job_name": "test"}
        med_file = save_medical_analysis_results(
            med_results,
            output_dir=str(tmp_path),
            encounter_id=enc_id,
            correlation_id=corr_id
        )
        
        # Save SOAP with same IDs
        soap_data = {"subjective": "Test"}
        soap_file = save_soap_note(
            soap_data,
            output_dir=str(tmp_path),
            encounter_id=enc_id,
            correlation_id=corr_id
        )
        
        # Load both and verify correlation
        med_data = load_json(med_file)
        soap_data_loaded = load_json(soap_file)
        
        assert med_data["encounter_id"] == soap_data_loaded["encounter_id"]
        assert med_data["correlation_id"] == soap_data_loaded["correlation_id"]


class TestIntegration:
    """Integration tests for IO utilities."""

    def test_full_pipeline_ids_flow(self, tmp_path):
        """Test complete flow of ID generation through pipeline."""
        # Generate unique IDs for this encounter
        enc_id = generate_encounter_id()
        corr_id = generate_correlation_id()
        
        # Simulate transcription results
        transcription_results = {
            "transcription_job_name": "medical-transcription-123456",
            "full_transcript": "Doctor: Hello. Patient: Hi there.",
            "speaker_segments": [
                {"speaker": "spk_0", "text": "Doctor: Hello"},
                {"speaker": "spk_1", "text": "Patient: Hi there"}
            ],
            "medical_entities": {"entities": []}
        }
        
        # Save medical analysis with IDs
        med_file = save_medical_analysis_results(
            transcription_results,
            output_dir=str(tmp_path),
            encounter_id=enc_id,
            correlation_id=corr_id
        )
        
        # Load it back
        med_data = load_json(med_file)
        
        # Extract IDs for SOAP generation
        retrieved_enc_id = med_data["encounter_id"]
        retrieved_corr_id = med_data["correlation_id"]
        
        # Generate SOAP note
        soap_note = {
            "subjective": "Patient reports symptoms",
            "objective": "Examination performed",
            "assessment": "Working diagnosis",
            "plan": "Management plan"
        }
        
        # Save SOAP with extracted IDs
        soap_file = save_soap_note(
            soap_note,
            output_dir=str(tmp_path),
            encounter_id=retrieved_enc_id,
            correlation_id=retrieved_corr_id
        )
        
        # Verify full correlation
        soap_data = load_json(soap_file)
        
        assert med_data["encounter_id"] == soap_data["encounter_id"]
        assert med_data["correlation_id"] == soap_data["correlation_id"]
        assert soap_data["soap_note"]["subjective"] == soap_note["subjective"]
