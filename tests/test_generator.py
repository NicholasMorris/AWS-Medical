"""Tests for src/clinical_notes/soap/generator.py - SOAP note generation."""

import json
import pytest
from unittest.mock import patch, MagicMock

from src.clinical_notes.soap.generator import generate_soap_note


def create_mock_bedrock_response(soap_json_content):
    """Create a mock Bedrock response with SOAP JSON."""
    response_body = json.dumps({
        "content": [
            {
                "type": "text",
                "text": json.dumps(soap_json_content)
            }
        ]
    })
    
    mock_response = {
        "body": MagicMock()
    }
    mock_response["body"].read.return_value = response_body.encode("utf-8")
    return mock_response


class TestSOAPNoteGeneration:
    """Tests for SOAP note generation with Claude."""

    @patch("src.clinical_notes.soap.generator.bedrock")
    def test_generate_soap_note_returns_dict(self, mock_bedrock):
        """generate_soap_note should return a dictionary with SOAP sections."""
        expected_soap = {
            "subjective": "Patient reports headache",
            "objective": "Exam normal",
            "assessment": "Tension headache",
            "plan": "Rest and fluids"
        }
        
        mock_bedrock.invoke_model.return_value = create_mock_bedrock_response(expected_soap)
        
        encounter = {
            "full_transcript": "Doctor: How are you? Patient: I have a headache.",
            "speaker_segments": []
        }
        
        result = generate_soap_note(encounter)
        
        assert isinstance(result, dict)
        assert result == expected_soap

    @patch("src.clinical_notes.soap.generator.bedrock")
    def test_generate_soap_note_includes_encounter_id_if_provided(self, mock_bedrock):
        """generate_soap_note should add encounter_id if provided."""
        expected_soap = {
            "subjective": "Test",
            "objective": "Test",
            "assessment": "Test",
            "plan": "Test"
        }
        
        mock_bedrock.invoke_model.return_value = create_mock_bedrock_response(expected_soap)
        
        encounter = {"full_transcript": "Test"}
        encounter_id = "test-encounter-123"
        
        result = generate_soap_note(
            encounter,
            encounter_id=encounter_id
        )
        
        assert result["encounter_id"] == encounter_id

    @patch("src.clinical_notes.soap.generator.bedrock")
    def test_generate_soap_note_includes_correlation_id_if_provided(self, mock_bedrock):
        """generate_soap_note should add correlation_id if provided."""
        expected_soap = {
            "subjective": "Test",
            "objective": "Test",
            "assessment": "Test",
            "plan": "Test"
        }
        
        mock_bedrock.invoke_model.return_value = create_mock_bedrock_response(expected_soap)
        
        encounter = {"full_transcript": "Test"}
        correlation_id = "test-correlation-456"
        
        result = generate_soap_note(
            encounter,
            correlation_id=correlation_id
        )
        
        assert result["correlation_id"] == correlation_id

    @patch("src.clinical_notes.soap.generator.bedrock")
    def test_generate_soap_note_calls_bedrock_invoke_model(self, mock_bedrock):
        """generate_soap_note should call bedrock.invoke_model."""
        expected_soap = {
            "subjective": "Test",
            "objective": "Test",
            "assessment": "Test",
            "plan": "Test"
        }
        
        mock_bedrock.invoke_model.return_value = create_mock_bedrock_response(expected_soap)
        
        encounter = {"full_transcript": "Test"}
        generate_soap_note(encounter)
        
        mock_bedrock.invoke_model.assert_called_once()
        call_kwargs = mock_bedrock.invoke_model.call_args[1]
        assert "modelId" in call_kwargs
        assert "body" in call_kwargs

    @patch("src.clinical_notes.soap.generator.bedrock")
    def test_generate_soap_note_uses_correct_model(self, mock_bedrock):
        """generate_soap_note should use Claude 3.5 Sonnet model."""
        expected_soap = {
            "subjective": "Test",
            "objective": "Test",
            "assessment": "Test",
            "plan": "Test"
        }
        
        mock_bedrock.invoke_model.return_value = create_mock_bedrock_response(expected_soap)
        
        encounter = {"full_transcript": "Test"}
        generate_soap_note(encounter)
        
        call_kwargs = mock_bedrock.invoke_model.call_args[1]
        assert call_kwargs["modelId"] == "anthropic.claude-3-sonnet-20240229-v1:0"

    @patch("src.clinical_notes.soap.generator.bedrock")
    def test_generate_soap_note_passes_encounter_data_to_model(self, mock_bedrock):
        """generate_soap_note should include encounter data in the prompt."""
        expected_soap = {
            "subjective": "Test",
            "objective": "Test",
            "assessment": "Test",
            "plan": "Test"
        }
        
        mock_bedrock.invoke_model.return_value = create_mock_bedrock_response(expected_soap)
        
        encounter = {
            "full_transcript": "Specific medical transcript content",
            "speaker_segments": [
                {"speaker": "spk_0", "text": "Doctor speaking"}
            ]
        }
        
        generate_soap_note(encounter)
        
        call_kwargs = mock_bedrock.invoke_model.call_args[1]
        body = json.loads(call_kwargs["body"])
        
        # Verify encounter data is in the body
        user_message = body["messages"][0]["content"]
        assert "Specific medical transcript content" in user_message

    @patch("src.clinical_notes.soap.generator.bedrock")
    def test_generate_soap_note_with_all_soap_sections(self, mock_bedrock):
        """generate_soap_note response should include all four SOAP sections."""
        complete_soap = {
            "subjective": {
                "presenting_complaint": "Headaches for 2 weeks",
                "history": "Started suddenly",
                "symptoms": "Throbbing pain"
            },
            "objective": {
                "examination": "Normal",
                "findings": "BP 120/80"
            },
            "assessment": {
                "diagnosis": "Tension headache",
                "differential": "Migraine"
            },
            "plan": {
                "treatment": "Rest and analgesia",
                "followup": "Review in 1 week"
            }
        }
        
        mock_bedrock.invoke_model.return_value = create_mock_bedrock_response(complete_soap)
        
        encounter = {"full_transcript": "Test encounter"}
        result = generate_soap_note(encounter)
        
        assert "subjective" in result
        assert "objective" in result
        assert "assessment" in result
        assert "plan" in result

    @patch("src.clinical_notes.soap.generator.bedrock")
    def test_generate_soap_note_temperature_is_conservative(self, mock_bedrock):
        """generate_soap_note should use low temperature (0.2) for conservative output."""
        expected_soap = {
            "subjective": "Test",
            "objective": "Test",
            "assessment": "Test",
            "plan": "Test"
        }
        
        mock_bedrock.invoke_model.return_value = create_mock_bedrock_response(expected_soap)
        
        encounter = {"full_transcript": "Test"}
        generate_soap_note(encounter)
        
        call_kwargs = mock_bedrock.invoke_model.call_args[1]
        body = json.loads(call_kwargs["body"])
        
        assert body["temperature"] == 0.2

    @patch("src.clinical_notes.soap.generator.bedrock")
    def test_generate_soap_note_uses_nova_model_when_requested(self, mock_bedrock):
        """generate_soap_note should use Nova model when model='nova'."""
        expected_soap = {
            "subjective": "Test",
            "objective": "Test",
            "assessment": "Test",
            "plan": "Test"
        }

        mock_bedrock.invoke_model.return_value = create_mock_bedrock_response(expected_soap)

        encounter = {"full_transcript": "Test"}
        generate_soap_note(encounter, model="nova")

        call_kwargs = mock_bedrock.invoke_model.call_args[1]
        # Bedrock may accept either short model id or full ARN; verify it contains 'nova'
        assert "nova" in call_kwargs["modelId"]
        body = json.loads(call_kwargs["body"])
        # Nova adapter places prompt under `input`
        assert "input" in body


