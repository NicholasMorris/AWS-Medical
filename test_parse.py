#!/usr/bin/env python3
"""Quick test of parse_nova_response function."""
import json
from src.common.aws import parse_nova_response

# Test 1: Plain text
print("Test 1: Plain text...")
resp1 = json.dumps({'output': {'message': {'content': [{'text': 'plain text'}]}}}).encode()
result1 = parse_nova_response(resp1)
print(f"  Result: {result1}")
assert result1 == {"text": "plain text"}, f"Expected {{'text': 'plain text'}}, got {result1}"

# Test 2: JSON with markdown
print("Test 2: JSON with markdown...")
resp2 = json.dumps({'output': {'message': {'content': [{'text': '```json\n{"key": "value"}\n```'}]}}}).encode()
result2 = parse_nova_response(resp2)
print(f"  Result: {result2}")
assert result2 == {"key": "value"}, f"Expected {{'key': 'value'}}, got {result2}"

# Test 3: JSON without markdown
print("Test 3: JSON without markdown...")
resp3 = json.dumps({'output': {'message': {'content': [{'text': '{"a": 1}'}]}}}).encode()
result3 = parse_nova_response(resp3)
print(f"  Result: {result3}")
assert result3 == {"a": 1}, f"Expected {{'a': 1}}, got {result3}"

print("All tests passed!")
