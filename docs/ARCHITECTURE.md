# Architecture and development milestones

## Current pipeline (implemented)

\`\`\`text
projects/first_light.json
       ↓ validate_project (safe shot registry)
engine/studio.py (deterministic scene graph + original audio)
       ↓ FFmpeg video encoding
output/first_light.mp4
       ├── _cover.png (real frame from the video)
       ├── _storyboard.jpg (one frame per shot)
       ├── _report.json (render facts)
       ├── _qa.json (stream and frame checks)
       └── _social.json (draft; NOT published)
\`\`\`

\`engine/qa.py\` verifies video/audio presence, 9:16 dimensions, duration and luminance at multiple timestamps. These are **technical checks**, not a guarantee of visual excellence.

## AI adapter

\`engine/brief.py\` accepts only HTTPS chat-completions endpoints, uses a model selected via environment variables, checks output size and parses a JSON response. Scene types and shot durations are validated before render. It does not execute arbitrary AI-generated code. Actual FreeLLMAPI compatibility has not been tested.

## Delivery

GitHub Actions renders the clip, runs unit tests and QA, then publishes a ZIP artifact for review. The Metricool metadata is a draft: the connected Metricool tool can be used separately once the final content is approved and account limitations are checked.

## Milestones

1. **Done:** Render an original animated 10-second short at 1080×1920 locally with audio and three shots.
2. **Done:** Implement scene JSON, storyboard, cover, reports, basic QA, unit tests and CI workflow.
3. **Next:** More expressive rigged characters, lip-sync, motion curves, richer backgrounds, voiceover and real logo support.
4. **Next:** Validate FreeLLMAPI's actual API contract, connect a secure provider configuration and add creative review loop.
5. **Later:** Mobile-friendly dashboard, asset storage, job queue, render workers, analytics-informed creative variants and approved Metricool scheduling.

## Engineering guardrails

- No secrets in Git.
- No automatic publishing of unreviewed assets.
- No arbitrary execution of language-model output.
- Audio is synthesized originally; no third-party copyrighted soundtrack is included.
- Version and test each scene template before using it in production.
