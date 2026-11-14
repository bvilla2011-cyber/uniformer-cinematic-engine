# Production architecture

## Implemented first milestone
- Pure Python procedural 2.5D renderer using Pillow and NumPy
- Independent particle, camera, planet, spacecraft, and floor animations
- Original synthesized ambient score and beat
- FFmpeg H.264/AAC vertical MP4 encoding
- GitHub Actions build with downloadable artifact

## Planned, not yet implemented
- Configurable shot graphs, articulated characters and asset packs
- Voiceover and word-timed captions
- Model-provider abstraction for FreeLLMAPI, with secrets stored outside Git
- Automated visual QA and iterative scene refinement
- Media storage and Metricool scheduling (subject to account/API constraints)

## Security
Do not commit API keys. Never execute arbitrary model-generated Python in Actions.
Review all external model output as untrusted input.

## Local test
```bash
sudo apt-get install ffmpeg
pip install -r requirements.txt
python engine/render.py --output output/uniformer_teaser.mp4
```
