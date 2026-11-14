# Cinematic Engine architecture

Pipeline: original scene JSON -> schema validator -> Python 2.5D renderer (Pillow + NumPy) -> WAV original synth -> FFmpeg H.264/AAC -> MP4 + screenshot + JSON manifest -> GitHub Actions artifact.

The project does not execute LLM-written code and does not rely on unverified video APIs. Optional model-assisted scene *planning* passes through an explicit, validated JSON protocol (`engine/llm.py`).

## Production gates before posting

1. Verify every render ends successfully and includes both video and sound.
2. Check character anatomy, leg joints, keeper/ball contact and shot transitions.
3. Compare the original approved logo and its usage in the end card.
4. Check captions for spelling, clipping and mobile safe areas.
5. Check licenses and commercial terms for anything supplied by third parties.
6. Review cover PNG; publish only after visual QA.

## Roadmap (not implemented)

- Character/rig assets authored by professional artists, cloth, depth, camera dolly and optical effects.
- Timed voiceover and subtitles aligned to real spoken words.
- GPU-based video model connector with continuity and content-review gates.
- Hosted previews, permanent HTTPS links for upload, Metricool scheduling and engagement feedback loops.
- Original camera choreography shot by shot, audio mixing and brand compliance.

Standard GitHub Actions runners have limited CPU and no general-purpose video-generation GPU. A GPU platform / licensed video service is needed for HyperFlow-class generative video inference.
