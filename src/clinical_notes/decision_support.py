"""Decision support prompt generation - clinical context without diagnosis."""

import json
from typing import Dict, Optional
from src.common.aws import get_bedrock_runtime
from src.common.models import MODEL_MAP, get_default_model

bedrock = get_bedrock_runtime()


def generate_decision_support_prompts(
    encounter_json: Dict,
    encounter_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    model: str = None,
) -> Dict:
    """
    Generate decision support prompts ("Did you consider?") from encounter data.
    
    Surfaces clinical context, red flags, and documentation gaps WITHOUT diagnosing.
    Examples:
    - "No red flag headache symptoms detected (vomiting, focal neurology, sudden onset)."
    - "High stress and poor sleep identified — common contributors to tension headache."
    - "Consider documenting screen time/posture advice (already discussed verbally)."
    
    Args:
        encounter_json: Medical encounter data from transcription
        encounter_id: Optional encounter ID for correlation
        correlation_id: Optional correlation ID for tracking
        
    Returns:
        Dict with decision support prompts list and metadata
    """

    system_prompt = """
You are a clinical decision support assistant for Australian General Practice.

Your task is to surface clinical context from the encounter data ONLY.

CRITICAL RULES - YOU MUST NOT DIAGNOSE:
- Do NOT suggest diagnoses or diagnostic labels
- Do NOT tell the patient they "have" a condition
- Do NOT provide medical advice
- DO surface relevant context: risk factors, lifestyle contributors, red flags observed
- DO highlight what was discussed but not yet documented
- DO note absence of red flag symptoms
- Use conservative, suggestive language: "Consider", "May be relevant", "No red flags observed"

Examples of GOOD prompts:
- "No red flag symptoms detected (sudden onset, focal neurology, vomiting)."
- "Stress and poor sleep identified — known contributors to presentation."
- "Consider documenting stretching/ergonomic advice if discussed."

Examples of BAD prompts (DO NOT DO):
- "Patient has tension headaches" (diagnostic)
- "Likely caused by screen time" (diagnosis by elimination)
- "Should refer to neurology" (medical advice)

Output a JSON object with one key:
- prompts: list of 3-5 decision support suggestions (strings)
"""

    user_prompt = f"""
Encounter data (JSON):
{json.dumps(encounter_json, indent=2)}

Generate 3-5 decision support prompts that surface clinical context without diagnosing.
Focus on:
1. Red flag symptoms NOT observed (if applicable to presenting complaint)
2. Risk factors or lifestyle contributors mentioned
3. Examination/investigation gaps or absences to note
4. Advice discussed but not yet documented
5. Follow-up or safety-netting opportunities

Return valid JSON with key: prompts (list of strings)
Each prompt should start with "Consider...", "No red flags...", or "Document..."
"""

    body = {
        "max_tokens": 500,
        "temperature": 0.3,
        "messages": [
            {"role": "user", "content": user_prompt}
        ]
    }

    # Decision support defaults to 'nova' for speed/cost (module-specific default)
    model_name = model or "nova"
    model_id = MODEL_MAP.get(model_name, MODEL_MAP["nova"])

    response = bedrock.invoke_model(
        modelId=model_id,
        body=json.dumps(body)
    )

    raw_output = response["body"].read().decode("utf-8")
    model_response = json.loads(raw_output)

    prompts_json = model_response["content"][0]["text"]
    prompts_data = json.loads(prompts_json)
    
    # Validate that output contains prompts
    if "prompts" not in prompts_data:
        prompts_data = {"prompts": []}
    
    # Add metadata if provided
    if encounter_id:
        prompts_data['encounter_id'] = encounter_id
    if correlation_id:
        prompts_data['correlation_id'] = correlation_id
    
    return prompts_data
