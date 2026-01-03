"""Optional LangChain adapter for Bedrock-backed LLM calls.

This module is intentionally lightweight and optional. If `langchain`
is not installed, importing or calling `call_model_via_langchain` will
raise a RuntimeError instructing the user to install LangChain.

The function returns a dict (parsed JSON) representing the SOAP note.
"""
from typing import Dict
import json
import os

from src.common.models import MODEL_MAP, get_default_model


def call_model_via_langchain(encounter_json: Dict, model_name: str = "claude") -> Dict:
    """Call Bedrock via LangChain's Bedrock LLM wrapper and return parsed JSON.

    This requires `langchain` to be installed. It will instantiate the
    `langchain.llms.Bedrock` LLM with `model_id` and `region_name` where
    available, then call it with the same prompt used elsewhere and parse
    the returned text as JSON.
    """
    try:
        from langchain.llms import Bedrock  # type: ignore
    except Exception as exc:
        raise RuntimeError("LangChain is not installed. Install 'langchain' to use this adapter.") from exc

    model_name = model_name or get_default_model()
    model_id = MODEL_MAP.get(model_name, MODEL_MAP["claude"])
    region = os.getenv("AWS_REGION", "ap-southeast-2")

    # Build the prompt similar to generator's user_prompt
    user_prompt = f"""
Encounter data (JSON):
{json.dumps(encounter_json, indent=2)}

Generate a SOAP note with keys: subjective, objective, assessment, plan. Return JSON only.
"""

    # Instantiate LangChain Bedrock LLM
    llm = Bedrock(model_id=model_id, region_name=region)

    text = llm(user_prompt)

    try:
        return json.loads(text)
    except Exception:
        # If model returns wrapped JSON, try to extract JSON substring
        # fallback to raise so tests can mock this function
        raise RuntimeError("LangChain model did not return valid JSON")

