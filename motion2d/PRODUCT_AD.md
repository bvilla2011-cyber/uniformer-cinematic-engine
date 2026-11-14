# Super Soccer product advertisement

Use product_ad.py for the current campaign direction. It requires actual gameplay and the official PNG logo. The placeholder U has also been removed from studio.py.

The manual product-ad.yml workflow captures the original Super-Soccer simulation and Canvas renderer at commit 0bf7469a82fd63ae499492407a939bc327b12cdc. It does not alter the game or invent player controls. This is an offline deterministic capture of the real game's rendering and simulation code, not a recording of the browser menus. The capture uses a fixed seed and contrasting away kit.

Install Pillow, numpy, edge-tts, FFmpeg, DejaVu fonts and @napi-rs/canvas. Run:

```sh
node motion2d/capture_game.cjs /path/to/Super-Soccer output/gameframes
ffmpeg -framerate 30 -i output/gameframes/%05d.png -c:v libx264 -crf 18 -pix_fmt yuv420p output/gameplay.mp4
python motion2d/product_ad.py --gameplay output/gameplay.mp4 --logo assets/official_logo.png --output output/ad.mp4
```

The composition uses the game's dark teal, cream and lime palette, animated editorial titles, a genuine gameplay panel, Spanish narration, original synthesized editorial impact/click/whoosh sounds, and an official brand end card. The panels are advertising graphics styled after the game, not screenshots of its menus. Sound accents mark edits, not simulated match events. Speech is normalized and the final mix limited. Edge speech requires a working external connection.

Local validation: full 1080×1920, 30 FPS, approximately 15 seconds, H.264/AAC export completed. Sampled opening, middle and brand frames inspected. This is an improvement of the product presentation, not a claim of AAA production parity.
