"""Optional text-model creative brief generator using an OpenAI-compatible API.

FreeLLMAPI compatibility depends on its configured backend; no API calls are
made without an explicit endpoint and model. Never execute model-written code.
"""
import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from engine.studio import validate_project

SYSTEM = (
    "You are a creative director for original cinematic game studio promos. "
    "Return ONLY a JSON object with title, shots and social. "
    "Each shot has type (rooftop, forge or reveal), duration (0.5 to 15), "
    "headline (max 70 chars) and subtitle (max 70 chars). "
    "Total duration must not exceed 60 seconds; maximum 12 shots. "
    "Use original phrases, no copyrighted characters or music. "
    "The renderer is procedural and supports only those three scene types."
)


def parse_response(raw):
    if not isinstance(raw, str) or len(raw) > 20000:
        raise ValueError("Invalid or oversized model response")
    raw = raw.strip()
    if raw.startswith('```'):
        raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
    data = json.loads(raw)
    validate_project(data)
    return data


def generate(idea, endpoint=None, model=None, api_key=None):
    endpoint = endpoint or os.getenv('FREELLMAPI_CHAT_URL')
    model = model or os.getenv('FREELLMAPI_MODEL')
    api_key = api_key or os.getenv('FREELLMAPI_API_KEY')
    if not endpoint or not model:
        raise ValueError('Set FREELLMAPI_CHAT_URL and FREELLMAPI_MODEL first')
    parsed = urlparse(endpoint)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError('Endpoint must be a valid HTTPS URL without embedded credentials')
    if len(idea) > 1500:
        raise ValueError('Idea too long')
    body = json.dumps({'model': model, 'messages': [
        {'role': 'system', 'content': SYSTEM},
        {'role': 'user', 'content': idea}], 'temperature': 0.7}).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = 'Bearer ' + api_key
    request = Request(endpoint, data=body, headers=headers, method='POST')
    with urlopen(request, timeout=45) as response:
        payload = response.read(500_001)
        if len(payload) > 500_000:
            raise ValueError('Model response exceeds size limit')
    result = json.loads(payload)
    return parse_response(result['choices'][0]['message']['content'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--idea', required=True)
    parser.add_argument('--output', default='projects/generated.json')
    args = parser.parse_args()
    data = generate(args.idea)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Validated brief saved:', out)


if __name__ == '__main__':
    main()
