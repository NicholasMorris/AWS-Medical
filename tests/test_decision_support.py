"""Tests for clinical decision support module."""

import json
import pytest
from unittest.mock import patch, MagicMock
from src.clinical_notes.decision_support import generate_decision_support_prompts


def create_mock_bedrock_response(prompts: list) -> dict:
    """Create a mock Bedrock response with decision support prompts."""
    return {
        "body": MagicMock(read=lambda: json.dumps({
            "content": [{"text": json.dumps({"prompts": prompts})}]
        }).encode("utf-8"))
    }


@pytest.fixture
def sample_encounter_json():
    """Sample encounter data for testing."""
    return {
        "encounter_id": "test-encounter-123",
        "correlation_id": "test-correlation-456",
        "timestamp": 1234567890,
        "transcription": "Patient reports mild headache for 2 days. No fever. Sleep normal.",
        "medical_entities": [
            {"Type": "SYMPTOM", "Text": "headache", "Score": 0.95},
            {"Type": "NEGATION", "Text": "No fever", "Score": 0.92}
        ],
        "patient_info": {"age": 45, "gender": "F"},
    }


@patch("src.clinical_notes.decision_support.bedrock.invoke_model")
def test_generate_decision_support_basic(mock_invoke, sample_encounter_json):
    """Test basic decision support generation."""
    # Mock response
    mock_invoke.return_value = create_mock_bedrock_response([
        "Consider: Migraine vs tension headache - any visual changes?",
        "No red flags noted - no fever, alert, normal sleep.",
        "Document: exact location, triggers, any associated symptoms."
    ])
    
    result = generate_decision_support_prompts(sample_encounter_json)
    
    assert "prompts" in result
    assert len(result["prompts"]) == 3
    assert "Consider:" in result["prompts"][0]


@patch("src.clinical_notes.decision_support.bedrock.invoke_model")
def test_decision_support_includes_encounter_id(mock_invoke, sample_encounter_json):
    """Test that encounter_id is included in response."""
    mock_invoke.return_value = create_mock_bedrock_response([
        "Consider: differential diagnosis",
        "No red flags found.",
        "Document: patient education provided."
    ])
    
    result = generate_decision_support_prompts(
        sample_encounter_json,
        encounter_id="test-123"
    )
    
    assert result["encounter_id"] == "test-123"


@patch("src.clinical_notes.decision_support.bedrock.invoke_model")
def test_decision_support_non_diagnostic(mock_invoke, sample_encounter_json):
    """Test that prompts are non-diagnostic (surfaces context, not diagnosis)."""
    mock_invoke.return_value = create_mock_bedrock_response([
        "Consider: differential diagnoses to explore",
        "No red flags identified - normal sleep, no fever",
        "Document: patient counseling on headache management"
    ])
    
    result = generate_decision_support_prompts(sample_encounter_json)
    
    # Verify prompts don't contain diagnostic language
    prompts_text = " ".join(result["prompts"])
    assert "patient has" not in prompts_text.lower()
    assert "diagnosis" not in prompts_text.lower()


@patch("src.clinical_notes.decision_support.bedrock.invoke_model")
def test_decision_support_surfaces_context(mock_invoke, sample_encounter_json):
    """Test that prompts surface clinical context and risk factors."""
    mock_invoke.return_value = create_mock_bedrock_response([
        "Consider: any vision changes, photophobia, nausea?",
        "Red flag alerts: none identified",
        "Document: timing, severity (1-10), impact on function"
    ])
    
    result = generate_decision_support_prompts(sample_encounter_json)
    prompts_text = " ".join(result["prompts"])
    
    # Should surface context/questions
    assert "consider" in prompts_text.lower() or "context" in prompts_text.lower()


@patch("src.clinical_notes.decision_support.bedrock.invoke_model")
def test_decision_support_model_parameters(mock_invoke, sample_encounter_json):
    """Test that Bedrock is called with correct model and parameters."""
    mock_invoke.return_value = create_mock_bedrock_response([
        "Consider: questions to explore",
        "No red flags.",
        "Document: findings."
    ])
    
    generate_decision_support_prompts(sample_encounter_json)
    
    # Verify mock was called
    assert mock_invoke.called
    
    # Verify correct model
    call_kwargs = mock_invoke.call_args[1]
    # Bedrock may accept short model id or full ARN; verify it references Nova
    assert "nova" in call_kwargs["modelId"]
    
    # Verify body has correct structure
    body = json.loads(call_kwargs["body"])
    assert body["temperature"] == 0.3
    assert body["max_tokens"] == 500
    assert "messages" in body


