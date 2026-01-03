"""
Test Titan model invocation with a simple Hello World prompt.
"""
import pytest
from src.common.aws import get_bedrock_runtime
import json

def test_titan_hello_world():
    bedrock = get_bedrock_runtime()
    model_id = "arn:aws:bedrock:ap-southeast-2:721285384514:inference-profile/apac.amazon.nova-lite-v1:0"
    request_body = {
        'messages': [
            {
                'role': 'user',
                'content': [{'text': 'Say hello world!'}]
            }
            ],
        'inferenceConfig': {
            'maxTokens': 50,
            'temperature': 0.1
            }
            }
    response = bedrock.invoke_model(
        modelId=model_id,
        body=json.dumps(request_body),
        accept="application/json",
        contentType="application/json"
    )
    result = json.loads(response["body"].read())
    assert "hello" in result["output"]["message"]["content"][0]["text"].lower()
