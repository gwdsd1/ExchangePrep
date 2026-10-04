"""Local web UI and JSON API for the research module."""

import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from models import ResearchRequest, ResearchResult
from knowledge_base import KNOWLEDGE_PATH, retrieve_knowledge
from research import research


ROOT = Path(__file__).resolve().parent
app = FastAPI(title="ExchangePrep Research Demo", version="0.2.0")


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/config")
def config():
    return {
        "llm_provider": os.getenv("EXCHANGEPREP_LLM_PROVIDER", os.getenv("PATHLOOM_LLM_PROVIDER", "openai")),
        "search_provider": os.getenv("EXCHANGEPREP_SEARCH_PROVIDER", os.getenv("PATHLOOM_SEARCH_PROVIDER", "auto")),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "deepseek_configured": bool(os.getenv("DEEPSEEK_API_KEY")),
        "brave_configured": bool(os.getenv("BRAVE_API_KEY")),
        "knowledge_base_available": KNOWLEDGE_PATH.is_file(),
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
