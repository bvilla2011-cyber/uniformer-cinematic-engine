import shutil
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from studio.app import app
from studio.renderer import render_project

client = TestClient(app)


def test_health_and_demo():
    r = client.get('/api/health')
    assert r.status_code == 200
    assert r.json()['ok'] is True
    projects = client.get('/api/projects').json()
    assert isinstance(projects, list) and len(projects) >= 1
    loaded = client.get('/api/projects/' + projects[0]['id']).json()
    assert isinstance(loaded['scenes'], list)


def test_projects_scene_and_validation():
    r = client.post('/api/projects', json={'title': 'Test de escenas', 'aspect': '16:9'})
    assert r.status_code == 200
    p = r.json()
    assert p['scenes'] == []
    pid = p['id']
    scene = client.post(f'/api/projects/{pid}/scenes', json={'title':'Primera', 'duration': 2})
    assert scene.status_code == 200
    sid = scene.json()['scenes'][0]['id']
    changed = client.patch(f'/api/projects/{pid}/scenes/{sid}', json={'title':'Editada', 'narration':'Narración editada', 'duration': 3})
    assert changed.status_code == 200
    assert changed.json()['scenes'][0]['title'] == 'Editada'
    assert client.patch(f'/api/projects/{pid}/scenes/{sid}', json={'duration': -2}).status_code == 422
    assert client.patch(f'/api/projects/{pid}', json={'aspect':'invalid'}).status_code == 422
    assert client.get('/api/projects/not-found').status_code == 404
    assert client.delete(f'/api/projects/{pid}/scenes/{sid}').status_code == 200


def test_upload_rejects_unsupported_extension():
    p = client.post('/api/projects', json={'title':'Archivos'}).json()
    r = client.post(f'/api/projects/{p["id"]}/assets', files={'file':('danger.py', b'print(1)', 'text/plain')})
    assert r.status_code == 415


def test_render_real_mp4():
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        return
    project = {'aspect':'16:9', 'scenes':[{'title':'Prueba real', 'narration':'Exportación verificable', 'duration':1, 'asset_id':None, 'voice_asset_id':None}]}
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)/'render.mp4'
        render_project(project, {}, out)
        assert out.exists() and out.stat().st_size > 2000
        import subprocess
        proc = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nokey=1:noprint_wrappers=1',str(out)],capture_output=True,text=True,check=True)
        assert 0.9 <= float(proc.stdout) <= 1.15
