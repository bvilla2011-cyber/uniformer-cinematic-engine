"""Optional FreeLLMAPI experimental remote MP4 endpoint, not HyperFlow H3 inference."""
import argparse
import json
import os
from pathlib import Path
from urllib import request
from .llm import base_url

def generate(prompt,output,duration=5,model="auto"):
    key=os.environ.get("FREELLM_API_KEY")
    if not key: raise RuntimeError("Missing FREELLM_API_KEY")
    if not prompt or len(prompt)>3000 or not 1<=duration<=12: raise ValueError("Bad prompt/duration")
    data=json.dumps({"model":model,"prompt":prompt,"duration":duration,"aspect_ratio":"9:16"}).encode()
    req=request.Request(base_url()+"/videos/generations",method="POST",data=data,
      headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
    path=Path(output)
    path.parent.mkdir(parents=True,exist_ok=True)
    total=0
    try:
        with request.urlopen(req,timeout=330) as resp, path.open("wb") as file:
            kind=resp.headers.get("Content-Type","").lower()
            if "video/" not in kind and "octet-stream" not in kind:raise RuntimeError("Response is not video")
            while True:
                piece=resp.read(1048576)
                if not piece:break
                total+=len(piece)
                if total>150*1048576:raise RuntimeError("Video too large")
                file.write(piece)
        with path.open("rb") as file:
            if b"ftyp" not in file.read(12):raise RuntimeError("Not an MP4")
    except Exception:
        path.unlink(missing_ok=True)
        raise
    print("Created:",path,total,"bytes")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--prompt",required=True)
    ap.add_argument("--output",default="dist/ai_shot.mp4")
    ap.add_argument("--duration",type=int,default=5)
    ap.add_argument("--model",default="auto")
    args=ap.parse_args()
    generate(args.prompt,args.output,args.duration,args.model)
if __name__=="__main__":main()