@patch("src.clinical_notes.decision_support.bedrock.invoke_model")
def test_decision_support_empty_encounter(mock_invoke):
    """Test handling of empty encounter data."""
    mock_invoke.return_value = create_mock_bedrock_response([
        "Consider: obtain full history",
        "No data available.",
        "Document: complete assessment needed."
    ])
    
    empty_encounter = {
        "transcription": "",
        "medical_entities": [],
    }
    
    result = generate_decision_support_prompts(empty_encounter)
    
    assert "prompts" in result
    assert isinstance(result["prompts"], list)


@patch("src.clinical_notes.decision_support.bedrock.invoke_model")
def test_decision_support_with_complex_entities(mock_invoke):
    """Test decision support with multiple medical entities."""
    complex_encounter = {
        "encounter_id": "complex-123",
        "transcription": "Patient has been fatigued for 3 weeks. Weight loss of 5kg. No appetite.",
        "medical_entities": [
            {"Type": "SYMPTOM", "Text": "fatigued", "Score": 0.98},
            {"Type": "SYMPTOM", "Text": "Weight loss", "Score": 0.96},
            {"Type": "SYMPTOM", "Text": "No appetite", "Score": 0.94},
        ]
    }
    
    mock_invoke.return_value = create_mock_bedrock_response([
        "Consider: thyroid function, anemia, malignancy screening",
        "Red flags: significant weight loss, loss of appetite - need investigations",
        "Document: investigations ordered, follow-up date set"
    ])
    
    result = generate_decision_support_prompts(complex_encounter)
    
    assert "prompts" in result
    # Should contain clinical context
    assert any("Consider" in p for p in result["prompts"])


@patch("src.clinical_notes.decision_support.bedrock.invoke_model")
def test_decision_support_bedrock_error_handling(mock_invoke):
    """Test graceful error handling if Bedrock fails."""
    mock_invoke.side_effect = Exception("Bedrock service error")
    
    with pytest.raises(Exception):
        generate_decision_support_prompts({"transcription": "test"})


@patch("src.clinical_notes.decision_support.bedrock.invoke_model")
def test_decision_support_json_parsing(mock_invoke):
    """Test JSON parsing of Bedrock response."""
    mock_invoke.return_value = create_mock_bedrock_response([
        "First prompt",
        "Second prompt",
        "Third prompt",
        "Fourth prompt",
        "Fifth prompt"
    ])
    
    result = generate_decision_support_prompts({"transcription": "test"})
    
    # Should have parsed the JSON correctly
    assert isinstance(result["prompts"], list)
    assert len(result["prompts"]) == 5
    for prompt in result["prompts"]:
        assert isinstance(prompt, str)


@patch("src.clinical_notes.decision_support.bedrock.invoke_model")
def test_decision_support_without_encounter_id(mock_invoke):
    """Test that function works without explicit encounter_id."""
    mock_invoke.return_value = create_mock_bedrock_response([
        "Consider: differential",
        "No red flags",
        "Document: plan"
    ])
    
    result = generate_decision_support_prompts({"transcription": "test"})
    
    # Should not have encounter_id if not provided
    assert "encounter_id" not in result
    assert "prompts" in result


@patch("src.clinical_notes.decision_support.bedrock.invoke_model")
def test_decision_support_preserves_structure(mock_invoke, sample_encounter_json):
    """Test that original encounter data structure is not modified."""
    original_keys = set(sample_encounter_json.keys())
    mock_invoke.return_value = create_mock_bedrock_response([
        "Consider: prompt",
        "Red flag: none",
        "Document: findings"
    ])
    
    generate_decision_support_prompts(sample_encounter_json)
    
    # Original data should not be modified
    assert set(sample_encounter_json.keys()) == original_keys


@patch("src.clinical_notes.decision_support.bedrock.invoke_model")
def test_decision_support_model_switching(mock_invoke, sample_encounter_json):
    """Test that passing model='claude' uses Claude model id."""
    mock_invoke.return_value = create_mock_bedrock_response([
        "Consider: example",
        "No red flags.",
        "Document: example"
    ])

    generate_decision_support_prompts(sample_encounter_json, model="claude")

    assert mock_invoke.called
    call_kwargs = mock_invoke.call_args[1]
    assert "claude" in call_kwargs["modelId"] or "anthropic" in call_kwargs["modelId"]
