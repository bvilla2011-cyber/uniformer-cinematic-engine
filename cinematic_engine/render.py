"""Continuously animate frames and pipe into FFmpeg alongside original audio."""
from pathlib import Path
import argparse
import shutil
import subprocess
import tempfile
from .story import load
from .visuals import Stage
from .sound import compose

PROFILES={"smoke":(216,384,8,27),"preview":(540,960,20,21),"final":(1080,1920,24,18)}

def render(story_file=None,output="dist/super_soccer.mp4",quality="preview",logo=None,poster=None):
    if quality not in PROFILES: raise ValueError("Unknown render profile")
    if shutil.which("ffmpeg") is None: raise RuntimeError("FFmpeg not installed")
    story=load(story_file)
    w,h,fps,crf=PROFILES[quality]
    canvas=Stage(w,h)
    dest=Path(output)
    dest.parent.mkdir(parents=True,exist_ok=True)
    if poster:
        Path(poster).parent.mkdir(parents=True,exist_ok=True)
        canvas.frame(story,story.duration*.45,logo).save(poster)
    with tempfile.TemporaryDirectory() as temp:
        wav=Path(temp)/"sound.wav"
        compose(wav,story.duration)
        cmd=["ffmpeg","-y","-nostdin","-loglevel","error",
             "-f","rawvideo","-pix_fmt","rgb24","-s",f"{w}x{h}","-r",str(fps),"-i","pipe:0",
             "-i",str(wav),"-map","0:v:0","-map","1:a:0",
             "-c:v","libx264","-preset","fast","-crf",str(crf),"-pix_fmt","yuv420p",
             "-c:a","aac","-b:a","160k","-movflags","+faststart","-shortest",str(dest)]
        process=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            for i in range(round(story.duration*fps)):
                process.stdin.write(canvas.frame(story,i/fps,logo).tobytes())
            process.stdin.close()
            process.stdin=None
            err=process.stderr.read().decode(errors="replace")
            if process.wait()!=0: raise RuntimeError("FFmpeg failure: "+err[-1000:])
        finally:
            if process.poll() is None: process.kill();process.wait()
    if dest.stat().st_size<2000: raise RuntimeError("Video output missing")
    print(f"Rendered {dest}: {w}x{h}, {fps} fps, {story.duration}s")
    return dest

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--story")
    p.add_argument("--output",default="dist/super_soccer.mp4")
    p.add_argument("--quality",choices=list(PROFILES),default="preview")
    p.add_argument("--logo")
    p.add_argument("--poster")
    a=p.parse_args()
    render(a.story,a.output,a.quality,a.logo,a.poster)
if __name__=="__main__": main()
