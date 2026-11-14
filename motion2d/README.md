# UniFormer editorial 2D studio

The active direction is illustrated 2D narrative marketing: detailed rooms, characters with gestures, interface cards, tactical diagrams and readable phrase captions. No Blender or 3D rendering is used. References inform visual grammar only; their videos, voices, scripts and watermarks are not copied into exports.

## Render with integrated Spanish voice

Requires Python 3.11+, Pillow, edge-tts, FFmpeg/ffprobe and DejaVu fonts.

```sh
python -m pip install Pillow edge-tts
python motion2d/studio.py --project motion2d/campaign.json --output output/campaign.mp4
```

Each scene supplies narration. Speech is generated and cached before rendering; scene duration follows the measured speech plus a short pause. Default voice: es-ES-AlvaroNeural. The Edge speech service requires network availability and may change or reject requests. For controlled production, supply a licensed recorded `voice_file` per scene, relative to the JSON file. No secret is required for the Edge provider. Speech failure aborts the normal export with an actionable error.

Output: portrait H.264/AAC, 1080×1920 at 30 FPS, normalized narration, burned phrase captions, and a JSON timing report. Widths 270 and 540 are available for faster previews. Phrase timing is estimated from narration length; it is not word-level forced alignment. Mouth movement is stylized, not phoneme lip-sync.

```sh
python motion2d/studio.py --project motion2d/campaign.json --output output/layout.mp4 --width 540 --silent-preview
```

`--silent-preview` is explicitly for layout review. It does not represent completed audio production.

## Scene contract

A project contains `voice` and 1–60 `scenes`. Every scene has `layout`, `title`, `narration`, and optionally `voice_file`. Layouts are `room`, `cards` (optional `cards` array), `pitch`, and `outro` (optional `cta`). Briefs are JSON data, never executable code. Keep narration below 600 characters per scene. The supplied campaign is an original demonstration.

## Production status

This is a functional replacement direction, not a claim to match the finish of every reference. Current templates have a limited illustrated asset vocabulary. Professional character design, additional scenario packs, music/SFX mixing, precise speech alignment, and final editorial review remain necessary for a finished marketing system. Original 2.5D experiments remain as legacy code; the removed Blender renderer is not used by this pipeline.
