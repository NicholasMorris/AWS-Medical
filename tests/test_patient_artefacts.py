"""Tests for patient artefacts module."""

import json
import pytest
from unittest.mock import patch, MagicMock
from src.clinical_notes.patient_artefacts import (
    generate_patient_handout,
    generate_after_visit_summary,
    generate_followup_checklist
)


def create_mock_bedrock_response(text: str) -> dict:
    """Create a mock Bedrock response."""
    return {
        "body": MagicMock(read=lambda: json.dumps({
            "content": [{"text": text}]
        }).encode("utf-8"))
    }


@pytest.fixture
def sample_encounter_json():
    """Sample encounter data for testing."""
    return {
        "encounter_id": "test-encounter-123",
        "correlation_id": "test-correlation-456",
        "timestamp": 1234567890,
        "transcription": "Patient with mild cold. Rest recommended. Fluids. Back in 1 week if not better.",
        "medical_entities": [
            {"Type": "SYMPTOM", "Text": "cold", "Score": 0.95},
        ],
        "patient_info": {"age": 35, "gender": "M"},
    }


@patch("src.clinical_notes.patient_artefacts.bedrock.invoke_model")
def test_patient_handout_basic(mock_invoke, sample_encounter_json):
    """Test basic patient handout generation."""
    handout_text = "You have a cold. Get rest, drink plenty of water, and come back if not better in a week."
    mock_invoke.return_value = create_mock_bedrock_response(handout_text)
    
    result = generate_patient_handout(sample_encounter_json)
    
    assert "patient_handout" in result
    assert "You have a cold" in result["patient_handout"]


@patch("src.clinical_notes.patient_artefacts.bedrock.invoke_model")
def test_patient_handout_plain_language(mock_invoke, sample_encounter_json):
    """Test that handout uses plain language, not medical jargon."""
    handout_text = "You're tired and achey. Take a break from screens, drink lots of water."
    mock_invoke.return_value = create_mock_bedrock_response(handout_text)
    
    result = generate_patient_handout(sample_encounter_json)
    
    # Verify plain language (examples of what NOT to use)
    handout = result["patient_handout"].lower()
    assert "tired" in handout or "achey" in handout  # Plain language
    # Note: Some legitimate medical terms might appear, but should be explained


@patch("src.clinical_notes.patient_artefacts.bedrock.invoke_model")
def test_patient_handout_includes_encounter_id(mock_invoke, sample_encounter_json):
    """Test that encounter_id is included when provided."""
    mock_invoke.return_value = create_mock_bedrock_response("You have a cold. Rest and fluids.")
    
    result = generate_patient_handout(
        sample_encounter_json,
        encounter_id="handout-test-123"
    )
    
    assert result["encounter_id"] == "handout-test-123"
    assert "patient_handout" in result


@patch("src.clinical_notes.patient_artefacts.bedrock.invoke_model")
def test_after_visit_summary_basic(mock_invoke, sample_encounter_json):
    """Test basic after-visit summary generation."""
    summary_text = "Today we discussed your cold. You have a viral infection. Rest and fluids will help."
    mock_invoke.return_value = create_mock_bedrock_response(summary_text)
    
    result = generate_after_visit_summary(sample_encounter_json)
    
    assert "after_visit_summary" in result
    assert "Today" in result["after_visit_summary"] or "today" in result["after_visit_summary"].lower()


@patch("src.clinical_notes.patient_artefacts.bedrock.invoke_model")
def test_after_visit_summary_plain_english(mock_invoke, sample_encounter_json):
    """Test that summary uses plain, friendly language."""
    summary_text = "Hi, here's what we found today: You have a cold causing your tiredness and cough. Drink plenty of water, rest, and come back if not better."
    mock_invoke.return_value = create_mock_bedrock_response(summary_text)
    
    result = generate_after_visit_summary(sample_encounter_json)
    summary = result["after_visit_summary"].lower()
    
    # Should use plain language
    assert "tiredness" in summary or "cough" in summary or "water" in summary


@patch("src.clinical_notes.patient_artefacts.bedrock.invoke_model")
def test_after_visit_summary_includes_encounter_id(mock_invoke, sample_encounter_json):
    """Test that encounter_id is included when provided."""
    mock_invoke.return_value = create_mock_bedrock_response("Summary of today's visit.")
    
    result = generate_after_visit_summary(
        sample_encounter_json,
        encounter_id="summary-test-456"
    )
    
    assert result["encounter_id"] == "summary-test-456"


@patch("src.clinical_notes.patient_artefacts.bedrock.invoke_model")
def test_followup_checklist_basic(mock_invoke, sample_encounter_json):
    """Test basic follow-up checklist generation."""
    checklist_text = "☐ Rest for 2-3 days\n☐ Drink 2-3 liters of water daily\n☐ Call if no improvement in 1 week"
    mock_invoke.return_value = create_mock_bedrock_response(checklist_text)
    
    result = generate_followup_checklist(sample_encounter_json)
    
    assert "followup_checklist" in result
    assert "☐" in result["followup_checklist"]


