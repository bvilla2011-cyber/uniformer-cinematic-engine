# UniFormer Cinematic Engine

Production toolkit for original, procedural 2.5D promotional clips for UniFormer Studio.

**Status:** experimental animation prototype. Not an AAA renderer; the first milestone is a reproducible short MP4 with independently animated scene elements, camera movement, original synthesized audio, and a GitHub Actions render workflow.

The engine never executes Python written by a language model. Text models can propose structured creative briefs; the renderer uses trusted, version-controlled animation code.

See the documentation and GitHub Actions workflow added in the next commit.

## Enhanced multi-shot cinematic pipeline

A separate experimental module has been added in **cinematic_engine/** with four animated football scenes, original sound, safe JSON storyboards, and optional FreeLLMAPI API adapters. See [cinematic engine guide](docs/CINEMATIC_ENGINE_README.md). Its dedicated workflow is **UniFormer Cinematic Engine**. The existing engine/render.py and its workflow remain available.
