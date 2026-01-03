import json
import boto3
from typing import Dict, Optional
from src.common.aws import get_bedrock_runtime

REGION = "ap-southeast-2"
MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

bedrock = get_bedrock_runtime()

def generate_soap_note(
    encounter_json: Dict,
    encounter_id: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> Dict:
    """
    Generate a clinical SOAP note from transcription + entity JSON.
    
    Args:
        encounter_json: Medical encounter data from transcription
        encounter_id: Optional encounter ID for correlation
        correlation_id: Optional correlation ID for tracking
        
    Returns:
        Dict with SOAP note structure and metadata
    """

    system_prompt = """
You are a clinical documentation assistant for Australian General Practice.

Your task is to generate a SOAP note strictly from the provided encounter data.

Rules:
- Do NOT invent symptoms, diagnoses, or findings
- Use only information explicitly stated or clearly implied
- Preserve negative findings (e.g. "no vomiting")
- Use conservative clinical language ("likely", "consistent with")
- Do NOT provide medical advice beyond what the GP already said
- The output must be suitable for GP review and editing
- Follow Australian clinical documentation conventions
"""

    user_prompt = f"""
Encounter data (JSON):
{json.dumps(encounter_json, indent=2)}

Generate a SOAP note with the following structure:

Subjective:
- Presenting complaint
- History of presenting illness
- Associated symptoms
- Explicit negatives

Objective:
- Examination findings (if stated)
- If none stated, say "Examination not documented"

Assessment:
- GP-stated working diagnosis or impression
- Differential only if explicitly mentioned
- Avoid certainty

Plan:
- Management advice discussed
- Medications mentioned
- Follow-up or safety-netting if stated

Return valid JSON only with keys:
subjective, objective, assessment, plan
"""

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 800,
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

    soap_json = model_response["content"][0]["text"]
    soap_data = json.loads(soap_json)
    
    # Add metadata if provided
    if encounter_id:
        soap_data['encounter_id'] = encounter_id
    if correlation_id:
        soap_data['correlation_id'] = correlation_id
    
    return soap_data