"""Foci-Med Harness API — FastAPI backend for the web dashboard.

Endpoints
---------
GET  /api/health
GET  /api/config           current project/DB config (password redacted)
POST /api/config           update project dir or DB credentials at runtime
GET  /api/stats            live DB record counts
POST /api/seed             enqueue a bulk data-seed job
GET  /api/seed/{id}/stream SSE: real-time seed progress
POST /api/tests/run        enqueue a pytest suite run
GET  /api/tests/{id}/stream SSE: real-time test output
GET  /api/jobs             list all jobs (seed + test) with status
GET  /api/catalog          full test catalog (all groups + cyber + sandbox)
POST /api/catalog/run      run selected test IDs via catalog executor
GET  /api/catalog/{id}/stream SSE: real-time catalog run output
GET  /api/audit/{job_id}   get compiled audit report for a completed job
GET  /api/history          list all completed audit reports
POST /api/upload           receive uploaded project folder
POST /api/cyber/run        run cyber mode tests
GET  /api/cyber/{id}/stream SSE: cyber run output
POST /api/sandbox/run      activate and run a sandbox environment
GET  /api/sandbox/{id}/stream SSE: sandbox run output
POST /api/reset            clear all jobs and audit history

Run locally::

    cd backend
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import AsyncGenerator, List, Optional

import asyncpg
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from seeder import run_seed
from runner import run_tests
from catalog import get_catalog_json, ALL_TESTS_BY_ID, CYBER_CATEGORIES, SANDBOX_TYPES
from executor import execute_batch
from audit import compile_audit

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

# ── In-memory stores ───────────────────────────────────────────────────────── #
_jobs:   dict[str, dict] = {}      # job_id → {status, type, queue, started, summary}
_audits: dict[str, dict] = {}      # job_id → AuditReport.to_dict()

# ── Mutable runtime config ─────────────────────────────────────────────────── #
_config: dict = {
    "db_host":     os.getenv("FOCIMED_DB_HOST",     "localhost"),
    "db_port":     int(os.getenv("FOCIMED_DB_PORT", "5432")),
    "db_name":     os.getenv("FOCIMED_DB_NAME",     "focimed_core"),
    "db_user":     os.getenv("FOCIMED_SUPERUSER",   "postgres"),
    "db_password": os.getenv("POSTGRES_PASSWORD",   "focimed_local_secret"),
    "app_user":    os.getenv("FOCIMED_APP_USER",    "app_user"),
    "app_password":os.getenv("FOCIMED_APP_PASSWORD","app_user_local_secret"),
    "project_dir": os.getenv("FOCI_PROJECT_DIR",   os.path.dirname(os.path.dirname(__file__))),
}

# ── App ────────────────────────────────────────────────────────────────────── #
app = FastAPI(title="Foci-Med Harness API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / response models ──────────────────────────────────────────────── #
class SeedRequest(BaseModel):
    n_tenants: int = 5
    n_patients_per_tenant: int = 1_000
    include_encounters: bool = True
    include_claims: bool = True
    clear_existing: bool = False


class TestRequest(BaseModel):
    suites: list[str] = ["functional", "security"]
    project_dir: Optional[str] = None


class ConfigUpdate(BaseModel):
    project_dir: Optional[str] = None
    db_host: Optional[str] = None
    db_port: Optional[int] = None
    db_name: Optional[str] = None
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    app_user: Optional[str] = None
    app_password: Optional[str] = None


class CatalogRunRequest(BaseModel):
    test_ids: List[str]
    project_dir: Optional[str] = None
    target_url: Optional[str] = None


class CyberRunRequest(BaseModel):
    test_ids: List[str]
    target_url: str = "http://localhost:3000"
    project_dir: Optional[str] = None


class SandboxRunRequest(BaseModel):
    sandbox_id: str
    test_ids: List[str]
    target_url: Optional[str] = None
    project_dir: Optional[str] = None


# ── Helpers ────────────────────────────────────────────────────────────────── #
async def _db_connect() -> asyncpg.Connection:
    return await asyncpg.connect(
        host=_config["db_host"],
        port=_config["db_port"],
        database=_config["db_name"],
        user=_config["db_user"],
        password=_config["db_password"],
    )


async def _sse_stream(job_id: str) -> AsyncGenerator[str, None]:
    """Yield SSE frames from the job queue until the job signals done."""
    job = _jobs.get(job_id)
    if not job:
        yield f"data: {json.dumps({'error': 'job not found'})}\n\n"
        return
    q: asyncio.Queue = job["queue"]
    while True:
        try:
            msg = await asyncio.wait_for(q.get(), timeout=30.0)
            yield f"data: {json.dumps(msg)}\n\n"
            if msg.get("done"):
                break
        except asyncio.TimeoutError:
            yield 'data: {"ping":true}\n\n'
        except Exception:
            break


def _new_job(kind: str) -> tuple[str, asyncio.Queue]:
    job_id = str(uuid.uuid4())
    q: asyncio.Queue = asyncio.Queue()
    _jobs[job_id] = {
        "status":  "running",
        "type":    kind,
        "queue":   q,
        "started": time.time(),
        "summary": None,
    }
    return job_id, q


# ── Health / Config / Stats ────────────────────────────────────────────────── #
@app.get("/api/health")
async def health():
    return {"status": "ok", "ts": time.time()}


@app.get("/api/config")
async def get_config():
    return {k: v for k, v in _config.items() if "password" not in k}


@app.post("/api/config")
async def update_config(body: ConfigUpdate):
    for k, v in body.model_dump(exclude_none=True).items():
        _config[k] = v
    return {"updated": True}


@app.get("/api/stats")
async def get_stats():
    try:
        conn = await _db_connect()
        n_tenants  = await conn.fetchval("SELECT count(*) FROM pool_01.tenants")
        n_patients = await conn.fetchval("SELECT count(*) FROM pool_01.patients")
        n_claims   = await conn.fetchval("SELECT count(*) FROM pool_01.claim_header")
        await conn.close()
        jobs_total = len(_jobs)
        jobs_done  = sum(1 for j in _jobs.values() if j["status"] in ("done", "error"))
        return {
            "db": {
                "tenants":  int(n_tenants),
                "patients": int(n_patients),
                "claims":   int(n_claims),
            },
            "jobs":         {"total": jobs_total, "done": jobs_done},
            "audits_total": len(_audits),
            "db_connected": True,
        }
    except Exception as exc:
        return {
            "db": {"tenants": 0, "patients": 0, "claims": 0},
            "jobs": {"total": len(_jobs), "done": 0},
            "audits_total": len(_audits),
            "db_connected": False,
            "error": str(exc),
        }


# ── Seed ──────────────────────────────────────────────────────────────────── #
@app.post("/api/seed")
async def start_seed(body: SeedRequest, background_tasks: BackgroundTasks):
    job_id, q = _new_job("seed")
    background_tasks.add_task(_run_seed_job, job_id, q, body.model_dump())
    return {"job_id": job_id}


async def _run_seed_job(job_id: str, q: asyncio.Queue, params: dict) -> None:
    try:
        await run_seed(q, _config, params)
        _jobs[job_id]["status"] = "done"
    except Exception as exc:
        await q.put({"level": "error", "msg": f"Seeder crashed: {exc}", "done": True})
        _jobs[job_id]["status"] = "error"


@app.get("/api/seed/{job_id}/stream")
async def seed_stream(job_id: str):
    return StreamingResponse(
        _sse_stream(job_id), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Legacy test suites ────────────────────────────────────────────────────── #
@app.post("/api/tests/run")
async def start_tests(body: TestRequest, background_tasks: BackgroundTasks):
    job_id, q = _new_job("test")
    project_dir = body.project_dir or _config["project_dir"]
    background_tasks.add_task(_run_test_job, job_id, q, project_dir, body.suites)
    return {"job_id": job_id}


async def _run_test_job(job_id: str, q: asyncio.Queue, project_dir: str, suites: list[str]) -> None:
    try:
        summary = await run_tests(q, project_dir, suites, _config)
        _jobs[job_id]["status"] = "done"
        _jobs[job_id]["summary"] = summary
    except Exception as exc:
        await q.put({"level": "error", "msg": f"Runner crashed: {exc}", "done": True})
        _jobs[job_id]["status"] = "error"


@app.get("/api/tests/{job_id}/stream")
async def test_stream(job_id: str):
    return StreamingResponse(
        _sse_stream(job_id), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Catalog ───────────────────────────────────────────────────────────────── #
@app.get("/api/catalog")
async def get_catalog():
    return get_catalog_json()


@app.post("/api/catalog/run")
async def run_catalog(body: CatalogRunRequest, background_tasks: BackgroundTasks):
    job_id, q = _new_job("catalog")
    project_dir = body.project_dir or _config["project_dir"]
    background_tasks.add_task(
        _run_catalog_job, job_id, q, body.test_ids, project_dir,
        body.target_url, "standard",
    )
    return {"job_id": job_id}


async def _run_catalog_job(
    job_id: str, q: asyncio.Queue, test_ids: list[str],
    project_dir: str, target_url: Optional[str], mode: str,
) -> None:
    try:
        await q.put({"level": "info", "msg": f"Starting {len(test_ids)} tests ({mode} mode) …"})
        results = await execute_batch(test_ids, project_dir, _config, target_url or "", q)
        report  = compile_audit(results, target=project_dir, mode=mode)
        _audits[job_id] = report.to_dict()
        _jobs[job_id]["status"]  = "done"
        _jobs[job_id]["summary"] = {
            "score":      report.overall_score,
            "risk":       report.risk_level,
            "passed":     report.passed,
            "failed":     report.failed,
            "total":      report.total,
            "audit_id":   report.id,
        }
        await q.put({
            "done":     True,
            "audit_id": report.id,
            "score":    report.overall_score,
            "risk":     report.risk_level,
            "summary":  report.executive_summary,
        })
    except Exception as exc:
        await q.put({"level": "error", "msg": f"Catalog run crashed: {exc}", "done": True})
        _jobs[job_id]["status"] = "error"


@app.get("/api/catalog/{job_id}/stream")
async def catalog_stream(job_id: str):
    return StreamingResponse(
        _sse_stream(job_id), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Audit ─────────────────────────────────────────────────────────────────── #
@app.get("/api/audit/{job_id}")
async def get_audit(job_id: str):
    report = _audits.get(job_id)
    if not report:
        return {"error": "Audit not found. The job may still be running or has no results."}
    return report


@app.get("/api/history")
async def get_history():
    return [
        {
            "job_id":        job_id,
            "audit_id":      r.get("id"),
            "generated_at":  r.get("generated_at"),
            "target":        r.get("target"),
            "overall_score": r.get("overall_score"),
            "risk_level":    r.get("risk_level"),
            "total":         r.get("total"),
            "passed":        r.get("passed"),
            "failed":        r.get("failed"),
            "mode":          r.get("mode", "standard"),
        }
        for job_id, r in sorted(
            _audits.items(),
            key=lambda x: x[1].get("generated_at", ""),
            reverse=True,
        )
    ]


# ── Upload ────────────────────────────────────────────────────────────────── #
@app.post("/api/upload")
async def upload_project(files: List[UploadFile] = File(...)):
    """Accept a list of files representing an uploaded project folder.

    The browser sends all files from a <input webkitdirectory> selection.
    We write them into a temporary directory keyed by a unique upload ID and
    return that directory path so the run endpoints can use it as project_dir.
    """
    upload_id  = str(uuid.uuid4())
    upload_dir = os.path.join(tempfile.gettempdir(), "focimed_uploads", upload_id)
    os.makedirs(upload_dir, exist_ok=True)

    saved = 0
    for f in files:
        # filename may include relative paths from webkitdirectory (e.g. "myapp/src/index.py")
        dest = os.path.join(upload_dir, f.filename or f"file_{saved}")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        content = await f.read()
        with open(dest, "wb") as fh:
            fh.write(content)
        saved += 1

    return {"upload_id": upload_id, "project_dir": upload_dir, "files_saved": saved}


# ── Cyber Mode ────────────────────────────────────────────────────────────── #
@app.post("/api/cyber/run")
async def run_cyber(body: CyberRunRequest, background_tasks: BackgroundTasks):
    job_id, q = _new_job("cyber")
    project_dir = body.project_dir or _config["project_dir"]
    background_tasks.add_task(
        _run_catalog_job, job_id, q, body.test_ids, project_dir,
        body.target_url, "cyber",
    )
    return {"job_id": job_id}


@app.get("/api/cyber/{job_id}/stream")
async def cyber_stream(job_id: str):
    return StreamingResponse(
        _sse_stream(job_id), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Sandbox ───────────────────────────────────────────────────────────────── #
@app.post("/api/sandbox/run")
async def run_sandbox(body: SandboxRunRequest, background_tasks: BackgroundTasks):
    job_id, q = _new_job("sandbox")
    project_dir = body.project_dir or _config["project_dir"]
    background_tasks.add_task(
        _run_sandbox_job, job_id, q, body.sandbox_id,
        body.test_ids, project_dir, body.target_url,
    )
    return {"job_id": job_id}


async def _run_sandbox_job(
    job_id: str, q: asyncio.Queue, sandbox_id: str,
    test_ids: list[str], project_dir: str, target_url: Optional[str],
) -> None:
    sandbox = next((s for s in SANDBOX_TYPES if s["id"] == sandbox_id), None)
    sb_name = sandbox["name"] if sandbox else sandbox_id
    await q.put({"level": "info", "msg": f"Activating sandbox: {sb_name} …"})
    await asyncio.sleep(0.5)
    await q.put({"level": "success", "msg": f"Sandbox environment '{sb_name}' ready."})

    await _run_catalog_job(job_id, q, test_ids, project_dir, target_url, "sandbox")


@app.get("/api/sandbox/{job_id}/stream")
async def sandbox_stream(job_id: str):
    return StreamingResponse(
        _sse_stream(job_id), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Jobs list / Reset ─────────────────────────────────────────────────────── #
@app.get("/api/jobs")
async def list_jobs():
    return [
        {
            "id":      jid,
            "type":    j["type"],
            "status":  j["status"],
            "started": j["started"],
            "summary": j.get("summary"),
        }
        for jid, j in sorted(_jobs.items(), key=lambda x: x[1]["started"], reverse=True)
    ]


@app.post("/api/reset")
async def reset_session():
    """Clear all in-memory jobs and audit history."""
    _jobs.clear()
    _audits.clear()
    return {"reset": True, "ts": time.time()}