@patch("src.clinical_notes.patient_artefacts.bedrock.invoke_model")
def test_followup_checklist_actionable(mock_invoke, sample_encounter_json):
    """Test that checklist contains specific, actionable items."""
    checklist_text = "This week:\n☐ Rest at least 8 hours nightly\n☐ Hydrate: drink water every 2 hours\n☐ Take paracetamol if needed\n\nWhen to seek help:\n☐ If fever over 38.5C\n☐ If cough worsens or lasts > 2 weeks"
    mock_invoke.return_value = create_mock_bedrock_response(checklist_text)
    
    result = generate_followup_checklist(sample_encounter_json)
    checklist = result["followup_checklist"].lower()
    
    # Should have specific, actionable items
    assert "☐" in result["followup_checklist"]
    assert "rest" in checklist or "hydrate" in checklist or "drink" in checklist


@patch("src.clinical_notes.patient_artefacts.bedrock.invoke_model")
def test_followup_checklist_includes_encounter_id(mock_invoke, sample_encounter_json):
    """Test that encounter_id is included when provided."""
    mock_invoke.return_value = create_mock_bedrock_response("☐ Rest\n☐ Drink water")
    
    result = generate_followup_checklist(
        sample_encounter_json,
        encounter_id="checklist-test-789"
    )
    
    assert result["encounter_id"] == "checklist-test-789"


@patch("src.clinical_notes.patient_artefacts.bedrock.invoke_model")
def test_all_artefacts_model_parameters(mock_invoke, sample_encounter_json):
    """Test that all functions use correct model and parameters."""
    mock_invoke.return_value = create_mock_bedrock_response("Sample text")
    
    functions = [
        generate_patient_handout,
        generate_after_visit_summary,
        generate_followup_checklist
    ]
    
    for func in functions:
        mock_invoke.reset_mock()
        func(sample_encounter_json)
        
        # Verify mock was called
        assert mock_invoke.called
        
        # Verify correct model
        call_kwargs = mock_bedrock = mock_invoke.call_args[1]
        # Bedrock may accept short model id or full ARN; verify it references Nova
        assert "nova" in call_kwargs["modelId"]
        
        # Verify body has correct structure
        body = json.loads(call_kwargs["body"])
        assert body["temperature"] == 0.2
        assert body["max_tokens"] == 300
        assert "messages" in body


@patch("src.clinical_notes.patient_artefacts.bedrock.invoke_model")
def test_patient_artefacts_model_switching(mock_invoke, sample_encounter_json):
    """Test that patient artefacts functions can switch to Claude model."""
    mock_invoke.return_value = create_mock_bedrock_response("Sample text")

    funcs = [
        (generate_patient_handout, {}),
        (generate_after_visit_summary, {}),
        (generate_followup_checklist, {})
    ]

    for func, kwargs in funcs:
        mock_invoke.reset_mock()
        func(sample_encounter_json, model="claude")
        assert mock_invoke.called
        call_kwargs = mock_invoke.call_args[1]
        assert "claude" in call_kwargs["modelId"] or "anthropic" in call_kwargs["modelId"]


@patch("src.clinical_notes.patient_artefacts.bedrock.invoke_model")
def test_handout_without_encounter_id(mock_invoke):
    """Test that handout works without explicit encounter_id."""
    mock_invoke.return_value = create_mock_bedrock_response("Rest well.")
    
    result = generate_patient_handout({"transcription": "test"})
    
    # Should not have encounter_id if not provided
    assert "encounter_id" not in result
    assert "patient_handout" in result


@patch("src.clinical_notes.patient_artefacts.bedrock.invoke_model")
def test_summary_without_encounter_id(mock_invoke):
    """Test that summary works without explicit encounter_id."""
    mock_invoke.return_value = create_mock_bedrock_response("Visit summary.")
    
    result = generate_after_visit_summary({"transcription": "test"})
    
    # Should not have encounter_id if not provided
    assert "encounter_id" not in result
    assert "after_visit_summary" in result


@patch("src.clinical_notes.patient_artefacts.bedrock.invoke_model")
def test_checklist_without_encounter_id(mock_invoke):
    """Test that checklist works without explicit encounter_id."""
    mock_invoke.return_value = create_mock_bedrock_response("☐ Item 1\n☐ Item 2")
    
    result = generate_followup_checklist({"transcription": "test"})
    
    # Should not have encounter_id if not provided
    assert "encounter_id" not in result
    assert "followup_checklist" in result


@patch("src.clinical_notes.patient_artefacts.bedrock.invoke_model")
def test_handout_complex_encounter(mock_invoke):
    """Test handout with complex medical scenario."""
    complex_encounter = {
        "transcription": "Patient with diabetes, hypertension, recent chest pain.",
        "medical_entities": [
            {"Type": "SYMPTOM", "Text": "chest pain", "Score": 0.98},
            {"Type": "CONDITION", "Text": "diabetes", "Score": 0.96},
            {"Type": "CONDITION", "Text": "hypertension", "Score": 0.95},
        ]
    }
    
    handout_text = "You have high blood pressure and diabetes. Take your medicines every day. Watch for chest pain and call 000 if it happens."
    mock_invoke.return_value = create_mock_bedrock_response(handout_text)
    
    result = generate_patient_handout(complex_encounter)
    
    assert "patient_handout" in result
    # Should mention actionable advice
    assert len(result["patient_handout"]) > 0


