"""Vertical MP4 renderer with a deterministic FFmpeg frame stream."""
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from super_soccer_renderer.story import load
from super_soccer_renderer.visuals import Canvas
from super_soccer_renderer.audio import compose

PROFILES = {"smoke": (216, 8, 28), "preview": (360, 16, 22), "final": (1080, 24, 17)}


def render(story_path, output, quality="preview", logo=None, cover=None, limit_frames=None):
    if quality not in PROFILES:
        raise ValueError("Invalid render profile")
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("FFmpeg binary missing")
    story = load(story_path)
    width, fps, crf = PROFILES[quality]
    canvas = Canvas(width)
    count = round(story.duration*fps) if limit_frames is None else max(1,min(int(limit_frames),round(story.duration*fps)))
    output = Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        soundtrack=compose(Path(temp)/"original.wav",story)
        ffmpeg=["ffmpeg","-nostdin","-y","-hide_banner","-loglevel","error",
                "-f","rawvideo","-pix_fmt","rgb24","-s",f"{canvas.w}x{canvas.h}",
                "-r",str(fps),"-i","pipe:0","-i",str(soundtrack),
                "-map","0:v:0","-map","1:a:0","-c:v","libx264",
                "-preset","veryfast" if quality=="final" else "fast", "-crf",str(crf),
                "-pix_fmt","yuv420p","-c:a","aac","-b:a","160k",
                "-movflags","+faststart","-shortest",str(output)]
        process=subprocess.Popen(ffmpeg,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            for i in range(count):
                process.stdin.write(canvas.frame(story,i/fps,logo).tobytes())
            process.stdin.close()
            process.stdin=None
            error=process.stderr.read().decode(errors="replace")
            if process.wait()!=0:
                raise RuntimeError(f"FFmpeg failed: {error[-1200:]}")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    if not output.is_file() or output.stat().st_size<2048:
        raise RuntimeError("Invalid output MP4")
    if cover:
        elapsed=0
        # Choose the point of greatest action instead of using the opening frame.
        goal=next(((elapsed+shot.seconds*.73) for shot in story.shots if shot.kind=="goal"),story.duration*.5)
        canvas.frame(story,goal,logo).save(cover)
    manifest=output.with_suffix(".json")
    manifest.write_text(json.dumps({"title":story.title,"render_profile":quality,
        "dimensions":[canvas.w,canvas.h],"fps":fps,"frames":count,
        "duration_seconds":count/fps,"audio":"original synthesized, not licensed music",
        "official_logo_included":bool(logo and Path(logo).is_file()),
        "rendered_file":output.name},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return output


def main():
    p=argparse.ArgumentParser(description="UniFormer Studio procedural cinematic engine")
    p.add_argument("--story",default="scenes/super_soccer.json")
    p.add_argument("--output",default="output/super_soccer.mp4")
    p.add_argument("--quality",choices=PROFILES,default="preview")
    p.add_argument("--logo",help="Path to official user-provided UniFormer logo PNG")
    p.add_argument("--cover",default="output/super_soccer_cover.png")
    p.add_argument("--limit-frames",type=int,help="For test only, trim render to N frames")
    args=p.parse_args()
    print(render(args.story,args.output,args.quality,args.logo,args.cover,args.limit_frames))

if __name__=="__main__":main()
