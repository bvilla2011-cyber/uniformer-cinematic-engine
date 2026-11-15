"""Creator Studio MVP — single-user, local-first prototype.

Run: uvicorn studio.app:app --host 127.0.0.1 --port 8000
This is NOT safe to expose to the internet: no authentication or tenant isolation.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from studio.renderer import render_project

HERE = Path(__file__).resolve().parent
DATA = Path(os.environ.get("STUDIO_DATA_DIR", str(HERE.parent / "data"))).resolve()
ASSETS = DATA / "assets"
EXPORTS = DATA / "exports"
DB = DATA / "studio.sqlite3"
WEB = HERE / "web"
MAX_UPLOAD_BYTES = 200 * 1024 * 1024
ALLOWED_EXT = {".mp4", ".mov", ".m4v", ".webm", ".png", ".jpg", ".jpeg", ".webp", ".mp3", ".wav", ".m4a", ".aac"}
JOBS: dict[str, dict[str, Any]] = {}
JOB_LOCK = threading.Lock()

for directory in (DATA, ASSETS, EXPORTS):
    directory.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Creator Studio MVP", version="0.1.0", docs_url="/api/docs", redoc_url=None)


def conn():
    db = sqlite3.connect(DB, check_same_thread=False, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def require_project(db, project_id: str):
    row = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Proyecto no encontrado")
    return dict(row)


def project_detail(db, project_id: str):
    project = require_project(db, project_id)
    project["scenes"] = [dict(x) for x in db.execute("SELECT * FROM scenes WHERE project_id=? ORDER BY position,id", (project_id,))]
    project["assets"] = [dict(x) for x in db.execute("SELECT id, filename, kind, created_at FROM assets WHERE project_id=? ORDER BY created_at DESC", (project_id,))]
    return project


def init_db():
    with conn() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, idea TEXT NOT NULL DEFAULT '',
            aspect TEXT NOT NULL DEFAULT '9:16', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS scenes (
            id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            position INTEGER NOT NULL, title TEXT NOT NULL, narration TEXT NOT NULL DEFAULT '',
            duration REAL NOT NULL DEFAULT 5, asset_id TEXT, voice_asset_id TEXT, notes TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS assets (
            id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            filename TEXT NOT NULL, kind TEXT NOT NULL, storage_name TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)
        count = db.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        if count == 0:
            pid = uuid.uuid4().hex
            stamp = now()
            db.execute("INSERT INTO projects VALUES (?,?,?,?,?,?)", (pid, "El poder de las ideas", "Una reflexión cinematográfica sobre la creatividad y el futuro", "9:16", stamp, stamp))
            scenes = [
                ("Todo empieza con una idea", "Hay ideas que cambian una tarde. Otras cambian el mundo.", 4.5, "Apertura impactante"),
                ("El primer paso", "Lo extraordinario comienza cuando alguien se atreve a intentarlo.", 5, "Transición suave"),
                ("Construir algo propio", "No se trata solo de crear: se trata de mejorar, probar y volver a crear.", 5, "Montaje dinámico"),
                ("Hazlo realidad", "Y la siguiente gran historia podría empezar hoy.", 4.5, "Cierre cinematográfico"),
            ]
            for i, (title, narration, dur, notes) in enumerate(scenes):
                db.execute("INSERT INTO scenes (id,project_id,position,title,narration,duration,notes) VALUES (?,?,?,?,?,?,?)",
                           (uuid.uuid4().hex, pid, i, title, narration, dur, notes))


init_db()


class NewProject(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    idea: str = Field(default="", max_length=2000)
    aspect: str = "9:16"


class NewScene(BaseModel):
    title: str = Field(default="Escena nueva", min_length=1, max_length=200)
    narration: str = Field(default="", max_length=12000)
    duration: float = Field(default=5, ge=1, le=120)


class CreativeRequest(BaseModel):
    project_id: str
    prompt: str = Field(min_length=10, max_length=4000)
    number_of_scenes: int = Field(default=6, ge=2, le=16)


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "render": shutil.which("ffmpeg") is not None,
        "ai": bool(os.getenv("AI_CHAT_URL") and os.getenv("AI_MODEL")),
        "stock": bool(os.getenv("PEXELS_API_KEY")),
        "version": "0.1.0",
        "mode": "single-user local prototype",
    }


@app.get("/api/projects")
def get_projects():
    with conn() as db:
        return [dict(x) for x in db.execute("""
            SELECT p.*, (SELECT COUNT(*) FROM scenes s WHERE s.project_id=p.id) AS scene_count
            FROM projects p ORDER BY updated_at DESC
        """)]


@app.post("/api/projects")
def create_project(payload: NewProject):
    if payload.aspect not in {"16:9", "9:16", "1:1"}:
        raise HTTPException(422, "Formato no válido")
    pid = uuid.uuid4().hex
    stamp = now()
    with conn() as db:
        db.execute("INSERT INTO projects VALUES (?,?,?,?,?,?)", (pid, payload.title.strip(), payload.idea, payload.aspect, stamp, stamp))
        return project_detail(db, pid)


@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    with conn() as db:
        return project_detail(db, project_id)


@app.patch("/api/projects/{project_id}")
def update_project(project_id: str, payload: dict):
    allowed = {"title", "idea", "aspect"}
    values = {k: v for k, v in payload.items() if k in allowed}
    if not values:
        raise HTTPException(422, "Sin cambios")
    if "aspect" in values and values["aspect"] not in {"16:9", "9:16", "1:1"}:
        raise HTTPException(422, "Formato no válido")
    if "title" in values and (not isinstance(values["title"], str) or not (1 <= len(values["title"]) <= 120)):
        raise HTTPException(422, "Título no válido")
    if "idea" in values and (not isinstance(values["idea"], str) or len(values["idea"]) > 2000):
        raise HTTPException(422, "Idea no válida")
    values["updated_at"] = now()
    with conn() as db:
        require_project(db, project_id)
        fields = ",".join(f"{k}=?" for k in values)
        db.execute(f"UPDATE projects SET {fields} WHERE id=?", (*values.values(), project_id))
        return project_detail(db, project_id)


@app.post("/api/projects/{project_id}/scenes")
def add_scene(project_id: str, payload: NewScene):
    with conn() as db:
        require_project(db, project_id)
        position = db.execute("SELECT COALESCE(MAX(position),-1)+1 FROM scenes WHERE project_id=?", (project_id,)).fetchone()[0]
        db.execute("INSERT INTO scenes (id,project_id,position,title,narration,duration) VALUES (?,?,?,?,?,?)",
                   (uuid.uuid4().hex, project_id, position, payload.title, payload.narration, payload.duration))
        db.execute("UPDATE projects SET updated_at=? WHERE id=?", (now(), project_id))
        return project_detail(db, project_id)


@app.patch("/api/projects/{project_id}/scenes/{scene_id}")
def update_scene(project_id: str, scene_id: str, payload: dict):
    allowed = {"title", "narration", "duration", "asset_id", "voice_asset_id", "notes"}
    values = {k: v for k, v in payload.items() if k in allowed}
    if not values:
        raise HTTPException(422, "Sin cambios")
    if "duration" in values:
        try:
            values["duration"] = float(values["duration"])
        except (TypeError, ValueError):
            raise HTTPException(422, "Duración inválida")
        if not 1 <= values["duration"] <= 120:
            raise HTTPException(422, "La duración debe estar entre 1 y 120 segundos")
    for k, limit in (("title", 200), ("narration", 12000), ("notes", 3000)):
        if k in values and (not isinstance(values[k], str) or len(values[k]) > limit or (k == "title" and not values[k].strip())):
            raise HTTPException(422, f"Campo no válido: {k}")
    with conn() as db:
        require_project(db, project_id)
        row = db.execute("SELECT 1 FROM scenes WHERE id=? AND project_id=?", (scene_id, project_id)).fetchone()
        if not row:
            raise HTTPException(404, "Escena no encontrada")
        for k in ("asset_id", "voice_asset_id"):
            if k in values and values[k] is not None:
                asset = db.execute("SELECT kind FROM assets WHERE id=? AND project_id=?", (values[k], project_id)).fetchone()
                if not asset or (k == "voice_asset_id" and asset[0] != "audio") or (k == "asset_id" and asset[0] == "audio"):
                    raise HTTPException(422, f"Recurso no válido: {k}")
        db.execute("UPDATE scenes SET "+",".join(f"{k}=?" for k in values)+" WHERE id=? AND project_id=?", (*values.values(), scene_id, project_id))
        db.execute("UPDATE projects SET updated_at=? WHERE id=?", (now(), project_id))
        return project_detail(db, project_id)


@app.delete("/api/projects/{project_id}/scenes/{scene_id}")
def delete_scene(project_id: str, scene_id: str):
    with conn() as db:
        require_project(db, project_id)
        db.execute("DELETE FROM scenes WHERE id=? AND project_id=?", (scene_id, project_id))
        db.execute("UPDATE projects SET updated_at=? WHERE id=?", (now(), project_id))
        return project_detail(db, project_id)


@app.post("/api/projects/{project_id}/scenes/reorder")
def reorder_scenes(project_id: str, payload: dict):
    scene_ids = payload.get("ids")
    with conn() as db:
        require_project(db, project_id)
        current = [r[0] for r in db.execute("SELECT id FROM scenes WHERE project_id=?", (project_id,))]
        if not isinstance(scene_ids, list) or len(scene_ids) != len(current) or set(scene_ids) != set(current):
            raise HTTPException(422, "Lista de escenas incorrecta")
        for pos, sid in enumerate(scene_ids):
            db.execute("UPDATE scenes SET position=? WHERE project_id=? AND id=?", (pos, project_id, sid))
        return project_detail(db, project_id)


@app.post("/api/projects/{project_id}/assets")
async def upload_asset(project_id: str, file: UploadFile = File(...)):
    with conn() as db:
        require_project(db, project_id)
    original = Path(file.filename or "asset").name
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(415, "Formato no soportado")
    kind = "video" if ext in {".mp4", ".mov", ".m4v", ".webm"} else "audio" if ext in {".mp3", ".wav", ".m4a", ".aac"} else "image"
    aid = uuid.uuid4().hex
    storage_name = aid + ext
    path = ASSETS / storage_name
    size = 0
    try:
        with path.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "Archivo demasiado grande (máximo 200 MB)")
                out.write(chunk)
        if size == 0:
            raise HTTPException(422, "Archivo vacío")
        # Reject renamed non-media uploads when ffprobe is available.
        if shutil.which("ffprobe"):
            result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)], capture_output=True, text=True, timeout=15)
            if result.returncode != 0 or kind not in result.stdout.split():
                raise HTTPException(422, "El archivo no contiene contenido multimedia válido")
        with conn() as db:
            db.execute("INSERT INTO assets VALUES (?,?,?,?,?,?)", (aid, project_id, original[:255], kind, storage_name, now()))
            return {"asset": {"id": aid, "filename": original, "kind": kind}, "project": project_detail(db, project_id)}
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


@app.get("/api/assets/{asset_id}")
def get_asset(asset_id: str):
    with conn() as db:
        row = db.execute("SELECT * FROM assets WHERE id=?", (asset_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Recurso no encontrado")
    return FileResponse(ASSETS / row["storage_name"], filename=row["filename"], content_disposition_type="inline")


def call_ai(prompt: str):
    url = os.getenv("AI_CHAT_URL", "").strip()
    model = os.getenv("AI_MODEL", "").strip()
    if not url or not model:
        raise HTTPException(503, "Configura AI_CHAT_URL y AI_MODEL para activar la IA real")
    if not url.startswith("https://") and not (url.startswith("http://127.0.0.1:") or url.startswith("http://localhost:")):
        raise HTTPException(503, "La URL del proveedor debe ser HTTPS o localhost")
    data = json.dumps({
        "model": model,
        "temperature": 0.65,
        "messages": [
            {"role": "system", "content": "Eres director audiovisual y guionista. Devuelve solo JSON válido: {\"scenes\":[{\"title\":string,\"narration\":string,\"duration\":number,\"notes\":string}]}. Crea escenas originales y coherentes, sin inventar derechos de uso de ningún material."},
            {"role": "user", "content": prompt},
        ],
    }).encode()
    headers = {"Content-Type": "application/json"}
    if os.getenv("AI_API_KEY"):
        headers["Authorization"] = "Bearer " + os.environ["AI_API_KEY"]
    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=45) as response:
            result = json.loads(response.read(1_000_000))
        content = result["choices"][0]["message"]["content"]
        content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed = json.loads(content)
        if not isinstance(parsed, dict) or not isinstance(parsed.get("scenes"), list):
            raise ValueError("Respuesta sin escenas")
        return parsed["scenes"]
    except (ValueError, KeyError, IndexError, urllib.error.URLError, TimeoutError) as exc:
        raise HTTPException(502, f"El proveedor IA no devolvió un storyboard válido: {str(exc)[:180]}")


@app.post("/api/storyboard")
def create_storyboard(payload: CreativeRequest):
    with conn() as db:
        project = require_project(db, payload.project_id)
    prompt = (f"Crea exactamente {payload.number_of_scenes} escenas para un vídeo en formato {project['aspect']}. "
              f"Título: {project['title']}. Idea: {payload.prompt}. Cada escena debe durar 3–15 segundos. "
              "Narración en español natural, muy cuidada y con dirección visual específica. "
              "No escribas enlaces inventados, marcas ajenas ni atribuciones inexistentes.")
    scenes = call_ai(prompt)
    clean = []
    for item in scenes[:payload.number_of_scenes]:
        if not isinstance(item, dict):
            continue
        clean.append({
            "title": str(item.get("title") or "Escena")[:200],
            "narration": str(item.get("narration") or "")[:12000],
            "duration": max(1.0, min(120.0, float(item.get("duration") or 5))),
            "notes": str(item.get("notes") or "")[:3000],
        })
    if not clean:
        raise HTTPException(502, "El proveedor no generó escenas utilizables")
    with conn() as db:
        # Replaces the script, but keeps previously imported assets in the project library.
        db.execute("DELETE FROM scenes WHERE project_id=?", (payload.project_id,))
        for i, scene in enumerate(clean):
            db.execute("INSERT INTO scenes (id,project_id,position,title,narration,duration,notes) VALUES (?,?,?,?,?,?,?)",
                       (uuid.uuid4().hex, payload.project_id, i, scene["title"], scene["narration"], scene["duration"], scene["notes"]))
        db.execute("UPDATE projects SET idea=?,updated_at=? WHERE id=?", (payload.prompt, now(), payload.project_id))
        return project_detail(db, payload.project_id)


@app.get("/api/stock/search")
def stock_search(query: str = Query(min_length=2, max_length=100), orientation: str = "portrait"):
    key = os.getenv("PEXELS_API_KEY", "")
    if not key:
        raise HTTPException(503, "Configura PEXELS_API_KEY para buscar clips")
    if orientation not in {"portrait", "landscape", "square"}:
        raise HTTPException(422, "Orientación inválida")
    params = urllib.parse.urlencode({"query": query, "orientation": orientation, "per_page": 12})
    url = "https://api.pexels.com/v1/videos/search?" + params
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": key}), timeout=15) as response:
            result = json.loads(response.read(3_000_000))
    except (urllib.error.URLError, ValueError) as exc:
        raise HTTPException(502, f"Pexels no disponible: {str(exc)[:120]}")
    return {"source": "Pexels", "source_url": "https://www.pexels.com/", "clips": [
        {"id": v.get("id"), "url": v.get("url"), "image": v.get("image"),
         "duration": v.get("duration"), "creator": (v.get("user") or {}).get("name", "Pexels")}
        for v in result.get("videos", [])
    ]}


def run_render(job_id: str, project: dict, assets: dict):
    try:
        target = EXPORTS / f"{job_id}.mp4"
        def progress(value: float, message: str):
            with JOB_LOCK:
                JOBS[job_id].update(progress=round(value, 1), message=message)
        render_project(project, assets, target, progress)
        with JOB_LOCK:
            JOBS[job_id].update(status="ready", progress=100, message="MP4 exportado correctamente")
    except Exception as exc:
        with JOB_LOCK:
            JOBS[job_id].update(status="error", message=str(exc)[:300])


@app.post("/api/projects/{project_id}/render")
def start_render(project_id: str):
    if not shutil.which("ffmpeg"):
        raise HTTPException(503, "Instala FFmpeg para activar la exportación")
    with conn() as db:
        project = project_detail(db, project_id)
        if not project["scenes"]:
            raise HTTPException(422, "Añade escenas antes de renderizar")
        ids = {x[k] for x in project["scenes"] for k in ("asset_id", "voice_asset_id") if x[k]}
        assets = {}
        for aid in ids:
            row = db.execute("SELECT * FROM assets WHERE id=? AND project_id=?", (aid, project_id)).fetchone()
            if not row:
                raise HTTPException(422, "Hay archivos que ya no pertenecen al proyecto")
            assets[aid] = {**dict(row), "path": str(ASSETS / row["storage_name"])}
    job_id = uuid.uuid4().hex
    with JOB_LOCK:
        JOBS[job_id] = {"id": job_id, "status": "rendering", "progress": 0, "message": "Preparando render"}
    thread = threading.Thread(target=run_render, args=(job_id, project, assets), daemon=True)
    thread.start()
    return JOBS[job_id]


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    with JOB_LOCK:
        job = JOBS.get(job_id)
        if not job:
            raise HTTPException(404, "Trabajo no encontrado (reiniciar el servidor elimina el historial)")
        return dict(job)


@app.get("/api/exports/{job_id}")
def get_export(job_id: str):
    with JOB_LOCK:
        job = JOBS.get(job_id)
        if not job or job["status"] != "ready":
            raise HTTPException(404, "Exportación no disponible")
    return FileResponse(EXPORTS / (job_id + ".mp4"), media_type="video/mp4", filename="creator-studio-" + job_id[:8] + ".mp4")


app.mount("/", StaticFiles(directory=WEB, html=True), name="web")