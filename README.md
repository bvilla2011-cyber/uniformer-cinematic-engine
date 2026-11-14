# UniFormer Cinematic Engine

Procedural 2.5D animation tools for original UniFormer Studio campaign clips. The repository contains three production paths: the general scene studio under `engine/`, the football teaser renderer under `super_soccer_renderer/`, and a HyperFrames composition under `hyperframes/`.

## HyperFrames cinematic composition

`hyperframes/super_soccer.html` is an authored 18-second vertical teaser built for HyperFrames: finite, seekable GSAP motion; low-poly-inspired stadium geometry; layered floodlights; articulated player silhouettes; camera pushes; a goal sequence; and a branded end card. It is a separate composition and does not remove the existing Python renderer.

Render it from the repository root with the [HyperFrames CLI](https://github.com/heygen-com/hyperframes):

```bash
npx hyperframes render --composition hyperframes/super_soccer.html --quality high --fps 30 --output output/super_soccer_hyperframes.mp4
```

The composition loads GSAP from jsDelivr, so rendering it requires network access. Its timeline uses authored deterministic keyframes rather than live wall-clock motion.

After this branch is merged into `main`, open [the HyperFrames workflow](https://github.com/bvilla2011-cyber/uniformer-cinematic-engine/actions/workflows/hyperframes.yml), choose **Run workflow**, select **high**, and download the resulting MP4 artifact when the run completes.

## Super Soccer teaser renderer

This path creates a vertical, original low-poly-inspired football sequence: tunnel, stadium action, goal, and UniFormer/SUPER SOCCER closing frame. It renders H.264/AAC MP4 at 216p, 360p, or 1080p, with a cover frame and JSON render manifest.

The renderer supports an optional original voiceover and timed SRT sidecar. The narration remains at its chosen gain; the soundtrack defaults to 30% and is ducked automatically while speech is present. A restrained contrast, saturation, gamma, and vignette grade is applied to the final video. The logo is optional and must be an authorized transparent PNG.

### Render with voice and captions

```bash
python -m pip install -r requirements-cinematic.txt
python -m super_soccer_renderer.render \
  --story scenes/super_soccer.json \
  --quality final \
  --voiceover assets/narration.wav \
  --subtitles assets/narration.srt \
  --logo assets/uniformer-logo.png \
  --output output/super_soccer.mp4
```

The MP4 is accompanied by `output/super_soccer.json`, the selected cover frame, and—when supplied—`output/super_soccer.srt`. Use `--voice-gain` and `--music-gain` to adjust the mix. Voice gain accepts 0–2; music gain accepts 0–1.

### Render on GitHub

Open [the Super Soccer render workflow](https://github.com/bvilla2011-cyber/uniformer-cinematic-engine/actions/workflows/super_soccer.yml), run it, and select a quality profile. The workflow produces a downloadable artifact. It does not receive a private narration or logo automatically; those files must be supplied to a local render or added through an approved private asset workflow.

## General scene studio

The separate `engine/` renderer supports rooftop, geometric forge, and floating city scenes from JSON briefs. Its usage and AI-assisted brief adapter are documented in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). FreeLLMAPI compatibility and credentials have not been verified, and no social posts are scheduled automatically.

## Development

Requires Python 3.11+ and FFmpeg. Dependencies are listed in `requirements-cinematic.txt` for the Super Soccer renderer and `requirements.txt` for the general studio.

```bash
python -m pytest -q
python -m super_soccer_renderer.render --quality smoke --output output/preview.mp4
```

## Current production boundary

The footage is deterministic, hand-authored procedural 2.5D built from vector shapes and animated layers. It is not a full 3D character animation pipeline or generative video, and it cannot guarantee a specific commercial/AAA result by itself. For a campaign deliverable, inspect the actual render, keep narration timing aligned to the storyboard, and provide authorized logo/audio assets. The new voice mix, color grade, cover frame and SRT sidecar are production controls; they do not replace final human review.
