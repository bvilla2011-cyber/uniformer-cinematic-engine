# Technical overview and honesty about capabilities

Current: validated JSON storyboard -> Python 2.5D motion scenes -> original synthesized sound -> FFmpeg encode -> GitHub Actions downloadable artifacts.

External AI is opt-in and *not* essential for the demo. FreeLLMAPI uses a user-configured OpenAI-compatible /v1/chat/completions for story data and /v1/videos/generations for provider MP4. The latter is a separate service and is **not** the Video Rebirth HyperFlow H3 diffusion model.

Missing: high-fidelity AI video inference / GPU infrastructure, persistent multi-shot character identity model, professional rigged art, synced audio/narration, consistent visual QA loop and automatic Metricool scheduling with public uploaded video URLs.

Security: never commit credentials; run FreeLLMAPI behind TLS and authenticated gateway; outputs from a model are validated JSON only, no arbitrary code execution. Confirm rights and commercial permissions with the model/provider before using content in marketing. Keep official brand logo out of the public repository if you don't want it publicly distributed.
