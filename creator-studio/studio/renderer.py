"""Real FFmpeg renderer for editable storyboards; no generative video model claims."""
from __future__ import annotations

import math
import os
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZES = {"16:9": (1280, 720), "9:16": (720, 1280), "1:1": (960, 960)}


def font(size: int, bold: bool = True):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def wrapped(draw, text: str, max_width: int, text_font):
    tokens = str(text).split()
    lines, line = [], ""
    for token in tokens:
        candidate = (line + " " + token).strip()
        if draw.textbbox((0, 0), candidate, font=text_font)[2] > max_width and line:
            lines.append(line)
            line = token
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def card(path: Path, w: int, h: int, scene: dict, index: int, transparent: bool):
    if transparent:
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    else:
        img = Image.new("RGB", (w, h))
        pixels = img.load()
        palettes = [((12, 18, 35), (25, 29, 75)), ((16, 13, 35), (47, 22, 75)), ((7, 26, 34), (14, 64, 77)), ((19, 18, 26), (51, 39, 50))]
        a, b = palettes[index % len(palettes)]
        for y in range(h):
            r = y / max(1, h-1)
            for x in range(w):
                gl = .16 * x / max(1, w-1)
                pixels[x, y] = tuple(int(a[k] * (1-r-gl) + b[k] * (r+gl)) for k in range(3))
    draw = ImageDraw.Draw(img, "RGBA")
    pad = int(w*.09)
    if transparent:
        draw.rounded_rectangle((pad//2, int(h*.60), w-pad//2, int(h*.86)), radius=24, fill=(4, 7, 20, 195))
    else:
        draw.ellipse((int(w*.41), int(h*.22), int(w*.97), int(h*.65)), fill=(61, 95, 190, 45), width=5)
        draw.rectangle((pad, int(h*.43), pad+int(w*.1), int(h*.44)), fill=(111, 136, 255, 255))
    title = str(scene.get("title") or "Escena")
    f_title = font(max(24, int(w * (.062 if w > h else .071))))
    f_body = font(max(18, int(w*.026)), False)
    f_label = font(max(14, int(w*.018)))
    width = w - 2*pad
    lines = wrapped(draw, title, width, f_title)[:4]
    y = int(h * (.64 if transparent else .48))
    for line in lines:
        draw.text((pad, y), line, font=f_title, fill=(255, 255, 255, 255), stroke_width=1)
        y += int(w * (.088 if w > h else .102))
    if not transparent:
        desc = str(scene.get("narration") or "")
        for line in wrapped(draw, desc, width, f_body)[:5]:
            draw.text((pad, y+18), line, font=f_body, fill=(188, 202, 226, 255))
            y += int(w*.043)
    draw.text((pad, h-pad), "CREATOR STUDIO  /  " + str(index+1).zfill(2), font=f_label, fill=(137, 166, 235, 255))
    img.save(path)


def call_ffmpeg(args: list[str]):
    try:
        result = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], capture_output=True, text=True, timeout=480)
    except subprocess.TimeoutExpired:
        raise RuntimeError("El render superó el límite de tiempo")
    if result.returncode:
        raise RuntimeError("FFmpeg: " + (result.stderr.strip() or "error desconocido")[-600:])


def render_project(project: dict, assets: dict, target: Path, progress=None):
    scenes = project.get("scenes") or []
    if not scenes:
        raise ValueError("No hay escenas para exportar")
    if len(scenes) > 80:
        raise ValueError("Máximo 80 escenas por render")
    w, h = SIZES.get(project.get("aspect", "9:16"), (720, 1280))
    output = Path(target)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="creator_render_") as temp:
        temp = Path(temp)
        segments = []
        for i, scene in enumerate(scenes):
            duration = float(scene.get("duration", 5))
            if not 1 <= duration <= 120 or not math.isfinite(duration):
                raise ValueError("Duración de escena inválida")
            visual = assets.get(scene.get("asset_id"))
            voice = assets.get(scene.get("voice_asset_id"))
            visual_file = temp / f"visual_{i:03d}.png"
            card(visual_file, w, h, scene, i, transparent=bool(visual))
            args = []
            if visual:
                if visual["kind"] == "video":
                    args += ["-stream_loop", "-1", "-i", visual["path"]]
                elif visual["kind"] == "image":
                    args += ["-loop", "1", "-framerate", "24", "-i", visual["path"]]
                else:
                    raise ValueError("Recurso visual no válido")
                args += ["-loop", "1", "-framerate", "24", "-i", str(visual_file)]
                video_filter = (f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
                                f"crop={w}:{h},setsar=1,format=yuv420p[bg];[bg][1:v]overlay=0:0:shortest=1[v]")
            else:
                args += ["-loop", "1", "-framerate", "24", "-i", str(visual_file)]
                video_filter = f"[0:v]format=yuv420p[v]"
            if voice:
                args += ["-i", voice["path"]]
                audio_idx = 2 if visual else 1
                args += ["-filter_complex", video_filter, "-map", "[v]", "-map", f"{audio_idx}:a:0", "-af", f"apad,atrim=0:{duration}"]
            else:
                args += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
                audio_idx = 2 if visual else 1
                args += ["-filter_complex", video_filter, "-map", "[v]", "-map", f"{audio_idx}:a:0"]
            clip = temp / f"shot_{i:03d}.mp4"
            args += ["-t", str(duration), "-r", "24", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-movflags", "+faststart", str(clip)]
            call_ffmpeg(args)
            segments.append(clip)
            if progress:
                progress((i+1)/len(scenes)*90, f"Renderizando escena {i+1}/{len(scenes)}")
        playlist = temp / "concat.txt"
        playlist.write_text("\n".join("file '" + p.name + "'" for p in segments), encoding="utf8")
        # All segments already share codec, dimensions, FPS and audio configuration.
        call_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(playlist), "-c", "copy", "-movflags", "+faststart", str(output)])
        if progress:
            progress(99, "Verificando exportación")
    if not output.exists() or output.stat().st_size < 1024:
        raise RuntimeError("El MP4 final no se generó")
    return output
