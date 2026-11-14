"""Optional OpenAI-compatible storyboard proposal adapter.

This client has no default external endpoint and performs no calls unless run
explicitly with operator-provided URL and secret. It treats all output as data.
"""
import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from super_soccer_renderer.story import validate


def draft(brief, model):
    endpoint=os.getenv("FREELLM_API_BASE","").rstrip("/")
    token=os.getenv("FREELLM_API_KEY","")
    parsed=urlparse(endpoint)
    if not token or (parsed.scheme!="https" and not (parsed.scheme=="http" and parsed.hostname in {"localhost","127.0.0.1"})):
        raise RuntimeError("Provide a reachable HTTPS FREELLM_API_BASE and FREELLM_API_KEY")
    if len(brief)>2000:
        raise ValueError("Creative brief exceeds 2000 characters")
    payload={"model":model,"temperature":.55,"messages":[
        {"role":"system","content":"Return ONLY JSON: {title,brand,shots}. Each shot must be one of tunnel, pitch, goal, brand with seconds 0.3-12 and a short caption. 4-8 original football game shots. No copied intellectual property. No HTML or code."},
        {"role":"user","content":brief},
    ]}
    request=Request(endpoint+"/chat/completions",data=json.dumps(payload).encode(),
        headers={"Content-Type":"application/json","Authorization":"Bearer "+token},method="POST")
    with urlopen(request,timeout=90) as response:
        data=json.load(response)
    raw=data["choices"][0]["message"]["content"].strip()
    if raw.startswith("```"):
        raw="\n".join(raw.splitlines()[1:-1])
    story=validate(json.loads(raw))
    return {"title":story.title,"brand":story.brand,
            "shots":[{"kind":s.kind,"seconds":s.seconds,"caption":s.caption} for s in story.shots]}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--brief",required=True)
    p.add_argument("--model",required=True,help="Model ID exposed by your own server")
    p.add_argument("--output",default="scenes/generated.json")
    args=p.parse_args()
    result=draft(args.brief,args.model)
    output=Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print(f"Validated storyboard written to {output}")

if __name__=="__main__":main()