@patch("src.clinical_notes.patient_artefacts.bedrock.invoke_model")
def test_summary_complex_encounter(mock_invoke):
    """Test summary with complex medical scenario."""
    complex_encounter = {
        "transcription": "Patient with diabetes and chest pain. EKG done.",
        "medical_entities": [
            {"Type": "CONDITION", "Text": "diabetes", "Score": 0.95},
            {"Type": "SYMPTOM", "Text": "chest pain", "Score": 0.98},
        ]
    }
    
    summary_text = "Today we examined you for chest pain. Your heart rhythm looks okay on EKG. Continue taking your diabetes medicine. Come back in 1 week."
    mock_invoke.return_value = create_mock_bedrock_response(summary_text)
    
    result = generate_after_visit_summary(complex_encounter)
    
    assert "after_visit_summary" in result
    summary = result["after_visit_summary"].lower()
    # Should mention what was done
    assert "ekg" in summary or "examined" in summary or "heart" in summary


@patch("src.clinical_notes.patient_artefacts.bedrock.invoke_model")
def test_checklist_complex_encounter(mock_invoke):
    """Test checklist with complex medical scenario."""
    complex_encounter = {
        "transcription": "Patient on multiple medications. Needs to monitor blood pressure.",
        "medical_entities": [
            {"Type": "CONDITION", "Text": "hypertension", "Score": 0.95},
        ]
    }
    
    checklist_text = "Daily:\n☐ Take all medicines (blood pressure, diabetes)\n☐ Check blood pressure at 9am\n☐ Record reading\n\nWatch for:\n☐ Severe headache\n☐ Chest pain\n☐ Shortness of breath\n\nCall doctor if any of these happen."
    mock_invoke.return_value = create_mock_bedrock_response(checklist_text)
    
    result = generate_followup_checklist(complex_encounter)
    
    assert "followup_checklist" in result
    checklist = result["followup_checklist"].lower()
    # Should have multiple checkboxes
    assert result["followup_checklist"].count("☐") >= 3


@patch("src.clinical_notes.patient_artefacts.bedrock.invoke_model")
def test_handout_bedrock_error(mock_invoke):
    """Test error handling when Bedrock fails."""
    mock_invoke.side_effect = Exception("Bedrock service error")
    
    with pytest.raises(Exception):
        generate_patient_handout({"transcription": "test"})


@patch("src.clinical_notes.patient_artefacts.bedrock.invoke_model")
def test_summary_bedrock_error(mock_invoke):
    """Test error handling when Bedrock fails."""
    mock_invoke.side_effect = Exception("Bedrock service error")
    
    with pytest.raises(Exception):
        generate_after_visit_summary({"transcription": "test"})


@patch("src.clinical_notes.patient_artefacts.bedrock.invoke_model")
def test_checklist_bedrock_error(mock_invoke):
    """Test error handling when Bedrock fails."""
    mock_invoke.side_effect = Exception("Bedrock service error")
    
    with pytest.raises(Exception):
        generate_followup_checklist({"transcription": "test"})


@patch("src.clinical_notes.patient_artefacts.bedrock.invoke_model")
def test_handout_preserves_encounter_data(mock_invoke, sample_encounter_json):
    """Test that original encounter data is not modified."""
    original_keys = set(sample_encounter_json.keys())
    mock_invoke.return_value = create_mock_bedrock_response("Handout text.")
    
    generate_patient_handout(sample_encounter_json)
    
    # Original data should not be modified
    assert set(sample_encounter_json.keys()) == original_keys


@patch("src.clinical_notes.patient_artefacts.bedrock.invoke_model")
def test_summary_preserves_encounter_data(mock_invoke, sample_encounter_json):
    """Test that original encounter data is not modified."""
    original_keys = set(sample_encounter_json.keys())
    mock_invoke.return_value = create_mock_bedrock_response("Summary text.")
    
    generate_after_visit_summary(sample_encounter_json)
    
    # Original data should not be modified
    assert set(sample_encounter_json.keys()) == original_keys


@patch("src.clinical_notes.patient_artefacts.bedrock.invoke_model")
def test_checklist_preserves_encounter_data(mock_invoke, sample_encounter_json):
    """Test that original encounter data is not modified."""
    original_keys = set(sample_encounter_json.keys())
    mock_invoke.return_value = create_mock_bedrock_response("☐ Item 1\n☐ Item 2")
    
    generate_followup_checklist(sample_encounter_json)
    
    # Original data should not be modified
    assert set(sample_encounter_json.keys()) == original_keys
