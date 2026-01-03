import json
import os
from typing import Dict, Optional
from src.common.aws import get_bedrock_runtime
from src.common.models import MODEL_MAP, get_default_model

# NOTE: model mapping/defaults are centralized in src.common.models

# Bedrock client (cached in common.aws)
bedrock = get_bedrock_runtime()


class ModelAdapter:
    """Adapter to build Bedrock request bodies and parse responses per model.

    Supports 'claude' and 'nova'. LangChain usage can be enabled by
    setting the environment variable `USE_LANGCHAIN=1` and installing
    `langchain` (optional).
    """

    def __init__(self, model_name: str = None):
        # If no model_name provided, fall back to global default
        self.model_name = model_name or get_default_model() or "claude"
        self.model_id = MODEL_MAP.get(self.model_name, MODEL_MAP["claude"])

    def build_request(self, encounter_json: Dict) -> Dict:
        """Return a request body compatible with the selected model."""
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

        # Claude (Anthropic) style body with messages
        if self.model_name == "claude":
            return {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 800,
                "temperature": 0.2,
                "messages": [
                    {"role": "user", "content": user_prompt}
                ],
            }

        # Nova: keep a similar structure but mark provider and use a conservative temperature
        return {
            "provider": "nova",
            "max_tokens": 800,
            "temperature": 0.2,
            "input": user_prompt,
        }

    def parse_response(self, response_body: bytes) -> Dict:
        """Parse the Bedrock response bytes into a Python dict containing the SOAP note."""
        raw = response_body.decode("utf-8")
        try:
            model_response = json.loads(raw)
        except Exception:
            # If response is plain JSON text, try to parse directly
            try:
                return json.loads(raw)
            except Exception:
                raise

        # Typical Bedrock wrapper: content[0].text contains model output
        try:
            soap_json = model_response["content"][0]["text"]
            return json.loads(soap_json)
        except Exception:
            # Fallback: if the model returned plain JSON string somewhere else
            # try to return first parsable field
            for v in model_response.values():
                if isinstance(v, str):
                    try:
                        return json.loads(v)
                    except Exception:
                        continue
            raise


def generate_soap_note(
    encounter_json: Dict,
    encounter_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    model: str = "claude",
) -> Dict:
    """
    Generate a clinical SOAP note from transcription + entity JSON.
    
    Args:
        encounter_json: Medical encounter data from transcription
        encounter_id: Optional encounter ID for correlation
        correlation_id: Optional correlation ID for tracking
        model: Model to use for generation ("nova" or "claude")
        
    Returns:
        Dict with SOAP note structure and metadata
    """

    # Optionally route through LangChain if requested
    use_langchain = os.getenv("USE_LANGCHAIN", "0").lower() in ("1", "true", "yes")

    if use_langchain:
        try:
            from src.clinical_notes.soap.langchain_adapter import call_model_via_langchain
        except Exception as exc:
            raise RuntimeError("LangChain adapter not available") from exc

        soap_data = call_model_via_langchain(encounter_json, model)
    else:
        # Use adapter to build the request and parse the response
        adapter = ModelAdapter(model_name=model)

        body = adapter.build_request(encounter_json)

        response = bedrock.invoke_model(
            modelId=adapter.model_id,
            body=json.dumps(body)
        )

        raw_output = response["body"].read()
        soap_data = adapter.parse_response(raw_output)

    # Add metadata if provided
    if encounter_id:
        soap_data["encounter_id"] = encounter_id
    if correlation_id:
        soap_data["correlation_id"] = correlation_id

    return soap_data