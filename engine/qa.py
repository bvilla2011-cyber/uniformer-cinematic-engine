"""Post-render quality gates for video and social assets."""
import argparse
import json
import subprocess
from pathlib import Path
from PIL import Image, ImageStat
import io

from engine.studio import ffprobe


def check(video, minimum_width=540):
    video = Path(video)
    probe = ffprobe(video)
    streams = probe.get('streams', [])
    v = next((s for s in streams if s.get('codec_type') == 'video'), None)
    a = next((s for s in streams if s.get('codec_type') == 'audio'), None)
    duration = float(probe['format']['duration'])
    errors = []
    if not v or v.get('width', 0) < minimum_width or v.get('height') != round(v.get('width', 0) * 16 / 9):
        errors.append('Missing or invalid 9:16 video stream')
    if not a:
        errors.append('Missing audio stream')
    if duration < 1 or duration > 61:
        errors.append('Duration outside allowed range')
    if video.stat().st_size < 20000:
        errors.append('Video too small')
    brightness = []
    for second in [duration*.12, duration*.50, duration*.86]:
        result = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-ss', str(second),
            '-i', str(video), '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', 'pipe:1'],
            check=True, capture_output=True)
        img = Image.open(io.BytesIO(result.stdout)).convert('L').resize((80, 142))
        brightness.append(round(ImageStat.Stat(img).mean[0], 2))
        if brightness[-1] < 5:
            errors.append(f'Near-black frame at {second:.2f}s')
    return {'passed': not errors, 'errors': errors, 'duration': duration,
        'width': v.get('width') if v else None, 'height': v.get('height') if v else None,
        'has_audio': bool(a), 'sample_luminance': brightness}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('video')
    p.add_argument('--min-width', type=int, default=540)
    args = p.parse_args()
    result = check(args.video, args.min_width)
    path = Path(args.video).with_name(Path(args.video).stem + '_qa.json')
    path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