class TestSOAPNoteValidation:
    """Tests for SOAP note content validation."""

    @patch("src.clinical_notes.soap.generator.bedrock")
    def test_generate_soap_note_returns_valid_json(self, mock_bedrock):
        """Generated SOAP note should be valid JSON."""
        soap_content = {
            "subjective": "Patient reports symptoms",
            "objective": "Examination performed",
            "assessment": "Working diagnosis",
            "plan": "Treatment plan"
        }
        
        mock_bedrock.invoke_model.return_value = create_mock_bedrock_response(soap_content)
        
        encounter = {"full_transcript": "Test"}
        result = generate_soap_note(encounter)
        
        # Should be able to serialize back to JSON (no circular references, etc.)
        json_str = json.dumps(result)
        parsed = json.loads(json_str)
        assert parsed == result

    @patch("src.clinical_notes.soap.generator.bedrock")
    def test_generate_soap_note_preserves_string_values(self, mock_bedrock):
        """SOAP note string values should be preserved as-is."""
        soap_content = {
            "subjective": "Very specific patient-reported information",
            "objective": "Documented findings from examination",
            "assessment": "Clinical impression with qualifiers",
            "plan": "Specific management actions"
        }
        
        mock_bedrock.invoke_model.return_value = create_mock_bedrock_response(soap_content)
        
        encounter = {"full_transcript": "Test"}
        result = generate_soap_note(encounter)
        
        assert result["subjective"] == "Very specific patient-reported information"
        assert result["objective"] == "Documented findings from examination"
        assert result["assessment"] == "Clinical impression with qualifiers"
        assert result["plan"] == "Specific management actions"


