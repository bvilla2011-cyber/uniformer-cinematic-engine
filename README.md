# UniFormer Cinematic Engine

The active campaign renderer is now **editorial 2D animation with integrated Spanish narration**. The rejected Blender 3D renderer and workflow have been removed from this branch.

See [the 2D studio guide](motion2d/README.md) and [original example project](motion2d/campaign.json).

```sh
python -m pip install Pillow edge-tts
python motion2d/studio.py --project motion2d/campaign.json --output output/campaign.mp4
```

Requires FFmpeg and DejaVu fonts. The renderer generates speech first, measures its duration, animates four illustrated scene types, burns phrase captions and exports H.264/AAC plus a timing report. Recorded voice files are supported. Remote speech failure stops the production export; silent previews require an explicit flag.

The manual workflow is `.github/workflows/editorial-2d.yml`. It becomes available in Actions once integrated into the default branch.

This is a functional new direction, not yet a finished production system matching all reference videos. Caption timings are approximate; character animation is stylized. More authored assets, precise speech alignment, sound design and editorial polish remain to be implemented.

The older `engine/` procedural experiments remain available as legacy code. No social posts are automatically published.
