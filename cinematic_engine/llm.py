"""FreeLLMAPI storyboards: accepts JSON data, never runs model-provided code."""
import argparse
import json
import os
from pathlib import Path
from urllib import request
from urllib.parse import urlsplit
from .story import validate

def base_url():
    url=os.environ.get("FREELLM_API_BASE","").rstrip("/")
    u=urlsplit(url)
    if not url or not (u.scheme=="https" or u.scheme=="http" and u.hostname in ("localhost","127.0.0.1")):
        raise RuntimeError("FREELLM_API_BASE must be HTTPS or loopback HTTP, ending in /v1")
    return url

def generate_story(brief,model="auto"):
    key=os.environ.get("FREELLM_API_KEY")
    if not key:
        raise RuntimeError("Set FREELLM_API_KEY in secure Secrets; never commit it")
    instructions=("Return JSON ONLY with title, brand and shots. shots is 4 to 8 entries: "
                  "each has kind (tunnel, pitch, goal or brand), duration (0.3 to 12), "
                  "caption (1-48 characters). Advertising for an original soccer game; "
                  "do not use protected characters, melodies or existing franchises.")
    payload={"model":model,"messages":[{"role":"system","content":instructions},
                                       {"role":"user","content":brief}]}
    req=request.Request(base_url()+"/chat/completions",method="POST",
      headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},
      data=json.dumps(payload).encode("utf8"))
    with request.urlopen(req,timeout=90) as response:
        result=json.load(response)
    raw=result["choices"][0]["message"]["content"].strip()
    if raw.startswith(chr(96)*3):
        raw="\n".join(raw.splitlines()[1:-1]).strip()
    s=validate(json.loads(raw))
    return {"title":s.title,"brand":s.brand,
            "shots":[{"kind":v.kind,"duration":v.duration,"caption":v.caption} for v in s.shots]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--brief",required=True)
    ap.add_argument("--model",default="auto")
    ap.add_argument("--output",default="scenes/ai_story.json")
    args=ap.parse_args()
    data=generate_story(args.brief,args.model)
    target=Path(args.output)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print("Saved validated storyboard:",target)
if __name__=="__main__":main()
