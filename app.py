"""Local web UI and JSON API for the research and planning modules."""

import os
import secrets
import threading
import time
from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Header, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from models import ResearchRequest, ResearchResult
from knowledge_base import KNOWLEDGE_PATH, retrieve_knowledge
from research import research
from deepseek_web import DeepSeekWebError

from planner.schema import PlanRequest, load_plan_request
from planner.timeline import build_plan, render_markdown as render_plan_markdown
from workflow import WorkflowRequest, plan_research, english_sample


ROOT = Path(__file__).resolve().parent
PLANNER_CASE_DIR = ROOT / "planner" / "cases"
app = FastAPI(title="ExchangePrep Research + Planner Demo", version="0.4.0")
PUBLIC_ORIGINS = [origin.strip().rstrip("/") for origin in os.getenv(
    "EXCHANGEPREP_ALLOWED_ORIGINS", "https://gwdsd1.github.io").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=PUBLIC_ORIGINS,
    allow_methods=["GET", "POST"], allow_headers=["Content-Type", "X-API-Key"], allow_credentials=False)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.middleware("http")
async def workflow_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith(("/api/workflow", "/workspace")):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/workspace")
def workspace():
    return FileResponse(ROOT / "static" / "workspace.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/workflow")
def run_workflow(payload: WorkflowRequest, request: Request,
                 x_api_key: str = Header(default="")):
    origin = request.headers.get("origin")
    if origin and origin != str(request.base_url).rstrip("/") and origin not in PUBLIC_ORIGINS:
        raise HTTPException(status_code=403, detail="请从本服务网页发起请求")
    if not x_api_key.strip() or len(x_api_key) > 512:
        raise HTTPException(status_code=400, detail="请在网页输入有效的 API Key")
    target = ResearchRequest.model_validate(payload.model_dump())
    try:
        result = research(target, provider=payload.provider,
            api_key=x_api_key.strip(), model=payload.model or None,
            search_backend="deepseek" if payload.provider == "deepseek" else "openai")
        return plan_research(result, payload)
    except Exception as exc:
        # Never echo provider responses, request headers or key-bearing exceptions.
        name = type(exc).__name__
        message = {"AuthenticationError": "API Key 认证失败，请检查提供商和密钥。",
            "RateLimitError": "请求限流或额度不足，请检查账户后重试。",
            "APITimeoutError": "模型请求超时，请稍后重试。"}.get(name,
            f"调查或排期未完成（{name}），请检查网络、模型名和项目网址后重试。")
        if payload.language == "en":
            message = {"AuthenticationError": "API key authentication failed. Check the key and selected provider.",
                "RateLimitError": "Rate limit or insufficient quota. Check your provider account.",
                "APITimeoutError": "The model request timed out. Please retry."}.get(name,
                f"Research or planning failed ({name}). Check the connection, model name and programme URL, then retry.")
        if isinstance(exc, DeepSeekWebError) and exc.status_code in {401, 402}:
            status = exc.status_code
            message = ("DeepSeek Search/Fetch authentication failed. Check your API key." if status == 401 else
                "DeepSeek account balance is insufficient for Search/Fetch.") if payload.language == "en" else (
                "DeepSeek Search/Fetch 密钥认证失败，请检查 API Key。" if status == 401 else
                "DeepSeek 账户余额不足，无法继续 Search/Fetch。")
        raise HTTPException(status_code=502, detail=message) from None


@app.post("/api/workflow/sample")
def workflow_sample(payload: WorkflowRequest):
    result = sample()
    if payload.language == "en":
        result = english_sample(result)
    result.request = ResearchRequest.model_validate(payload.model_dump())
    return plan_research(result, payload)


# One browser investigation at a time on a small free instance. Completed
# results are held in RAM for 30 minutes, never written to disk.
_jobs = {}
_jobs_lock = threading.Lock()


@app.post("/api/workflow/jobs", status_code=202)
def start_workflow_job(payload: WorkflowRequest, request: Request,
                       x_api_key: str = Header(default="")):
    origin = request.headers.get("origin")
    if origin and origin != str(request.base_url).rstrip("/") and origin not in PUBLIC_ORIGINS:
        raise HTTPException(status_code=403, detail="Origin not allowed")
    if not x_api_key.strip() or len(x_api_key) > 512:
        raise HTTPException(status_code=400, detail="Enter a valid API key" if payload.language == "en" else "请输入有效的 API Key")
    with _jobs_lock:
        expired = [key for key, job in _jobs.items() if job["status"] != "running" and time.monotonic()-job["created"] > 1800]
        for key in expired:
            del _jobs[key]
        if any(job["status"] == "running" for job in _jobs.values()):
            raise HTTPException(status_code=429, detail="Service busy. Please retry shortly." if payload.language == "en" else "当前已有调查进行中，请稍后重试。")
        while len(_jobs) >= 4:
            del _jobs[next(iter(_jobs))]
        job_id = secrets.token_urlsafe(32)
        _jobs[job_id] = {"status": "running", "created": time.monotonic()}
    def execute():
        try:
            result = run_workflow(payload, request, x_api_key)
            with _jobs_lock:
                _jobs[job_id].update(status="complete", result=result)
        except HTTPException as exc:
            with _jobs_lock:
                _jobs[job_id].update(status="failed", detail=exc.detail)
        except Exception:
            with _jobs_lock:
                _jobs[job_id].update(status="failed", detail="Request failed. Please retry.")
    threading.Thread(target=execute, daemon=True).start()
    return {"job_id": job_id, "status": "running"}


