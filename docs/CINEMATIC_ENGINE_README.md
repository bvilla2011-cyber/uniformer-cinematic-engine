# UniFormer Cinematic Engine

An **original, working experimental** procedural 2.5D animation and soundtrack pipeline for UniFormer Studio. This does **not** replicate Video Rebirth HyperFlow's trained video models, nor promise their level of fidelity.

## Included

- Four continuous animated shots: a stadium tunnel, pitch with players and moving football, goal impact with net and confetti, kinetic brand card.
- Animated skeleton-like actors, independent moving props, glow, parallax, particle effects.
- Original generated score (no third-party music) and captions.
- FFmpeg MP4 H.264/AAC, frame poster and 3 quality profiles.
- Tests + GitHub Actions workflow that renders MP4 artifacts.
- Optional FreeLLMAPI story planning and experimental provider video requests.

## From your phone

Open **Actions > UniFormer Cinematic Engine > Run workflow**. GitHub renders a smoke demo and a 540x960 video (manual run) and provides downloadable artifacts when successful. A push to main runs tests and a tiny smoke MP4. Public repos can use standard GitHub-hosted runners subject to GitHub policy and quotas.

## Run locally

Install Python 3.10+ and FFmpeg:

    pip install -r requirements.txt
    python -m pytest -q
    python -m cinematic_engine --story scenes/super_soccer_teaser.json --quality preview --output dist/teaser.mp4 --poster dist/poster.png
    python -m cinematic_engine --quality final --output dist/final.mp4

Output profiles: smoke 216x384/8fps, preview 540x960/20fps, final 1080x1920/24fps. Final CPU rendering can take substantial time.

To use the true official logo, place an authorized file in assets/brand/logo.png and supply --logo assets/brand/logo.png. Default UF typography is only a placeholder.

## FreeLLMAPI (optional)

You must host or connect a secure, reachable FreeLLMAPI gateway. GitHub runners cannot reach your local iPhone's localhost. Keep all keys in secret storage, never in this repository.

    export FREELLM_API_BASE="https://your-private-server.example/v1"
    export FREELLM_API_KEY="secret-not-in-git"
    python -m cinematic_engine.llm --brief "Original 10 second football teaser" --output scenes/new.json
    python -m cinematic_engine --story scenes/new.json --output dist/new.mp4

Experimental remote MP4 generation:

    python -m cinematic_engine.video_api --prompt "A brand-new cinematic football game trailer" --duration 5

Availability and reuse rights of FreeLLMAPI and the connected model providers must be verified for a commercial campaign. This endpoint is not the separate Video Rebirth HyperFlow H3 model.

## Limitations and roadmap

This is a technical prototype, not finished AAA advertising. It still needs professional character art/rigging, visual QA, speech/lipsync, branded assets, a high-end licensed GPU video provider, consistent-character multimodal shot generation and approval before Metricool publishing. The repo does not auto-post to social media.

See docs/ARCHITECTURE.md for details.

## New: cinematic multi-shot AI director

Plan consistent reference-based prompts without an API key using `python -m cinematic_engine.director --story scenes/super_soccer_teaser.json --output dist/shot-plan.json`. This creates a detailed JSON shot plan and **does not** call providers or use quotas. When a user-configured FreeLLMAPI endpoint is available and its commercial terms permit use, add `--generate` to request one MP4 per shot and automatically assemble them through `cinematic_engine.master`. GPU/model quality depends on the provider; no HyperFlow H3 weights are included. The AI shots are joined with intentional cuts; professional continuity and visual review remain required.