class TestSOAPNoteEdgeCases:
    """Tests for edge cases in SOAP note generation."""

    @patch("src.clinical_notes.soap.generator.bedrock")
    def test_generate_soap_note_with_minimal_encounter(self, mock_bedrock):
        """generate_soap_note should handle minimal encounter data."""
        expected_soap = {
            "subjective": "Minimal info",
            "objective": "Not documented",
            "assessment": "Unclear",
            "plan": "Follow up"
        }
        
        mock_bedrock.invoke_model.return_value = create_mock_bedrock_response(expected_soap)
        
        encounter = {"full_transcript": ""}
        result = generate_soap_note(encounter)
        
        assert isinstance(result, dict)
        assert all(key in result for key in ["subjective", "objective", "assessment", "plan"])

    @patch("src.clinical_notes.soap.generator.bedrock")
    def test_generate_soap_note_with_complex_encounter(self, mock_bedrock):
        """generate_soap_note should handle complex, nested encounter data."""
        expected_soap = {
            "subjective": "Complex case",
            "objective": "Multiple findings",
            "assessment": "Differential diagnosis",
            "plan": "Multi-step plan"
        }
        
        mock_bedrock.invoke_model.return_value = create_mock_bedrock_response(expected_soap)
        
        encounter = {
            "full_transcript": "Long transcript...",
            "speaker_segments": [{"speaker": "spk_0", "text": "..."} for _ in range(10)],
            "medical_entities": {
                "entities": [
                    {"type": "MEDICATION", "text": "drug1"},
                    {"type": "SYMPTOM", "text": "symptom1"}
                ]
            },
            "phi_entities": {"entities": []},
            "speaker_analysis": [{"speaker": "spk_0", "entities": []}],
            "metadata": {"version": "1.0"}
        }
        
        result = generate_soap_note(encounter)
        
        assert isinstance(result, dict)
        assert len(result) >= 4  # At least SOAP sections

    @patch("src.clinical_notes.soap.generator.bedrock")
    def test_generate_soap_note_without_optional_ids(self, mock_bedrock):
        """generate_soap_note should work without encounter_id and correlation_id."""
        expected_soap = {
            "subjective": "Test",
            "objective": "Test",
            "assessment": "Test",
            "plan": "Test"
        }
        
        mock_bedrock.invoke_model.return_value = create_mock_bedrock_response(expected_soap)
        
        encounter = {"full_transcript": "Test"}
        result = generate_soap_note(encounter)
        
        assert result == expected_soap
        assert "encounter_id" not in result
        assert "correlation_id" not in result


def test_generate_soap_note_uses_langchain_if_enabled(monkeypatch):
    """If USE_LANGCHAIN=1, generator should call LangChain adapter instead of Bedrock."""
    expected_soap = {
        "subjective": "LC",
        "objective": "LC",
        "assessment": "LC",
        "plan": "LC"
    }

    # Patch the langchain adapter to return our expected soap
    def fake_langchain(encounter_json, model_name):
        return expected_soap

    monkeypatch.setenv("USE_LANGCHAIN", "1")
    monkeypatch.setattr("src.clinical_notes.soap.langchain_adapter.call_model_via_langchain", fake_langchain)

    # Ensure bedrock is not called by not patching it; call should succeed via langchain
    encounter = {"full_transcript": "Test"}
    result = generate_soap_note(encounter)
    assert result == expected_soap