@app.get("/api/workflow/jobs/{job_id}")
def workflow_job(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None or (job["status"] != "running" and time.monotonic()-job["created"] > 1800):
            raise HTTPException(status_code=404, detail="Result expired or unavailable; please run a new query.")
        return {key: value for key, value in job.items() if key != "created"}


@app.get("/planner")
def planner_page():
    """Readable view of the dependency-modelling and timeline output."""

    return FileResponse(ROOT / "static" / "planner.html")


@app.get("/api/config")
def config():
    return {
        "llm_provider": os.getenv("EXCHANGEPREP_LLM_PROVIDER", os.getenv("PATHLOOM_LLM_PROVIDER", "openai")),
        "search_provider": os.getenv("EXCHANGEPREP_SEARCH_PROVIDER", os.getenv("PATHLOOM_SEARCH_PROVIDER", "auto")),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "deepseek_configured": bool(os.getenv("DEEPSEEK_API_KEY")),
        "brave_configured": bool(os.getenv("BRAVE_API_KEY")),
        "knowledge_base_available": KNOWLEDGE_PATH.is_file(),
        "web_workflow_search": {"deepseek": "deepseek_search_fetch", "openai": "openai_web_search"},
    }


@app.get("/api/knowledge-base")
def search_knowledge_base(query: str = Query(min_length=1, max_length=300)):
    try:
        return {"matches": retrieve_knowledge(query), "document_url": "/api/knowledge-base/document"}
    except OSError as exc:
        raise HTTPException(status_code=503, detail="知识库文件不可读") from exc


@app.get("/api/knowledge-base/document")
def knowledge_document():
    if not KNOWLEDGE_PATH.is_file():
        raise HTTPException(status_code=404, detail="知识库文件不存在")
    return FileResponse(KNOWLEDGE_PATH, media_type="text/markdown; charset=utf-8")


@app.get("/api/sample", response_model=ResearchResult)
def sample():
    return ResearchResult.model_validate_json((ROOT / "sample.json").read_text(encoding="utf-8"))


@app.post("/api/research", response_model=ResearchResult)
def run_research(request: ResearchRequest, provider: Literal["openai", "deepseek"] | None = None):
    try:
        return research(request, provider=provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        # Never return API keys, raw provider bodies, or user data in an error response.
        raise HTTPException(status_code=502, detail=f"外部搜索或模型请求失败：{type(exc).__name__}") from exc


# --------------------------------------------------------------------------- #
# Dependency modelling and timeline generation (planner module)
# --------------------------------------------------------------------------- #
def _case_files() -> list[Path]:
    if not PLANNER_CASE_DIR.is_dir():
        return []
    return sorted(PLANNER_CASE_DIR.glob("*.json"))


def _case_path(case_id: str) -> Path:
    """Resolve a curated case by file stem *or* by the ``case_id`` it declares."""

    for path in _case_files():
        if path.stem == case_id:
            return path
        try:
            if load_plan_request(path).case_id == case_id:
                return path
        except Exception:
            continue
    raise HTTPException(status_code=404, detail=f"未知的规划案例：{case_id}")


@app.get("/api/planner/cases")
def planner_cases():
    """List the curated planning cases shipped with the planner module."""

    cases = []
    for path in _case_files():
        try:
            request = load_plan_request(path)
        except Exception:  # a broken manifest must not break the listing
            cases.append({"case_id": path.stem, "readable": False})
            continue
        cases.append(
            {
                "case_id": request.case_id,
                "file": path.name,
                "label": request.case_label,
                "programme_id": request.programme_id,
                "tasks": len(request.tasks),
                "as_of": request.as_of.isoformat(),
                "readable": True,
            }
        )
    return {"cases": cases}


@app.get("/api/planner/plan/{case_id}")
def planner_plan(
    case_id: str,
    as_of: date | None = Query(default=None, description="覆盖规划基准日期 YYYY-MM-DD"),
    format: Literal["json", "markdown"] = Query(default="json"),
):
    """Build the ordered, dated plan for a curated case."""

    request = load_plan_request(_case_path(case_id))
    if as_of is not None:
        request = request.model_copy(update={"as_of": as_of})
    plan = build_plan(request)
    if format == "markdown":
        return {"case_id": plan.case_id, "markdown": render_plan_markdown(plan)}
    return plan


@app.post("/api/planner/plan")
def planner_plan_from_payload(payload: PlanRequest, format: Literal["json", "markdown"] = "json"):
    """Build a plan from a full planning manifest sent by another module."""

    try:
        plan = build_plan(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if format == "markdown":
        return {"case_id": plan.case_id, "markdown": render_plan_markdown(plan)}
    return plan


@app.get("/api/planner/schema")
def planner_schema():
    """Publish the planner JSON schema so the research module can match it."""

    return {
        "plan_schema_version": PlanRequest.model_fields["plan_schema_version"].default,
        "plan_request_schema": PlanRequest.model_json_schema(),
    }
