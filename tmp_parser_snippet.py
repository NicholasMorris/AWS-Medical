# helper snippet for testing parsing logic
from typing import Any

def find_texts(obj: Any):
    if isinstance(obj, dict):
        if 'text' in obj and isinstance(obj['text'], str):
            yield obj['text']
        for v in obj.values():
            yield from find_texts(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from find_texts(item)

# example usage
if __name__ == '__main__':
    import json
    s = json.dumps({"output": {"message": {"content": [{"text": "{\"a\": 1}"}]}}})
    parsed = json.loads(s)
    print(list(find_texts(parsed)))
