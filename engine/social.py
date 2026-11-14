"""Prepare a reviewed publishing package; never posts without authorization."""
import argparse
import json
from pathlib import Path
from engine.studio import validate_project


def create_manifest(project_path, video_path):
    project = json.loads(Path(project_path).read_text(encoding='utf-8'))
    validate_project(project)
    video = Path(video_path)
    if not video.is_file():
        raise FileNotFoundError(video)
    social = project.get('social', {})
    if not isinstance(social, dict):
        raise ValueError('social must be an object')
    hashtags = social.get('hashtags', [])
    if not isinstance(hashtags, list) or any(not isinstance(tag, str) or len(tag)>50 for tag in hashtags):
        raise ValueError('Invalid hashtags')
    manifest = {
        'status': 'draft_not_scheduled',
        'video': video.name,
        'cover': video.stem + '_cover.png',
        'caption': str(social.get('caption', project['title']))[:2200],
        'hashtags': hashtags,
        'platforms': social.get('platforms', []),
        'requires_human_review': True,
        'note': 'Use the connected Metricool app to schedule only after approval.'
    }
    out = video.with_name(video.stem + '_social.json')
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    return out


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--project',default='projects/first_light.json')
    p.add_argument('--video',default='output/first_light.mp4')
    a=p.parse_args()
    print(create_manifest(a.project,a.video))


if __name__=='__main__':
    main()
