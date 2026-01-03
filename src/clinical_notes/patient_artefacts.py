"""Patient-ready artefacts: handout, visit summary, follow-up checklist."""

import json
from typing import Dict, Optional
from src.common.aws import get_bedrock_runtime

MODEL_ID = "amazon.nova-2-lite-v1:0"

bedrock = get_bedrock_runtime()


def generate_patient_handout(
    encounter_json: Dict,
    encounter_id: Optional[str] = None
) -> Dict:
    """
    Generate plain English patient handout (take-home advice).
    
    NO medical jargon. Written for patient understanding.
    
    Args:
        encounter_json: Medical encounter data from transcription
        encounter_id: Optional encounter ID for correlation
        
    Returns:
        Dict with patient handout text and metadata
    """

    system_prompt = """
You are a patient education specialist for Australian General Practice.
Write a clear, friendly handout for patients - NO medical jargon.

Use simple language:
- "pain" not "discomfort"
- "tired" not "fatigue"
- "blood pressure" not "BP"
- "take a break from screens" not "reduce computer exposure"

Structure:
- What we discussed today (plain language)
- What you can do at home (actionable steps)
- When to seek help (clear warning signs)
- Questions to ask your GP next visit (encourage engagement)

Tone: supportive, encouraging, empowering.
Length: 150-200 words (fits on 1 page)
"""

    user_prompt = f"""
Encounter data (JSON):
{json.dumps(encounter_json, indent=2)}

Create a patient handout in plain English.
Include: what was discussed, what patient can do, warning signs, next steps.
NO medical terms. Write as if talking to a friend.
Return plain text only (not JSON).
"""

    body = {
        "max_tokens": 300,
        "temperature": 0.2,
        "messages": [
            {"role": "user", "content": user_prompt}
        ]
    }

    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(body)
    )

    raw_output = response["body"].read().decode("utf-8")
    model_response = json.loads(raw_output)
    handout_text = model_response["content"][0]["text"]
    
    result = {"patient_handout": handout_text}
    if encounter_id:
        result["encounter_id"] = encounter_id
    
    return result


def generate_after_visit_summary(
    encounter_json: Dict,
    encounter_id: Optional[str] = None
) -> Dict:
    """
    Generate after-visit summary: what happened today in plain language.
    
    Patient-facing document of the encounter.
    
    Args:
        encounter_json: Medical encounter data from transcription
        encounter_id: Optional encounter ID for correlation
        
    Returns:
        Dict with after-visit summary text and metadata
    """

    system_prompt = """
You are writing a patient visit summary in plain English.
Summarize what happened today clearly and simply.

Include:
- Reason for visit
- What the GP found (examination/assessment)
- What we think is happening (GP's impression, NOT diagnosis)
- What you should do (advice given)
- When to follow up

Write as if the GP is writing a friendly letter to the patient.
NO medical jargon. Plain English only.
Length: 150-200 words.
"""

    user_prompt = f"""
Encounter data (JSON):
{json.dumps(encounter_json, indent=2)}

Write a friendly after-visit summary as if the GP is writing to the patient.
What happened at today's visit? What should the patient do?
Plain English, NO medical terms.
Return plain text only.
"""

    body = {
        "max_tokens": 300,
        "temperature": 0.2,
        "messages": [
            {"role": "user", "content": user_prompt}
        ]
    }

    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(body)
    )

    raw_output = response["body"].read().decode("utf-8")
    model_response = json.loads(raw_output)
    summary_text = model_response["content"][0]["text"]
    
    result = {"after_visit_summary": summary_text}
    if encounter_id:
        result["encounter_id"] = encounter_id
    
    return result


def generate_followup_checklist(
    encounter_json: Dict,
    encounter_id: Optional[str] = None
) -> Dict:
    """
    Generate patient-actionable follow-up checklist.
    
    What should the patient do at home? When should they follow up?
    
    Args:
        encounter_json: Medical encounter data from transcription
        encounter_id: Optional encounter ID for correlation
        
    Returns:
        Dict with follow-up checklist text and metadata
    """

    system_prompt = """
You are creating a patient follow-up checklist.
Make it ACTION-ORIENTED and SPECIFIC.

Format as a checklist the patient can use at home.
Include:
- This week: daily actions (rest, hydration, medication timing)
- This month: weekly check-ins (how are you doing?, any concerns?)
- When to contact GP: clear warning signs or if not improving

Make it encouraging and specific.
NO medical jargon. Plain English only.
Use checkboxes: ☐ action
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

    body = {
        "max_tokens": 300,
        "temperature": 0.2,
        "messages": [
            {"role": "user", "content": user_prompt}
        ]
    }

    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(body)
    )

    raw_output = response["body"].read().decode("utf-8")
    model_response = json.loads(raw_output)
    checklist_text = model_response["content"][0]["text"]
    
    result = {"followup_checklist": checklist_text}
    if encounter_id:
        result["encounter_id"] = encounter_id
    
    return result
