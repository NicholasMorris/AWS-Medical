import boto3
from functools import lru_cache
from typing import Optional, Dict, Any
import json

DEFAULT_REGION = "ap-southeast-2"


@lru_cache
def get_bedrock_runtime(region_name: Optional[str] = None):
    """
    Returns a cached Bedrock Runtime client.
    """
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=region_name or DEFAULT_REGION,
    )


@lru_cache
def get_transcribe_client(region_name: Optional[str] = None):
    """
    Returns a cached AWS Transcribe client.
    """
    return boto3.client(
        service_name="transcribe",
        region_name=region_name or DEFAULT_REGION,
    )


@lru_cache
def get_comprehend_medical_client(region_name: Optional[str] = None):
    """
    Returns a cached AWS Comprehend Medical client.
    """
    return boto3.client(
        service_name="comprehendmedical",
        region_name=region_name or DEFAULT_REGION,
    )

@lru_cache
def get_s3_client(region_name: Optional[str] = None):
    """
    Returns a cached AWS S3 client.
    """
    return boto3.client(
        service_name="s3",
        region_name=region_name or DEFAULT_REGION,
    )


def build_nova_request(
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 512,
    system_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a Nova Invoke API request body with messages + inferenceConfig.

    Args:
        user_prompt: The user message text
        temperature: Model temperature (0.0–1.0; default 0.2 for conservative output)
        max_tokens: Maximum tokens in response
        system_prompt: Optional system prompt for context/instructions

    Returns:
        Dict ready to be JSON-serialized and passed to bedrock.invoke_model(body=...)
    """
    messages = [{"role": "user", "content": [{"text": user_prompt}]}]
    
    body = {
        "messages": messages,
        "inferenceConfig": {"temperature": temperature, "maxTokens": max_tokens},
    }

    if system_prompt:
        body["system"] = [{"text": system_prompt}]

    return body


def parse_nova_response(response_bytes: bytes) -> Dict[str, Any]:
    """
    Parse a Nova Invoke API response, extracting the first JSON object or plain text.

    Handles:
    - New Nova response shape: output.message.content[].text
    - Legacy shape: content[].text
    - Markdown code blocks (```json ... ```)
    - If no JSON found, returns the first text block as-is (useful for plain text responses)
    - Recursive search for parseable JSON in any text field

    Args:
        response_bytes: Raw bytes from bedrock.invoke_model() response body

    Returns:
        Parsed JSON dict if JSON found; otherwise, dict with "text" key containing plain text

    Raises:
        ValueError: If no text blocks found at all
    """
    raw = response_bytes.decode("utf-8")
    try:
        model_response = json.loads(raw)
    except Exception:
        # If response is plain JSON text, try to parse directly
        try:
            return json.loads(raw)
        except Exception:
            raise

    def _find_texts(obj):
        """Yield all `text` string values found recursively in `obj`."""
        if isinstance(obj, dict):
            if "text" in obj and isinstance(obj["text"], str):
                yield obj["text"]
            for v in obj.values():
                yield from _find_texts(v)
        elif isinstance(obj, list):
            for item in obj:
                yield from _find_texts(item)

    def _try_parse_json(text: str):
        """Attempt to parse JSON from text, stripping markdown code blocks if present."""
        if not isinstance(text, str):
            return None
        # Strip markdown code block markers (```json ... ```)
        cleaned = text.strip()
        if cleaned.startswith("```"):
            # Find the opening marker and extract content after it
            lines = cleaned.split("\n", 1)
            if len(lines) > 1:
                # Remove the closing ``` if present
                content = lines[1]
                if content.endswith("```"):
                    content = content[:-3]
                cleaned = content.strip()
        try:
            return json.loads(cleaned)
        except Exception:
            return None

    # 1) Nova shape: output.message.content -> list of blocks
    content_list = model_response.get("output", {}).get("message", {}).get("content", [])
    first_text = None
    for item in content_list:
        if isinstance(item, dict) and "text" in item and isinstance(item["text"], str):
            if first_text is None:
                first_text = item["text"]
            result = _try_parse_json(item["text"])
            if result is not None:
                return result

    # 2) Legacy shape: content[0].text
    try:
        soap_json = model_response["content"][0]["text"]
        if first_text is None:
            first_text = soap_json
        result = _try_parse_json(soap_json)
        if result is not None:
            return result
    except Exception:
        pass

    # 3) Recursive search for any text blocks that parse as JSON
    for txt in _find_texts(model_response):
        if first_text is None:
            first_text = txt
        result = _try_parse_json(txt)
        if result is not None:
            return result

    # If we found text but it wasn't JSON, return it as a plain text dict
    if first_text is not None:
        return {"text": first_text}

    # If we reach here, we could not locate any text in the response.
    preview = raw[:1000] + ("..." if len(raw) > 1000 else "")
    raise ValueError(f"Unable to extract text from model response. Raw response preview: {preview}")

