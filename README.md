# UniFormer Cinematic Engine

**Experimental procedural animation studio** for UniFormer Studio. Produces original 2.5D short-form promotional clips from a structured JSON brief. This is a **working technical prototype**, not yet an AAA-quality cinematic tool or a replacement for professional animators.

## What works now

- Three original animated environments: rooftop character, geometric forge, floating city reveal.
- Independently animated layers, articulated arm, particles, camera-like parallax, light effects and shot transitions.
- Original synthesized soundtrack and effects, optional external voiceover.
- Optional time-coded captions in project JSON and an official PNG logo overlay via `--logo assets/official_logo.png`.
- Vertical H.264/AAC MP4 output at **540×960 or 1080×1920**, 24 FPS by default.
- Extracted **cover frame**, **storyboard**, render report and Metricool-ready **draft metadata**.
- Automated unit tests and visual/audio quality checks.
- GitHub Actions workflow producing a downloadable production package.
- Optional **OpenAI-compatible** text-model creative brief adapter. FreeLLMAPI compatibility and credentials **not yet verified**; no automatic posting.

## Render on GitHub (iPhone-friendly)

1. Open [GitHub Actions](https://github.com/bvilla2011-cyber/uniformer-cinematic-engine/actions/workflows/render.yml).
2. Tap **Run workflow** and choose 1080 for full-HD vertical output.
3. Wait for the workflow to complete successfully.
4. Open the run and download the **uniformer-first-light-production** artifact ZIP.

The workflow also runs automatically when engine, project or test files change.

## Local development

Requires Python 3.11+ and FFmpeg (including ffprobe).

\`\`\`bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m engine.studio --project projects/first_light.json --width 1080 --output output/first_light.mp4
python -m engine.qa output/first_light.mp4 --min-width 1080
python -m engine.social --project projects/first_light.json --video output/first_light.mp4
\`\`\`

For a fast smoke test use \`--width 270 --preview\`.

## AI-assisted brief generation (optional)

\`engine/brief.py\` can call an **OpenAI-compatible chat-completions endpoint**. This is an adapter, not a verified FreeLLMAPI integration. Configure **FREELLMAPI_CHAT_URL**, **FREELLMAPI_MODEL**, and optionally **FREELLMAPI_API_KEY** as private environment variables; never commit credentials.

\`\`\`bash
python -m engine.brief --idea "An original 10-second UniFormer teaser" --output projects/generated.json
python -m engine.studio --project projects/generated.json --output output/generated.mp4
\`\`\`

AI output is **strictly validated as data**. It is never executed as Python. Only three predefined scene types are supported at present.

## Mobile AI-to-video workflow (optional, not yet connected)

A second workflow is available: [AI creative brief → video](https://github.com/bvilla2011-cyber/uniformer-cinematic-engine/actions/workflows/ai-creative-render.yml).

Before running it, configure the following **Actions repository secrets** in GitHub **Settings → Secrets and variables → Actions**:

- \`FREELLMAPI_CHAT_URL\`: full HTTPS URL of a working OpenAI-compatible chat-completions endpoint (not just a domain).
- \`FREELLMAPI_MODEL\`: exact supported model identifier.
- \`FREELLMAPI_API_KEY\`: provider key if required.

These secrets are **not configured by this repository** and the FreeLLMAPI service contract is **not verified**. The workflow will fail with an explanatory error until configured. Once compatible, you can enter an original creative idea from your phone, validate the model's JSON output, render the approved procedural scene templates and download a ZIP. It does **not** generate photorealistic diffusion videos, create new scene types, or schedule Metricool posts automatically.

## Important limits

- Procedural 2.5D is not photorealistic 3D or generative video.
- No actual FreeLLMAPI account or API key has been connected.
- No Metricool post has been scheduled. The social JSON is a **draft**.
- Rendering uses GitHub Actions minutes and artifact storage subject to GitHub limits.
- The official logo image has not been added to this repository; the overlay only activates when an authorized PNG is provided. Use only authorized brand assets.
- Review every final clip for quality, rights, text legibility and platform compliance.

See [architecture](docs/ARCHITECTURE.md).
