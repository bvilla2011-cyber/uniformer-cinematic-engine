# Blender 3D teaser renderer

This renderer adds a complete, original 18-second low-poly football teaser beside the existing 2.5D scene engine. It uses Blender 4.x Eevee, keyframed character rigs, a procedural stadium, a tracked camera, a custom synthesized score, AgX color, motion blur and a portrait end card. Its color system follows Super Soccer's navy, blue, purple, cyan, yellow, coral and paper-white UI.

## Render locally

Install Blender 4.x and FFmpeg, then run from the repository root:

```bash
blender -b --python renderers/blender_super_soccer.py -- --preview --output output/super_soccer_preview.mp4
blender -b --python renderers/blender_super_soccer.py -- --output output/super_soccer_1080.mp4
```

The preview is 360×640 at 12 FPS. The production render is 1080×1920 at 24 FPS, with 8 Eevee samples and motion blur. Both are 18 seconds, portrait 9:16, H.264/AAC, and include the original score.

The authorized UniFormer logo is included at `assets/official_logo.png` and appears by default. Override it with another logo PNG when needed. Add a recorded voiceover WAV and timed SRT captions with:

```bash
blender -b --python renderers/blender_super_soccer.py -- \
  --output output/super_soccer.mp4 \
  --logo assets/official_logo.png \
  --voiceover assets/voiceover.wav \
  --subtitles projects/super_soccer_launch.srt
```

Voice is mixed above the score with automatic music ducking. The renderer does not synthesize a voice; record the original narration below or supply an authorized voice recording. The official logo is used by default and remains replaceable. Captions are burned into the MP4 and also copied as a separate SRT sidecar.

## Original narration

> Cuando se apagan las luces, empieza el partido. Un equipo. Un estadio. Un sueño: un pase puede cambiarlo todo. Corre, combina, busca el espacio. Y cuando llega el momento… decide. Super Soccer. El estadio despierta. Ya puedes entrar en beta.

The matching SRT is `projects/super_soccer_launch.srt`. The script and captions are original to this project.

## GitHub Actions

Run **Actions → Blender Super Soccer teaser → Run workflow**. Choose preview or production quality. The MP4 and SRT are published as a downloadable artifact. Production quality requires a longer Actions runner time and storage than preview quality.

This is a deterministic, stylized low-poly renderer, not a photorealistic video generator. Review the exported clip and attach licensed brand, voice and music assets before publishing a campaign.
