"""Patient-ready artefacts: handout, visit summary, follow-up checklist.

Each function calls Bedrock (via cached client) using Nova Invoke API.
Functions accept a `debug: bool` parameter and only print brief lines to stdout
when `debug` is True; structured logging uses the module logger.
"""

import json
import logging
from typing import Dict, Optional
from src.common.aws import get_bedrock_runtime, build_nova_request, parse_nova_response
from src.common.models import MODEL_MAP

logger = logging.getLogger(__name__)
bedrock = get_bedrock_runtime()


def generate_patient_handout(
    encounter_json: Dict,
    encounter_id: Optional[str] = None,
    model: str = "nova",
    debug: bool = False,
) -> Dict:
    """
    Generate plain English patient handout (take-home advice).

    NO medical jargon. Written for patient understanding.

    Args:
        encounter_json: Medical encounter data from transcription
        encounter_id: Optional encounter ID for correlation
        model: Model to use (default 'nova')
        debug: If True, print a short debug line to stdout

    Returns:
        Dict with patient handout text and metadata
    """

    user_prompt = f"""
Encounter data (JSON):
{json.dumps(encounter_json, indent=2)}

Create a patient handout in plain English.
Include: what was discussed, what patient can do, warning signs, next steps.
NO medical terms. Write as if talking to a friend.
Return plain text only (not JSON).
"""

    body = build_nova_request(user_prompt, temperature=0.2, max_tokens=300)

    model_name = model or "nova"
    if model_name not in MODEL_MAP:
        raise ValueError(f"Unsupported model: {model_name}")
    model_id = MODEL_MAP[model_name]
    logger.debug("Patient handout using model '%s' -> %s", model_name, model_id)
    if debug:
        print(f"Patient handout: using model {model_name} -> {model_id}")

    response = bedrock.invoke_model(modelId=model_id, body=json.dumps(body))
    raw_output = response["body"].read()
    response_json = parse_nova_response(raw_output)

    # Response should be a dict with 'text' or similar key; if it's just a string, wrap it
    if isinstance(response_json, dict):
        handout_text = response_json.get("text", json.dumps(response_json))
    else:
        handout_text = str(response_json)

    result = {"patient_handout": handout_text}
    if encounter_id:
        result["encounter_id"] = encounter_id

    return result


def generate_after_visit_summary(
    encounter_json: Dict,
    encounter_id: Optional[str] = None,
    model: str = "nova",
    debug: bool = False,
) -> Dict:
    """
    Generate after-visit summary: what happened today in plain language.

    Args:
        encounter_json: Medical encounter data from transcription
        encounter_id: Optional encounter ID for correlation
        model: Model to use (default 'nova')
        debug: If True, print a short debug line to stdout

    Returns:
        Dict with after-visit summary text and metadata
    """

    user_prompt = f"""
Encounter data (JSON):
{json.dumps(encounter_json, indent=2)}

Write a friendly after-visit summary as if the GP is writing to the patient.
What happened at today's visit? What should the patient do?
Plain English, NO medical terms.
Return plain text only.
"""

    body = build_nova_request(user_prompt, temperature=0.2, max_tokens=300)

    model_name = model or "nova"
    if model_name not in MODEL_MAP:
        raise ValueError(f"Unsupported model: {model_name}")
    model_id = MODEL_MAP[model_name]
    logger.debug("After-visit summary using model '%s' -> %s", model_name, model_id)
    if debug:
        print(f"After-visit summary: using model {model_name} -> {model_id}")

    response = bedrock.invoke_model(modelId=model_id, body=json.dumps(body))
    raw_output = response["body"].read()
    response_json = parse_nova_response(raw_output)

    # Response should be a dict with 'text' or similar key; if it's just a string, wrap it
    if isinstance(response_json, dict):
        summary_text = response_json.get("text", json.dumps(response_json))
    else:
        summary_text = str(response_json)

    result = {"after_visit_summary": summary_text}
    if encounter_id:
        result["encounter_id"] = encounter_id
    return result


def generate_followup_checklist(
    encounter_json: Dict,
    encounter_id: Optional[str] = None,
    model: str = "nova",
    debug: bool = False,
) -> Dict:
    """
    Generate patient-actionable follow-up checklist.

    Args:
        encounter_json: Medical encounter data from transcription
        encounter_id: Optional encounter ID for correlation
        model: Model to use (default 'nova')
        debug: If True, print a short debug line to stdout

    Returns:
        Dict with follow-up checklist text and metadata
    """

    user_prompt = f"""
Encounter data (JSON):
{json.dumps(encounter_json, indent=2)}

Create a patient follow-up checklist with specific actions to do at home.
Include: daily actions, weekly check-ins, when to seek help.
Format as checkboxes the patient can print and tick off.
Plain English, NO medical terms.
Return plain text with checkboxes (☐).
"""

    body = build_nova_request(user_prompt, temperature=0.2, max_tokens=300)

    model_name = model or "nova"
    if model_name not in MODEL_MAP:
        raise ValueError(f"Unsupported model: {model_name}")
    model_id = MODEL_MAP[model_name]
    logger.debug("Follow-up checklist using model '%s' -> %s", model_name, model_id)
    if debug:
        print(f"Follow-up checklist: using model {model_name} -> {model_id}")

    response = bedrock.invoke_model(modelId=model_id, body=json.dumps(body))
    raw_output = response["body"].read()
    response_json = parse_nova_response(raw_output)

    # Response should be a dict with 'text' or similar key; if it's just a string, wrap it
    if isinstance(response_json, dict):
        checklist_text = response_json.get("text", json.dumps(response_json))
    else:
        checklist_text = str(response_json)

    result = {"followup_checklist": checklist_text}
    if encounter_id:
        result["encounter_id"] = encounter_id

    return result
