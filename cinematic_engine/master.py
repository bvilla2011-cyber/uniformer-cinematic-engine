"""Normalize and assemble externally generated MP4 shots with an original score."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from .sound import compose

SIZES={"preview":(540,960),"final":(1080,1920)}

def run_command(args):
    result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,text=True)
    if result.returncode:
        raise RuntimeError("FFmpeg/FFprobe failed: "+result.stderr[-1200:])
    return result.stdout

def duration_of(path):
    output=run_command(["ffprobe","-v","error","-show_entries","format=duration",
                       "-of","json",str(path)])
    duration=float(json.loads(output)["format"]["duration"])
    if not .2<duration<601:
        raise ValueError("Unexpected duration")
    return duration

def combine(paths,output,quality="preview"):
    if quality not in SIZES:raise ValueError("Invalid output quality")
    if not isinstance(paths,(list,tuple)) or not 1<=len(paths)<=24:
        raise ValueError("Need 1-24 source clips")
    sources=[Path(p).resolve() for p in paths]
    for source in sources:
        if not source.is_file():raise FileNotFoundError(source)
    output=Path(output).resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    w,h=SIZES[quality]
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp)
        normalized=[]
        total=0.0
        for i,src in enumerate(sources):
            clip=root/f"clip_{i:03d}.mp4"
            scale=f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps=24,format=yuv420p"
            run_command(["ffmpeg","-y","-loglevel","error","-i",str(src),"-vf",scale,"-an",
                         "-c:v","libx264","-preset","fast","-crf","20",
                         "-movflags","+faststart",str(clip)])
            total+=duration_of(clip)
            normalized.append(clip)
        concat=root/"concat.txt"
        concat.write_text("".join("file '"+str(p)+"'\n" for p in normalized),encoding="utf8")
        soundtrack=root/"original.wav"
        compose(soundtrack,total)
        run_command(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",str(concat),
                     "-i",str(soundtrack),"-map","0:v:0","-map","1:a:0","-c:v","copy",
                     "-c:a","aac","-b:a","160k","-shortest","-movflags","+faststart",str(output)])
    if output.stat().st_size<4096:raise RuntimeError("Master output missing")
    print(f"Master ready: {output} ({len(sources)} shots)")
    return output

def main():
    p=argparse.ArgumentParser()
    p.add_argument("clips",nargs="+")
    p.add_argument("--output",default="dist/ai_master.mp4")
    p.add_argument("--quality",choices=list(SIZES),default="preview")
    a=p.parse_args()
    combine(a.clips,a.output,a.quality)
if __name__=="__main__":
    main()
