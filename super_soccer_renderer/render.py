"""Vertical cinematic renderer with voice-prioritized audio and safe sidecar subtitles."""
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


def _audio_input(path, label):
    if path is None:
        return None
    candidate = Path(path)
    if not candidate.is_file():
        raise FileNotFoundError(f"{label} file not found: {candidate}")
    return candidate


def render(story_path, output, quality="preview", logo=None, cover=None,
           limit_frames=None, voiceover=None, subtitles=None, voice_gain=1.0,
           music_gain=0.30):
    if quality not in PROFILES:
        raise ValueError("Invalid render profile")
    if not 0 <= voice_gain <= 2:
        raise ValueError("Voice gain must be between 0 and 2")
    if not 0 <= music_gain <= 1:
        raise ValueError("Music gain must be between 0 and 1")
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("FFmpeg binary missing")

    voiceover = _audio_input(voiceover, "Voiceover")
    subtitles = _audio_input(subtitles, "Subtitle")
    story = load(story_path)
    width, fps, crf = PROFILES[quality]
    canvas = Canvas(width)
    total_frames = round(story.duration * fps)
    count = total_frames if limit_frames is None else max(1, min(int(limit_frames), total_frames))
    render_duration = count / fps
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    logo_path = Path(logo) if logo else None
    logo_path = logo_path if logo_path and logo_path.is_file() else None

    with tempfile.TemporaryDirectory() as temp:
        soundtrack = compose(Path(temp) / "original.wav", story)
        ffmpeg = [
            "ffmpeg", "-nostdin", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{canvas.w}x{canvas.h}",
            "-r", str(fps), "-i", "pipe:0", "-i", str(soundtrack),
        ]
        if voiceover:
            ffmpeg += ["-i", str(voiceover)]
            duration = f"{render_duration:.3f}"
            ffmpeg += [
                "-filter_complex",
                f"[1:a]aformat=sample_rates=48000:channel_layouts=stereo,"
                f"volume={music_gain:.3f}[music];"
                f"[2:a]aformat=sample_rates=48000:channel_layouts=stereo,"
                f"volume={voice_gain:.3f},apad,atrim=duration={duration},"
                f"asetpts=PTS-STARTPTS[voice];"
                "[music][voice]sidechaincompress=threshold=0.025:ratio=6:"
                "attack=20:release=280[ducked];"
                "[ducked][voice]amix=inputs=2:duration=first:normalize=0,"
                "alimiter=limit=0.95[aout]",
                "-map", "0:v:0", "-map", "[aout]",
            ]
        else:
            ffmpeg += [
                "-filter_complex",
                f"[1:a]aformat=sample_rates=48000:channel_layouts=stereo,"
                f"volume={music_gain:.3f},alimiter=limit=0.95[aout]",
                "-map", "0:v:0", "-map", "[aout]",
            ]
        ffmpeg += [
            "-vf", "eq=contrast=1.05:saturation=1.06:gamma=0.98,vignette=PI/5",
            "-c:v", "libx264", "-preset", "veryfast" if quality == "final" else "fast",
            "-crf", str(crf), "-pix_fmt", "yuv420p", "-c:a", "aac",
            "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
            "-t", f"{render_duration:.3f}", str(output),
        ]
        process = subprocess.Popen(ffmpeg, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            for i in range(count):
                process.stdin.write(canvas.frame(story, i / fps, logo_path).tobytes())
            process.stdin.close()
            process.stdin = None
            error = process.stderr.read().decode(errors="replace")
            if process.wait() != 0:
                raise RuntimeError(f"FFmpeg failed: {error[-1200:]}")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()

    if not output.is_file() or output.stat().st_size < 2048:
        raise RuntimeError("Invalid output MP4")
    if cover:
        elapsed = 0
        goal = next((elapsed + shot.seconds * .73 for shot in story.shots if shot.kind == "goal"),
                    story.duration * .5)
        canvas.frame(story, min(goal, max(0, render_duration - .01)), logo_path).save(cover)

    subtitle_output = None
    if subtitles:
        subtitle_output = output.with_suffix(".srt")
        if subtitles.resolve() != subtitle_output.resolve():
            shutil.copyfile(subtitles, subtitle_output)

    manifest = output.with_suffix(".json")
    manifest.write_text(json.dumps({
        "title": story.title,
        "render_profile": quality,
        "dimensions": [canvas.w, canvas.h],
        "fps": fps,
        "frames": count,
        "duration_seconds": render_duration,
        "audio": {
            "voiceover": voiceover.name if voiceover else None,
            "voice_gain": voice_gain if voiceover else None,
            "music_gain": music_gain,
            "voice_priority_ducking": bool(voiceover),
        },
        "subtitles": subtitle_output.name if subtitle_output else None,
        "official_logo_included": bool(logo_path),
        "rendered_file": output.name,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output


def main():
    p = argparse.ArgumentParser(description="UniFormer Studio procedural cinematic renderer")
    p.add_argument("--story", default="scenes/super_soccer.json")
    p.add_argument("--output", default="output/super_soccer.mp4")
    p.add_argument("--quality", choices=PROFILES, default="preview")
    p.add_argument("--logo", help="Path to official user-provided UniFormer logo PNG")
    p.add_argument("--cover", default="output/super_soccer_cover.png")
    p.add_argument("--voiceover", help="Original narration or dialogue audio file")
    p.add_argument("--voice-gain", type=float, default=1.0)
    p.add_argument("--music-gain", type=float, default=0.30)
    p.add_argument("--subtitles", help="Optional timed SRT subtitle sidecar")
    p.add_argument("--limit-frames", type=int, help="For test only, trim render to N frames")
    args = p.parse_args()
    print(render(
        args.story, args.output, args.quality, args.logo, args.cover, args.limit_frames,
        args.voiceover, args.subtitles, args.voice_gain, args.music_gain,
    ))


if __name__ == "__main__":
    main()
