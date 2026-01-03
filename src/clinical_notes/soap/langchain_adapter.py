"""Optional LangChain adapter for Bedrock-backed LLM calls.

This module provides a fallback that calls Bedrock directly (using the same
request/response format as the project's `ModelAdapter`). This avoids LangChain
format mismatches (e.g. missing `messages`) while keeping the `USE_LANGCHAIN`
switchable path intact.
"""
from typing import Dict
import json
import os

from src.common.models import MODEL_MAP, get_default_model
from src.common.aws import get_bedrock_runtime
from src.clinical_notes.soap.generator import ModelAdapter


def call_model_via_langchain(encounter_json: Dict, model_name: str = "nova") -> Dict:
    """
    Call Bedrock directly and return parsed JSON.

    This function preserves the same request/response shape used by the
    non-LangChain path by delegating build/parse to `ModelAdapter`. It is
    intentionally lightweight and avoids constructing LangChain-specific
    payloads that can lead to Bedrock validation errors.
    """
    model_name = model_name or get_default_model()
    adapter = ModelAdapter(model_name=model_name)

    region = os.getenv("AWS_REGION", "ap-southeast-2")
    bedrock = get_bedrock_runtime(region)

    body = adapter.build_request(encounter_json)

    response = bedrock.invoke_model(
        modelId=adapter.model_id,
        body=json.dumps(body),
    )

    raw_output = response["body"].read()
    return adapter.parse_response(raw_output)

